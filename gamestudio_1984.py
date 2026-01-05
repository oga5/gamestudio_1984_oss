#!/usr/bin/env python3
"""
GameStudio 1984 v0.7 - AI-Powered Arcade Game Development System

This file focuses on:
- Agent creation and orchestration
- Workflow execution
- No tool implementations (moved to tools/)
"""

import os
import sys
import json
import datetime
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# LLM and Agent imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, SummarizationMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langchain_core.tools import tool
from langchain.agents.middleware.types import AgentMiddleware
from google.api_core.exceptions import ResourceExhausted


# ============================================================================
# Exceptions
# ============================================================================

class RepeatedToolErrorException(Exception):
    """Raised when the same tool error occurs too many times consecutively."""
    def __init__(self, tool_name: str, error_key: str, count: int):
        self.tool_name = tool_name
        self.error_key = error_key
        self.count = count
        super().__init__(
            f"Tool '{tool_name}' failed {count} times consecutively with same parameters.\n"
            f"Error key: {error_key[:200]}\n"
            f"This indicates the agent is stuck in an error loop. Terminating."
        )

# Load environment variables
load_dotenv()

# Global tool error counter
GLOBAL_TOOL_ERROR_COUNT = 0
MAX_GLOBAL_TOOL_ERRORS = 100  # Default, will be overridden by config

# Global token usage tracking
TOTAL_INPUT_TOKENS = 0
TOTAL_OUTPUT_TOKENS = 0
MAX_TOTAL_TOKENS = 5000000  # Default, will be overridden by config

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            MAX_GLOBAL_TOOL_ERRORS = config.get("max_global_tool_errors", 100)
            MAX_TOTAL_TOKENS = config.get("max_total_tokens", 5000000)
    except Exception as e:
        print(f"Warning: Could not load config.json: {e}")


# ============================================================================
# Global Error Counter Function
# ============================================================================

def increment_global_error_count():
    """
    Increment global tool error count and check if limit is reached.

    Raises:
        SystemExit: If max global errors exceeded
    """
    global GLOBAL_TOOL_ERROR_COUNT
    GLOBAL_TOOL_ERROR_COUNT += 1

    if GLOBAL_TOOL_ERROR_COUNT >= MAX_GLOBAL_TOOL_ERRORS:
        from middleware import tprint
        tprint(f"ERROR: Maximum global tool errors ({MAX_GLOBAL_TOOL_ERRORS}) reached!")
        tprint(f"Total errors: {GLOBAL_TOOL_ERROR_COUNT}")
        raise SystemExit(f"Max global tool errors exceeded")


# ============================================================================
# Global Token Usage Tracking Function
# ============================================================================

def add_token_usage(input_tokens: int, output_tokens: int):
    """
    Add token usage to global counters and check if limit is reached.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used

    Raises:
        SystemExit: If max total tokens exceeded
    """
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += input_tokens
    TOTAL_OUTPUT_TOKENS += output_tokens
    total_tokens = TOTAL_INPUT_TOKENS + TOTAL_OUTPUT_TOKENS

    if total_tokens >= MAX_TOTAL_TOKENS:
        from middleware import tprint
        tprint(f"ERROR: Maximum total tokens ({MAX_TOTAL_TOKENS}) reached!")
        tprint(f"Total input tokens: {TOTAL_INPUT_TOKENS}")
        tprint(f"Total output tokens: {TOTAL_OUTPUT_TOKENS}")
        tprint(f"Total tokens: {total_tokens}")
        raise SystemExit(f"Max total tokens exceeded")


# Import custom middleware
from middleware import LoggingMiddleware, TimeoutWaitMiddleware

# Import workflow components
from workflow_engine import WorkflowEngine
from asset_tracker import AssetTracker

# Import tools
from tools import (
    DESIGNER_TOOLS,
    PROGRAMMER_TOOLS,
    GRAPHIC_ARTIST_TOOLS,
    SOUND_ARTIST_TOOLS,
    TESTER_TOOLS,
    MANAGER_TOOLS,
    set_project_root,
)

# Import test directory helper
from tools.test_directory_helper import get_latest_test_directory

# Set project root environment variable
PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
os.environ["PROJECT_ROOT"] = PROJECT_ROOT


# ============================================================================
# Tool Error Tracking
# ============================================================================

class ToolErrorTracker:
    """
    Track consecutive identical errors for tools to prevent infinite loops.
    
    This tracks errors at the tool call level, detecting when the same tool
    is called repeatedly with the same parameters and produces the same error.
    """

    def __init__(self, max_consecutive_errors: int = 3, max_file_errors: int = 10):
        self.max_consecutive_errors = max_consecutive_errors
        self.max_file_errors = max_file_errors
        self._error_history: Dict[str, List[str]] = {}  # tool_name -> list of recent error keys
        self._file_error_history: Dict[str, List[str]] = {}  # tool_name -> list of recent file paths

    def record_error(self, tool_name: str, params: dict, error_msg: str):
        """
        Record an error and raise exception if same error repeats too many times.

        Args:
            tool_name: Name of the tool
            params: Parameters passed to the tool
            error_msg: The error message

        Raises:
            RepeatedToolErrorException: If same error occurs max_consecutive_errors times
                                       or same file fails max_file_errors times
        """
        # Create a key from params and error
        error_key = f"{json.dumps(params, sort_keys=True)}:{error_msg[:100]}"

        if tool_name not in self._error_history:
            self._error_history[tool_name] = []

        history = self._error_history[tool_name]
        history.append(error_key)

        # Keep only recent history
        if len(history) > self.max_consecutive_errors:
            history.pop(0)

        # Check for consecutive identical errors (same parameters)
        if len(history) >= self.max_consecutive_errors:
            if all(h == error_key for h in history):
                raise RepeatedToolErrorException(
                    tool_name,
                    error_key,
                    len(history)
                )

        # Track file-level errors (file_path only)
        file_path = params.get('file_path')
        if file_path:
            if tool_name not in self._file_error_history:
                self._file_error_history[tool_name] = []

            file_history = self._file_error_history[tool_name]
            file_history.append(file_path)

            # Keep only recent file history
            if len(file_history) > self.max_file_errors:
                file_history.pop(0)

            # Check for cumulative file-level errors (same file, regardless of other params)
            if len(file_history) >= self.max_file_errors:
                # Count how many times this specific file appears in the history
                file_error_count = sum(1 for f in file_history if f == file_path)
                if file_error_count >= self.max_file_errors:
                    raise RepeatedToolErrorException(
                        tool_name,
                        f"file_path={file_path} (file-level cumulative limit: {file_error_count}/{self.max_file_errors})",
                        file_error_count
                    )

    def record_success(self, tool_name: str):
        """Clear error history for a tool after success (but keep file-level cumulative count)."""
        if tool_name in self._error_history:
            self._error_history[tool_name] = []
        # Note: Don't clear file_error_history - we want cumulative count across all attempts

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics for debugging."""
        return {
            tool: len(errors) for tool, errors in self._error_history.items()
        }


# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


# Global tool error tracker
TOOL_ERROR_TRACKER = ToolErrorTracker(max_consecutive_errors=3, max_file_errors=10)


# Helper function to print with timestamp
def tprint(*args, **kwargs):
    """Print with timestamp prefix."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}]", *args, **kwargs, flush=True)


def get_model_for_role(role: str, role_models: Optional[Dict[str, str]] = None, default_model: Optional[str] = None) -> str:
    """
    Get the appropriate model for a given role.

    Args:
        role: Role name (e.g., "programmer", "designer")
        role_models: Optional dict mapping roles to models (overrides config)
        default_model: Optional default model (overrides config default)

    Returns:
        Model name to use for this role
    """
    # Handle both dict and string model configs
    model_config = CONFIG.get("model", {})

    if isinstance(model_config, str):
        # Legacy format: single model for all roles
        return default_model if default_model else model_config

    # New format: per-role models
    # Priority: role_models param > config per-role > default_model param > config default > fallback
    if role_models and role in role_models:
        return role_models[role]

    if isinstance(model_config, dict):
        # Check role-specific model
        if role in model_config:
            return model_config[role]
        # Fall back to default_model param, then config default, then fallback
        return default_model if default_model else model_config.get("default", "gemini-2.0-flash-exp")

    # Ultimate fallback
    return default_model if default_model else "gemini-2.0-flash-exp"


# ============================================================================
# Helper Functions
# ============================================================================

def normalize_role_name(role: str) -> str:
    """Normalize role name to lowercase with underscores.
    
    Examples:
        'Designer' -> 'designer'
        'Sound Artist' -> 'sound_artist'
        'Graphic Artist' -> 'graphic_artist'
    """
    return role.lower().replace(' ', '_')




# ============================================================================
# Prompt Loading
# ============================================================================

def load_prompt(prompt_path: str) -> str:
    """
    Load prompt from file.

    Tries to load from PROJECT_ROOT first (for project-specific prompts),
    falls back to script directory if not found.
    """
    # Try PROJECT_ROOT first (for copied prompts)
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        full_path = os.path.join(project_root, prompt_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                tprint(f"Warning: Could not read prompt from PROJECT_ROOT: {e}")

    # Fall back to script directory
    full_path = os.path.join(os.path.dirname(__file__), prompt_path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        tprint(f"Warning: Prompt file not found: {full_path}")
        return ""


# ============================================================================
# Agent Creation
# ============================================================================

def create_game_agent(role: str, task: str, asset_context: str = "", session_id: Optional[str] = None, model: Optional[str] = None, project_dir: Optional[str] = None) -> Any:
    """
    Create a simple agent with role + task prompt.

    Args:
        role: Role name (e.g., "programmer", "designer")
        task: Task name (e.g., "implement_game", "create_game_concept")
        asset_context: Optional asset context to inject for programmer
        session_id: Optional session ID for logging (auto-generated if not provided)
        model: Optional model name (uses config.json if not specified)
        project_dir: Optional project directory for log storage

    Returns:
        Agent instance
    """
    # Get tools for role (normalized to lowercase with underscores)
    tool_map = {
        "designer": DESIGNER_TOOLS,
        "programmer": PROGRAMMER_TOOLS,
        "graphic_artist": GRAPHIC_ARTIST_TOOLS,
        "sound_artist": SOUND_ARTIST_TOOLS,
        "tester": TESTER_TOOLS,
        "manager": MANAGER_TOOLS,
    }

    normalized_role = normalize_role_name(role)
    tools = tool_map.get(normalized_role, [])

    # Load prompts (using normalized role name)
    common_prompt = load_prompt("system_prompt/roles/common.md")
    role_prompt = load_prompt(f"system_prompt/roles/{normalized_role}.md")
    task_prompt = load_prompt(f"system_prompt/tasks/{normalized_role}/{task}.md")

    # Combine: Common vision + Role defines WHO + Task defines WHAT
    system_prompt = f"{common_prompt}\n\n---\n\n{role_prompt}\n\n---\n\n{task_prompt}"

    # Inject asset context for programmer
    if asset_context and normalized_role == "programmer":
        system_prompt += f"\n\n---\n\n{asset_context}"

    # Create LLM (use provided model or fall back to config)
    model_name = model if model else CONFIG.get("model", "gemini-2.0-flash-exp")
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
    )

    # Create middleware stack
    # Determine log directory (project_dir/logs)
    if project_dir:
        log_dir = os.path.join(project_dir, "logs")
    else:
        # Fallback for standalone agent usage
        workspace_dir = CONFIG.get("workspace_dir", "./workspace")
        log_dir = os.path.join(workspace_dir, "logs")

    middleware_stack = [
        # Logging: Track all model calls and tool usage with JSONL file output
        LoggingMiddleware(
            verbose=True,
            log_dir=log_dir,
            session_id=session_id,
            role=normalized_role,
            task=task,
            error_tracker=TOOL_ERROR_TRACKER  # Pass global error tracker
        ),

        # TPM Limit: Retry with exponential backoff on rate limits
        TimeoutWaitMiddleware(
            max_retries=CONFIG.get("max_retries", 3),
            initial_wait_seconds=60
        ),

        # Todo: Track task progress (langchain built-in)
        TodoListMiddleware(),
    ]

    # Create agent
    memory = MemorySaver()

    agent = create_agent(
        llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=memory,
        middleware=middleware_stack,
    )

    return agent


# ============================================================================
# Initialization Functions
# ============================================================================

def _initialize_system_prompts(project_dir: str) -> None:
    """
    Initialize system_prompt directory by copying from v0.4 source.

    Creates system_prompt directory and copies all role and task prompts
    to the project directory for agent reference.

    Args:
        project_dir: Project directory path
    """
    try:
        import shutil

        # Determine the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Source and destination paths
        src_system_prompt = os.path.join(script_dir, "system_prompt")
        dst_system_prompt = os.path.join(project_dir, "system_prompt")

        # Copy entire system_prompt directory
        if os.path.exists(src_system_prompt):
            if os.path.exists(dst_system_prompt):
                shutil.rmtree(dst_system_prompt)
            shutil.copytree(src_system_prompt, dst_system_prompt)
            tprint(f"✓ Copied system_prompt to: {dst_system_prompt}")
        else:
            tprint(f"Warning: system_prompt directory not found at {src_system_prompt}")

    except Exception as e:
        tprint(f"Error initializing system_prompt: {e}")
        # Don't fail the entire process if copy fails


def _initialize_templates(project_dir: str) -> None:
    """
    Initialize templates directory and public template files from v0.4 source.

    Creates templates directory with game templates (game_template, game_template_advanced)
    to the project directory for reference and use.

    Also copies essential template files (index.html, style.css, gamelib.js) to /public.
    For existing projects (where /public already exists), template files are NOT overwritten.

    Args:
        project_dir: Project directory path
    """
    try:
        import shutil

        # Determine the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Source and destination paths for templates directory
        src_templates = os.path.join(script_dir, "templates")
        dst_templates = os.path.join(project_dir, "templates")

        # Copy entire templates directory
        if os.path.exists(src_templates):
            if os.path.exists(dst_templates):
                shutil.rmtree(dst_templates)
            shutil.copytree(src_templates, dst_templates)
            tprint(f"✓ Copied templates to: {dst_templates}")
        else:
            tprint(f"Warning: templates directory not found at {src_templates}")

        # Initialize public directory with template files
        # Skip if public directory already exists (existing project)
        dst_public = os.path.join(project_dir, "public")
        if os.path.exists(dst_public):
            tprint(f"✓ Existing project detected - skipping public template initialization")
            return

        # Create public directory
        os.makedirs(dst_public, exist_ok=True)

        # Template files to copy to public
        template_files = [
            # (source_subdir, filename)
            ("game_template_advanced", "index.html"),
            ("game_template_advanced", "style.css"),
            ("game_template_advanced", "gamelib.js"),
        ]

        copied_count = 0
        for src_subdir, filename in template_files:
            src_file = os.path.join(src_templates, src_subdir, filename)
            dst_file = os.path.join(dst_public, filename)

            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                copied_count += 1
            else:
                tprint(f"Warning: Template file not found: {src_file}")

        if copied_count > 0:
            tprint(f"✓ Copied {copied_count} template files to: {dst_public}")

        # Create assets subdirectories
        assets_dirs = [
            os.path.join(dst_public, "assets", "images"),
            os.path.join(dst_public, "assets", "sounds"),
        ]
        for assets_dir in assets_dirs:
            os.makedirs(assets_dir, exist_ok=True)
        tprint(f"✓ Created assets directories in: {dst_public}")

    except Exception as e:
        tprint(f"Error initializing templates: {e}")
        # Don't fail the entire process if copy fails


# ============================================================================
# Main Workflow Execution
# ============================================================================

def execute_agent_task(agent, task_description: str, thread_id: str = "default") -> Dict[str, Any]:
    """
    Execute a task with an agent.

    Args:
        agent: The agent to execute
        task_description: Description of the task to perform
        thread_id: Thread ID for conversation memory

    Returns:
        Agent response as dictionary
    """
    try:
        # Invoke agent
        result = agent.invoke(
            {"messages": [{"role": "user", "content": task_description}]},
            config={"configurable": {"thread_id": thread_id}}
        )
        return result
    except RepeatedToolErrorException as e:
        tprint(f"ERROR: Tool error loop detected: {e}")
        return {"error": "repeated_tool_error", "details": str(e)}
    except GraphRecursionError as e:
        tprint(f"WARNING: Recursion limit reached: {e}")
        return {"error": "recursion_limit"}
    except ResourceExhausted as e:
        tprint(f"WARNING: Resource exhausted (TPM limit): {e}")
        return {"error": "resource_exhausted"}
    except Exception as e:
        tprint(f"ERROR: Agent execution failed: {e}")
        return {"error": str(e)}


def execute_asset_generation_task(agent, agent_role: str, task_name: str, task_id: str,
                                  user_request: str, task_desc: str, project_dir: str, session_id: str,
                                  role_models: Optional[Dict[str, str]] = None,
                                  default_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute asset generation task by processing one asset at a time.

    This reduces token consumption by creating a fresh agent for each asset,
    preventing context accumulation across multiple asset generations.

    Args:
        agent: Initial agent (will be recreated for each asset)
        agent_role: Role name (graphic_artist or sound_artist)
        task_name: Task name (generate_sprites or generate_sounds)
        task_id: Task ID for logging
        user_request: Original user request
        task_desc: Task description
        project_dir: Project directory path
        session_id: Session ID for unified logging
        role_models: Optional dict mapping roles to models (from command-line args)
        default_model: Optional default model (from command-line args)

    Returns:
        Combined result from all asset generations
    """
    tprint(f"  → Using per-asset generation to reduce token consumption")

    # Determine asset list file and key based on task
    if task_name == "generate_sprites":
        asset_file = os.path.join(project_dir, "work", "image_asset.json")
        asset_key = "images"
        asset_type = "image"
    else:  # generate_sounds
        asset_file = os.path.join(project_dir, "work", "sound_asset.json")
        asset_key = "sounds"
        asset_type = "sound"

    # Load asset list
    try:
        with open(asset_file, 'r', encoding='utf-8') as f:
            asset_data = json.load(f)
        assets = asset_data.get(asset_key, [])

        if not assets:
            tprint(f"  WARNING: No assets found in {asset_file}")
            return {"error": f"No {asset_key} found in {asset_file}"}

        tprint(f"  → Found {len(assets)} {asset_type}(s) to generate")

    except FileNotFoundError:
        tprint(f"  ERROR: Asset list not found: {asset_file}")
        return {"error": f"Asset list not found: {asset_file}"}
    except Exception as e:
        tprint(f"  ERROR: Failed to load asset list: {e}")
        return {"error": f"Failed to load asset list: {str(e)}"}

    # Process each asset individually
    combined_result = {
        "assets_generated": [],
        "assets_failed": [],
        "assets_skipped": []
    }

    # Get model for this role (respects command-line args)
    agent_model = get_model_for_role(agent_role, role_models, default_model)

    max_retries = 2  # Maximum retry attempts per asset

    for i, asset in enumerate(assets, 1):
        asset_name = asset.get("name", f"asset_{i}")
        tprint(f"\n  [{i}/{len(assets)}] Generating {asset_type}: {asset_name}")

        # Determine asset path
        if asset_type == "image":
            asset_path = os.path.join(project_dir, "public", "assets", "images", asset_name)
        else:  # sound
            asset_path = os.path.join(project_dir, "public", "assets", "sounds", asset_name)

        # Retry loop for this asset
        asset_generated = False
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                tprint(f"  → Retry attempt {attempt}/{max_retries} for {asset_name}")

            # Create fresh agent for this asset (prevents context accumulation)
            # Use same session_id to log to unified JSONL file
            try:
                fresh_agent = create_game_agent(
                    agent_role,
                    task_name,
                    session_id=session_id,
                    model=agent_model,
                    project_dir=project_dir
                )
            except Exception as e:
                tprint(f"  ERROR: Failed to create agent for {asset_name} (attempt {attempt}): {e}")
                if attempt == max_retries:
                    tprint(f"  ✗ Skipping {asset_name} after {max_retries} failed agent creation attempts")
                    combined_result["assets_failed"].append({
                        "name": asset_name,
                        "reason": f"Agent creation failed: {str(e)}"
                    })
                    break
                continue

            # Create task prompt for single asset
            asset_json = json.dumps(asset, indent=2, ensure_ascii=False)
            single_asset_prompt = f"""User Request: {user_request}

Task: Generate a SINGLE {asset_type} asset

You are processing asset {i} of {len(assets)}.

Asset specification:
{asset_json}

Instructions:
1. Generate ONLY this one {asset_type} based on the specification above
2. Follow all guidelines from your task instructions
3. Validate the generated asset
4. DO NOT process any other assets - focus only on this one

Complete when this single {asset_type} is successfully generated and validated.
"""

            # Execute with fresh agent (use unique thread_id for each asset attempt)
            result = execute_agent_task(
                fresh_agent,
                single_asset_prompt,
                thread_id=f"task_{task_id}_asset{i}_attempt{attempt}"
            )

            # Check for execution errors
            if "error" in result:
                tprint(f"  ERROR: Agent execution failed for {asset_name} (attempt {attempt}): {result.get('error')}")
                if attempt == max_retries:
                    tprint(f"  ✗ Skipping {asset_name} after {max_retries} failed attempts")
                    combined_result["assets_failed"].append({
                        "name": asset_name,
                        "reason": f"Agent error: {result.get('error')}"
                    })
                    break
                continue

            # Verify that the asset file was actually created
            if os.path.exists(asset_path):
                tprint(f"  ✓ {asset_name} generated successfully (attempt {attempt})")
                combined_result["assets_generated"].append(asset_name)
                asset_generated = True
                break
            else:
                tprint(f"  ERROR: Asset file not found: {asset_path}")
                tprint(f"  Agent completed without error, but file was not created.")
                tprint(f"  This may indicate MALFORMED_FUNCTION_CALL or other silent failure.")

                if attempt == max_retries:
                    tprint(f"  ✗ Skipping {asset_name} after {max_retries} attempts (file not created)")
                    combined_result["assets_failed"].append({
                        "name": asset_name,
                        "reason": "File not created after agent completion"
                    })
                    break

    # Summary
    tprint(f"\n  {'='*60}")
    tprint(f"  Asset Generation Summary:")
    tprint(f"    Total assets: {len(assets)}")
    tprint(f"    ✓ Generated: {len(combined_result['assets_generated'])}")
    tprint(f"    ✗ Failed: {len(combined_result['assets_failed'])}")

    if combined_result["assets_failed"]:
        tprint(f"\n  Failed assets:")
        for failed in combined_result["assets_failed"]:
            tprint(f"    - {failed['name']}: {failed['reason']}")

    if len(combined_result['assets_generated']) > 0:
        tprint(f"\n  ✓ Continuing with {len(combined_result['assets_generated'])} successfully generated {asset_type}(s)")
        # Return success even if some assets failed - programmer will work with available assets
        return combined_result
    else:
        tprint(f"\n  ✗ No {asset_type}s were generated successfully")
        return {"error": f"No {asset_type}s generated", "details": combined_result}


# ============================================================================
# Standard Output Capture (Tee)
# ============================================================================

class StdoutTee:
    """
    Tee class that writes to both stdout and a file, similar to the Unix tee command.
    This allows capturing stdout while still displaying it in the console.
    """

    def __init__(self, file_path: str, original_stdout):
        """
        Initialize the Tee object.

        Args:
            file_path: Path to the file where stdout should be written
            original_stdout: The original sys.stdout to write to
        """
        self.file = open(file_path, 'w', encoding='utf-8')
        self.stdout = original_stdout

    def write(self, data: str):
        """Write data to both file and stdout."""
        self.file.write(data)
        self.file.flush()
        self.stdout.write(data)
        self.stdout.flush()

    def flush(self):
        """Flush both file and stdout."""
        self.file.flush()
        self.stdout.flush()

    def close(self):
        """Close the file."""
        self.file.close()

    def isatty(self):
        """Return False to indicate this is not a terminal."""
        return False


def main(user_request: str = None, project_name: str = None, model: str = None,
         role_models: Optional[Dict[str, str]] = None, reasoning_enabled: bool = False,
         role_reasonings: Optional[Dict[str, bool]] = None):
    """
    Main entry point for GameStudio 1984 v0.7.

    Args:
        user_request: User's game request (e.g., "Create a space shooter game")
        project_name: Project name (auto-generated if not provided)
        model: Default model name (uses config.json if not provided)
        reasoning_enabled: Whether to enable reasoning for the project (default: False)
        role_reasonings: Optional dict mapping role names to reasoning flags
                         (e.g., {"programmer": True, "tester": False})
        role_models: Optional dict mapping role names to model names
                     (e.g., {"programmer": "gemini-3-flash", "tester": "gemini-3-flash"})
    """
    # Generate session ID for logging (timestamp format: YYYYMMDD_HHMMSS)
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determine project name
    if not project_name:
        execution_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = execution_timestamp

    # Determine project directory
    workspace_dir = CONFIG.get("workspace_dir", "./workspace")
    project_dir = os.path.join(workspace_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)

    # Setup stdout capture to project logs directory (unified with JSONL logs)
    project_log_dir = os.path.join(project_dir, "logs")
    os.makedirs(project_log_dir, exist_ok=True)
    stdout_log_file = os.path.join(project_log_dir, f"{session_id}.out")
    original_stdout = sys.stdout
    sys.stdout = StdoutTee(stdout_log_file, original_stdout)

    # Determine default model name
    if model:
        default_model = model
    else:
        model_config = CONFIG.get("model", "gemini-2.0-flash-exp")
        if isinstance(model_config, dict):
            default_model = model_config.get("default", "gemini-2.0-flash-exp")
        else:
            default_model = model_config

    tprint("=" * 80)
    tprint("GameStudio 1984 v0.7 - AI-Powered Arcade Game Development")
    tprint("=" * 80)
    tprint(f"Project: {project_name}")
    tprint(f"Session ID: {session_id}")
    tprint(f"Default Model: {default_model}")
    if role_models:
        tprint(f"Role-specific models: {role_models}")
    tprint(f"Project Directory: {project_dir}")

    # Initialize system prompts
    _initialize_system_prompts(project_dir)

    # Initialize templates
    _initialize_templates(project_dir)

    # Set PROJECT_ROOT to project directory
    global PROJECT_ROOT
    PROJECT_ROOT = os.path.abspath(project_dir)
    os.environ["PROJECT_ROOT"] = PROJECT_ROOT

    # Check if this is an existing project
    game_js_path = os.path.join(project_dir, "public", "game.js")
    design_json_path = os.path.join(project_dir, "work", "design.json")
    is_existing_project = os.path.exists(game_js_path)

    if is_existing_project:
        tprint("\n[Existing Project Detected]")
        tprint(f"  - Game implementation found: {game_js_path}")
        if os.path.exists(design_json_path):
            tprint(f"  - Design specification found: {design_json_path}")
        tprint("  - Mode: Continuous Development (fix/improvement)")
    else:
        tprint("\n[New Project]")
        tprint("  - Mode: New Game Development")

    # For WebUI compatibility: Don't prompt for input if no request provided
    if not user_request:
        user_request = ""  # Empty request will be handled by workflow decision logic

    if user_request:
        tprint(f"\nUser Request: {user_request}")
    else:
        tprint(f"\nUser Request: (empty - will resume existing workflow if available)")

    # Save user request to project directory
    prompt_dir = os.path.join(project_dir, "prompt")
    os.makedirs(prompt_dir, exist_ok=True)
    execution_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_file = os.path.join(prompt_dir, f"{execution_timestamp}.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(user_request)
    tprint(f"Prompt saved to: {prompt_file}")

    # Initialize workflow engine and asset tracker
    engine = WorkflowEngine(PROJECT_ROOT)
    tracker = AssetTracker()

    # Ensure PROJECT_ROOT is set for all file tools
    set_project_root(PROJECT_ROOT)

    # Check if there's an existing workflow with pending tasks
    workflow_path = "work/workflow.json"
    workflow_full_path = os.path.join(PROJECT_ROOT, workflow_path)
    existing_workflow_has_pending = False
    should_resume = False

    if os.path.exists(workflow_full_path):
        tprint("\n[Existing Workflow Detected]")
        # Try to load and check for pending tasks
        if engine.load_workflow(workflow_path):
            summary = engine.get_workflow_summary()
            tprint(f"  - Total tasks: {summary['total_tasks']}")
            tprint(f"  - Completed: {summary['completed']}")
            tprint(f"  - Pending: {summary['pending']}")
            tprint(f"  - In Progress: {summary['in_progress']}")

            if summary['pending'] > 0 or summary['in_progress'] > 0:
                existing_workflow_has_pending = True
                tprint("\n[Workflow Decision Required]")
                tprint("  - Existing workflow has pending tasks")
                tprint("  - Asking Manager to evaluate best course of action...")

                # Create manager agent to evaluate workflow action
                try:
                    manager_model = get_model_for_role("manager", role_models, default_model)
                    manager = create_game_agent("manager", "evaluate_workflow_action",
                                               session_id=session_id, model=manager_model,
                                               project_dir=project_dir)

                    evaluation_prompt = f"""Evaluate whether to resume existing workflow or create new one.

User Request: {user_request if user_request else "(empty)"}

Workflow Summary:
- Total tasks: {summary['total_tasks']}
- Completed: {summary['completed']}
- Pending: {summary['pending']}
- In Progress: {summary['in_progress']}

Analyze the project state and existing workflow, then decide:
- resume: Continue existing workflow
- create_new: Start new workflow

Write your decision to /work/workflow_action.json
"""

                    result = execute_agent_task(manager, evaluation_prompt,
                                               thread_id="workflow_evaluation")

                    if "error" in result:
                        tprint(f"  WARNING: Manager evaluation failed: {result['error']}")
                        tprint(f"  → Defaulting to resume existing workflow")
                        should_resume = True
                    else:
                        # Read manager's decision
                        action_file = os.path.join(project_dir, "work", "workflow_action.json")
                        if os.path.exists(action_file):
                            try:
                                with open(action_file, "r", encoding="utf-8") as f:
                                    action_data = json.load(f)

                                action = action_data.get("action", "resume")
                                reason = action_data.get("reason", "No reason provided")

                                if action == "resume":
                                    should_resume = True
                                    tprint("\n→ Manager Decision: RESUME existing workflow")
                                    tprint(f"   Reason: {reason}")
                                    tprint(f"   Continuing from task {summary['completed'] + 1} of {summary['total_tasks']}")
                                else:  # create_new
                                    should_resume = False
                                    tprint("\n→ Manager Decision: CREATE NEW workflow")
                                    tprint(f"   Reason: {reason}")
                                    tprint(f"   Previous workflow will be replaced")
                            except Exception as e:
                                tprint(f"  WARNING: Could not read workflow_action.json: {e}")
                                tprint(f"  → Defaulting to resume existing workflow")
                                should_resume = True
                        else:
                            tprint(f"  WARNING: workflow_action.json not created by manager")
                            tprint(f"  → Defaulting to resume existing workflow")
                            should_resume = True

                except Exception as e:
                    tprint(f"  ERROR: Failed to create manager for evaluation: {e}")
                    tprint(f"  → Defaulting to resume existing workflow")
                    should_resume = True

    # Step 1: Create workflow (skip if resuming)
    if should_resume:
        tprint("\n[Step 1] Using existing workflow...")
        tprint("✓ Workflow loaded")
    else:
        tprint("\n[Step 1] Generating workflow...")
        manager_model = get_model_for_role("manager", role_models, default_model)
        manager = create_game_agent("manager", "generate_workflow", session_id=session_id, model=manager_model, project_dir=project_dir)

        workflow_task = f"""Create a workflow for developing this game: {user_request}

Generate a complete workflow.json file at /work/workflow.json following the format in your task instructions.
The workflow must follow the asset-first rule: Design → Assets → Implementation → Testing.
"""

        result = execute_agent_task(manager, workflow_task, thread_id="workflow_creation")

        if "error" in result:
            tprint(f"ERROR: Failed to create workflow: {result['error']}")
            return

        tprint("✓ Workflow created")

    # Step 2: Load and validate workflow (skip if already loaded for resume)
    if should_resume:
        tprint("\n[Step 2] Validating resumed workflow...")
    else:
        tprint("\n[Step 2] Loading and validating workflow...")
        if not engine.load_workflow(workflow_path):
            tprint("ERROR: Failed to load workflow!")
            return

    errors = engine.validate_workflow_order()
    if errors:
        tprint("ERROR: Invalid workflow order!")
        for error in errors:
            tprint(f"  - {error}")
        return

    tprint("✓ Workflow validated")

    # Step 3: Execute workflow phases
    tprint("\n[Step 3] Executing workflow...")

    max_iterations = 100  # Safety limit
    iteration = 0

    while not engine.is_workflow_complete() and iteration < max_iterations:
        iteration += 1

        # Get next task
        task = engine.get_next_task()
        if not task:
            tprint("No more tasks available (waiting for dependencies)")
            break

        task_id = task.get("id")
        agent_role = normalize_role_name(task.get("agent", ""))
        task_name = task.get("task")
        task_desc = task.get("description", "")

        tprint(f"\n--- Task {iteration}: {task_id} ---")
        tprint(f"Agent: {agent_role}")
        tprint(f"Task: {task_name}")
        tprint(f"Description: {task_desc}")

        # Update status to in_progress and save state
        engine.update_task_status(task_id, "in_progress")
        engine.save_workflow(workflow_path)

        # Create agent for this task
        try:
            # Select model for this role
            agent_model = get_model_for_role(agent_role, role_models, default_model)
            agent = create_game_agent(agent_role, task_name, session_id=session_id, model=agent_model, project_dir=project_dir)
            tprint(f"  → Using model: {agent_model}")
        except Exception as e:
            tprint(f"ERROR: Failed to create agent: {e}")
            engine.update_task_status(task_id, "failed", str(e))
            engine.save_workflow(workflow_path)
            break

        # Execute task
        # Special handling for asset generation tasks: process one asset at a time
        if task_name in ["generate_sprites", "generate_sounds"]:
            result = execute_asset_generation_task(
                agent, agent_role, task_name, task_id, user_request, task_desc, project_dir, session_id,
                role_models, default_model
            )
        else:
            task_prompt = f"User Request: {user_request}\n\nExecute your task: {task_desc}"
            result = execute_agent_task(agent, task_prompt, thread_id=f"task_{task_id}")

        if "error" in result:
            error_type = result.get("error")
            error_details = result.get("details", "")
            
            # Handle repeated tool error (infinite loop detected)
            if error_type == "repeated_tool_error":
                tprint(f"ERROR: Tool error loop detected!")
                tprint(f"Details: {error_details}")
                tprint("Terminating workflow to prevent infinite loop.")
                engine.update_task_status(task_id, "failed", f"Repeated tool error: {error_details}")
                engine.save_workflow(workflow_path)
                break

            # Handle other errors
            tprint(f"ERROR: Task failed: {error_type}")
            engine.update_task_status(task_id, "failed", error_type)
            engine.save_workflow(workflow_path)
            break

        # Mark as completed (do this FIRST before archiving, for atomicity)
        engine.update_task_status(task_id, "completed", result)
        tprint(f"✓ Task {task_id} completed")

        # Save workflow state after each task completion for resume capability
        engine.save_workflow(workflow_path)

        # If this was a fix_bugs task, archive previous test results
        # NOTE: Archive operation comes AFTER task completion for safety
        if task_name == "fix_bugs":
            try:
                # Count how many fix attempts have been made
                fix_count = sum(1 for p in engine.workflow.get("phases", [])
                              if "fix" in p.get("id", "").lower())

                # Archive previous test files with fix attempt number
                test_result_path = os.path.join(project_dir, "work", "test_result.json")
                test_report_path = os.path.join(project_dir, "work", "test_report.json")

                archived_count = 0
                if os.path.exists(test_result_path):
                    try:
                        archived_path = os.path.join(project_dir, "work", f"test_result_before_fix{fix_count}.json")
                        os.rename(test_result_path, archived_path)
                        tprint(f"  ✓ Archived: test_result.json → test_result_before_fix{fix_count}.json")
                        archived_count += 1
                    except Exception as e:
                        tprint(f"  ⚠ Warning: Could not archive test_result.json: {e}")

                if os.path.exists(test_report_path):
                    try:
                        archived_path = os.path.join(project_dir, "work", f"test_report_before_fix{fix_count}.json")
                        os.rename(test_report_path, archived_path)
                        tprint(f"  ✓ Archived: test_report.json → test_report_before_fix{fix_count}.json")
                        archived_count += 1
                    except Exception as e:
                        tprint(f"  ⚠ Warning: Could not archive test_report.json: {e}")

                if archived_count > 0:
                    tprint(f"  → Ready for fresh re-test (attempt {fix_count})")
            except Exception as e:
                tprint(f"  ⚠ Warning: Archive operation failed: {e}")

        # Check if this was a test task - if FAIL, add fix phase
        if task_name == "test_game":
            # Find test_report.json in the latest numbered test directory
            latest_test_dir = get_latest_test_directory(project_dir)
            if latest_test_dir:
                test_report_path = os.path.join(project_dir, latest_test_dir.lstrip("/"), "test_report.json")
            else:
                # Fallback to legacy location
                test_report_path = os.path.join(project_dir, "work", "test_report.json")

            if os.path.exists(test_report_path):
                try:
                    with open(test_report_path, "r", encoding="utf-8") as f:
                        test_report = json.load(f)

                    # CRITICAL: Validate test_report schema
                    if not isinstance(test_report, dict):
                        tprint(f"  ✗ ERROR: test_report.json must be a JSON object, got {type(test_report).__name__}")
                        tprint(f"  ✗ Cannot determine test verdict. Marking task as failed.")
                        engine.update_task_status(task_id, "failed", "Invalid test_report schema")
                        engine.save_workflow(workflow_path)
                        break

                    if "verdict" not in test_report:
                        tprint(f"  ✗ ERROR: test_report.json is missing 'verdict' field")
                        tprint(f"  ✗ Required format: {{'verdict': 'PASS' | 'FAIL', ...}}")
                        tprint(f"  ✗ Actual content: {json.dumps(test_report, indent=2)[:200]}")
                        engine.update_task_status(task_id, "failed", "test_report missing 'verdict' field")
                        engine.save_workflow(workflow_path)
                        break

                    # Get verdict and validate it's a string
                    verdict_raw = test_report.get("verdict")
                    if not isinstance(verdict_raw, str):
                        tprint(f"  ✗ ERROR: 'verdict' must be a string, got {type(verdict_raw).__name__}")
                        engine.update_task_status(task_id, "failed", f"Invalid verdict type: {type(verdict_raw).__name__}")
                        engine.save_workflow(workflow_path)
                        break

                    verdict = verdict_raw.upper()
                    if verdict not in ["PASS", "FAIL"]:
                        tprint(f"  ✗ ERROR: 'verdict' must be 'PASS' or 'FAIL', got '{verdict_raw}'")
                        engine.update_task_status(task_id, "failed", f"Invalid verdict value: {verdict_raw}")
                        engine.save_workflow(workflow_path)
                        break

                    tprint(f"  Test Verdict: {verdict}")

                    if verdict == "FAIL":
                        # Count existing fix phases to prevent infinite loops
                        # IMPROVED: Use more reliable ID pattern matching
                        fix_phases = [
                            p for p in engine.workflow.get("phases", [])
                            if p.get("id", "").lower().startswith("fix_") or
                               p.get("id", "").lower() == "debug" or
                               "fix_bugs" in p.get("id", "").lower()
                        ]
                        fix_count = len(fix_phases)

                        max_fix_attempts = 3
                        if fix_count < max_fix_attempts:
                            attempt_num = fix_count + 1
                            tprint(f"  → Test failed. Adding fix phase (attempt {attempt_num}/{max_fix_attempts})")
                            tprint(f"    Error details: {test_report.get('errors', [])[:2] if 'errors' in test_report else 'See test_report.json'}")

                            if engine.add_fix_phase(task_id):
                                tprint(f"  ✓ Fix phase added to workflow")
                                engine.save_workflow(workflow_path)
                            else:
                                tprint(f"  ⚠ Failed to add fix phase")
                        else:
                            tprint(f"  ⚠ Maximum fix attempts ({max_fix_attempts}) reached. Stopping.")
                            tprint(f"  ℹ️ Existing fix phases: {[p.get('id') for p in fix_phases]}")
                            break
                    elif verdict == "PASS":
                        tprint(f"  ✓ Test passed! Game is working correctly.")

                except json.JSONDecodeError as e:
                    tprint(f"  ✗ ERROR: test_report.json is not valid JSON: {e}")
                    engine.update_task_status(task_id, "failed", f"Invalid JSON in test_report: {str(e)[:100]}")
                    engine.save_workflow(workflow_path)
                    break
                except Exception as e:
                    tprint(f"  ✗ ERROR: Could not process test report: {e}")
                    engine.update_task_status(task_id, "failed", f"Test report processing error: {str(e)[:100]}")
                    engine.save_workflow(workflow_path)
                    break
            else:
                tprint(f"  ✗ WARNING: test_report.json not found at {test_report_path}")
                tprint(f"  ✗ Tester must create this file with 'verdict' field")

        # Save workflow progress
        engine.save_workflow(workflow_path)

    # Summary
    tprint("\n" + "=" * 80)
    summary = engine.get_workflow_summary()
    tprint(f"Workflow Summary:")
    tprint(f"  Total Tasks: {summary['total_tasks']}")
    tprint(f"  Completed: {summary['completed']}")
    tprint(f"  Pending: {summary['pending']}")
    tprint(f"  In Progress: {summary['in_progress']}")

    if summary['complete']:
        tprint("\n✓ Game development complete!")
    else:
        tprint("\n⚠ Workflow incomplete")

    tprint("=" * 80)

    # Close the stdout file
    if hasattr(sys.stdout, 'close'):
        sys.stdout.close()
    # Restore original stdout
    sys.stdout = original_stdout


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GameStudio 1984 v0.7")
    parser.add_argument("request", nargs="?", help="Game creation request")
    parser.add_argument("--project", "-p", help="Project name (auto-generated if not specified)")
    parser.add_argument("--model", "-m", help="Default model name (uses config.json if not specified)")
    parser.add_argument("--designer-model", help="Model for designer role")
    parser.add_argument("--programmer-model", help="Model for programmer role")
    parser.add_argument("--graphic-artist-model", help="Model for graphic_artist role")
    parser.add_argument("--sound-artist-model", help="Model for sound_artist role")
    parser.add_argument("--tester-model", help="Model for tester role")
    parser.add_argument("--manager-model", help="Model for manager role")
    parser.add_argument("--reasoning", action="store_true", help="Enable reasoning mode for supported models")
    # Per-role reasoning flags
    parser.add_argument("--designer-reasoning", action="store_true", help="Enable reasoning for designer role")
    parser.add_argument("--programmer-reasoning", action="store_true", help="Enable reasoning for programmer role")
    parser.add_argument("--graphic-artist-reasoning", action="store_true", help="Enable reasoning for graphic artist role")
    parser.add_argument("--sound-artist-reasoning", action="store_true", help="Enable reasoning for sound artist role")
    parser.add_argument("--tester-reasoning", action="store_true", help="Enable reasoning for tester role")
    parser.add_argument("--manager-reasoning", action="store_true", help="Enable reasoning for manager role")

    args = parser.parse_args()

    # Build role_models dict from command-line arguments
    role_models = {}
    if args.designer_model:
        role_models["designer"] = args.designer_model
    if args.programmer_model:
        role_models["programmer"] = args.programmer_model
    if args.graphic_artist_model:
        role_models["graphic_artist"] = args.graphic_artist_model
    if args.sound_artist_model:
        role_models["sound_artist"] = args.sound_artist_model
    if args.tester_model:
        role_models["tester"] = args.tester_model
    if args.manager_model:
        role_models["manager"] = args.manager_model
    
    # Build role_reasonings dict from command-line arguments
    role_reasonings = {}
    if args.designer_reasoning:
        role_reasonings["designer"] = True
    if args.programmer_reasoning:
        role_reasonings["programmer"] = True
    if args.graphic_artist_reasoning:
        role_reasonings["graphic_artist"] = True
    if args.sound_artist_reasoning:
        role_reasonings["sound_artist"] = True
    if args.tester_reasoning:
        role_reasonings["tester"] = True
    if args.manager_reasoning:
        role_reasonings["manager"] = True

    main(user_request=args.request, project_name=args.project, model=args.model,
         role_models=role_models if role_models else None, reasoning_enabled=args.reasoning,
         role_reasonings=role_reasonings if role_reasonings else None)
