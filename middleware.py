"""
GameStudio 1984 v0.4 - Custom Middlewares

This module contains custom middleware implementations for the agent system:
- LoggingMiddleware: Logs model calls and tool calls for monitoring and debugging
- TimeoutWaitMiddleware: Handles rate limit errors with automatic retry logic
"""
import time
import logging
import datetime
import json
import uuid
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse, ToolCallRequest
from google.api_core.exceptions import ResourceExhausted

# Setup logging
logger = logging.getLogger(__name__)


def tprint(*args, **kwargs):
    """Print with timestamp prefix."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}]", *args, **kwargs, flush=True)


def format_message_for_log(msg) -> str:
    """
    Format a LangChain message for human-readable logging.

    Extracts essential information and hides internal metadata.

    Args:
        msg: A LangChain message object

    Returns:
        A human-readable string representation
    """
    try:
        # Get message type/role
        msg_type = type(msg).__name__

        # Try to extract role
        role = getattr(msg, 'type', None) or getattr(msg, 'role', None) or msg_type

        # Extract content
        content = getattr(msg, 'content', None)

        # Check for tool calls (function_call in Gemini)
        tool_calls = []
        additional_kwargs = getattr(msg, 'additional_kwargs', {})

        # Gemini function_call format
        if 'function_call' in additional_kwargs:
            fc = additional_kwargs['function_call']
            tool_name = fc.get('name', 'unknown')
            # Parse arguments JSON if possible
            args_raw = fc.get('arguments', '{}')
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                # Truncate long argument values
                args_preview = {}
                for k, v in args.items() if isinstance(args, dict) else {}:
                    v_str = str(v)
                    args_preview[k] = v_str[:100] + "..." if len(v_str) > 100 else v_str
                tool_calls.append(f"{tool_name}({json.dumps(args_preview, ensure_ascii=False)})")
            except:
                tool_calls.append(f"{tool_name}(...)")

        # LangChain tool_calls format
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    tool_name = tc.get('name', 'unknown')
                    tool_calls.append(f"{tool_name}(...)")
                else:
                    tool_calls.append(str(tc)[:50])

        # Build output
        parts = [f"[{role}]"]

        if content:
            # Truncate content for preview
            content_str = str(content)
            if len(content_str) > 200:
                content_str = content_str[:200] + "..."
            parts.append(content_str)

        if tool_calls:
            parts.append(f"tool_calls: {', '.join(tool_calls)}")

        # Check if it's a tool result message
        tool_call_id = getattr(msg, 'tool_call_id', None)
        name = getattr(msg, 'name', None)
        if tool_call_id and name:
            content_preview = str(content)[:100] + "..." if content and len(str(content)) > 100 else content
            return f"[tool_result:{name}] {content_preview}"

        return " ".join(parts) if len(parts) > 1 else parts[0]

    except Exception as e:
        # Fallback to simple string representation
        msg_str = str(msg)
        return msg_str[:200] + "..." if len(msg_str) > 200 else msg_str


class LoggingMiddleware(AgentMiddleware):
    """
    Middleware that logs all model calls and tool calls.

    This middleware tracks:
    - Model Call: Request messages and response content
    - Tool Call: Tool name, arguments, and execution results

    Logs are output to:
    - Console: Simple text format (with timestamps)
    - File: JSONL format (logs/{session_id}.jsonl)

    This helps with monitoring, debugging, and understanding agent behavior.
    """

    def __init__(self, verbose: bool = True, log_dir: str = "logs", session_id: Optional[str] = None,
                 role: Optional[str] = None, task: Optional[str] = None, error_tracker: Optional[Any] = None):
        """
        Initialize the logging middleware.

        Args:
            verbose: If True, prints detailed logs. If False, only logs critical information.
            log_dir: Directory for JSONL log files (default: "logs")
            session_id: Session ID for this execution (auto-generated if not provided)
            role: Role name (e.g., "manager", "programmer")
            task: Task name (e.g., "validate_assets", "implement_game")
            error_tracker: Optional ToolErrorTracker instance for tracking consecutive errors
        """
        self.verbose = verbose
        self._model_call_count = 0
        self._tool_call_count = 0
        self.error_tracker = error_tracker  # Store error tracker instance

        # Generate or use provided session_id
        self.session_id = session_id if session_id else str(uuid.uuid4())[:8]

        # Store role and task information
        self.role = role
        self.task = task

        # Setup log directory and file
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{self.session_id}.jsonl"

    @property
    def name(self) -> str:
        return "LoggingMiddleware"

    def _log_event(self, level: str, category: str, event: str, call_id: int,
                   message: str, metadata: Optional[Dict] = None):
        """
        Log an event to both console and JSONL file.

        Args:
            level: DEBUG, INFO, WARNING, ERROR
            category: model_call or tool_call
            event: start, request, response, result, or error
            call_id: Call number for this category
            message: Human-readable message
            metadata: Additional structured data
        """
        # Create log entry
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "role": self.role,  # Add role information
            "task": self.task,  # Add task information
            "level": level,
            "category": category,
            "event": event,
            "call_id": call_id,
            "message": message,
            "metadata": metadata or {}
        }

        # Write to JSONL file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()  # Ensure immediate write for webui updates
                os.fsync(f.fileno())  # Force OS to write to disk
        except Exception as e:
            tprint(f"[LoggingMiddleware] Warning: Failed to write log to file: {e}")

    def wrap_model_call(self, request: ModelRequest, handler):
        """
        Log model call requests and responses.

        Args:
            request: The model request containing messages
            handler: The handler function to execute the actual model call

        Returns:
            The model response
        """
        self._model_call_count += 1
        call_id = self._model_call_count

        # Log: Model call start
        if self.verbose:
            role_task_info = ""
            if self.role and self.task:
                role_task_info = f" (role: {self.role}, task: {self.task})"
            elif self.role:
                role_task_info = f" (role: {self.role})"
            elif self.task:
                role_task_info = f" (task: {self.task})"
            tprint(f"[LoggingMiddleware] 🤖 Model Call #{call_id}{role_task_info} - START")

        # Extract request details
        messages_count = 0
        messages_preview = []
        messages_full = []
        if hasattr(request, 'messages') and request.messages:
            messages_count = len(request.messages)
            if self.verbose:
                tprint(f"[LoggingMiddleware]   📨 Request: {messages_count} message(s)")
            for i, msg in enumerate(request.messages[-3:], 1):  # Show last 3 messages
                msg_preview = format_message_for_log(msg)
                messages_preview.append(msg_preview)
                if self.verbose:
                    tprint(f"[LoggingMiddleware]   Message {i}: {msg_preview}")

            # Extract full messages for JSONL (all messages, not just last 3)
            for msg in request.messages:
                # Convert message to dict format for better logging
                if hasattr(msg, 'dict'):
                    messages_full.append(msg.dict())
                elif hasattr(msg, 'to_dict'):
                    messages_full.append(msg.to_dict())
                else:
                    messages_full.append(str(msg))

        # Log: Request details to JSONL
        self._log_event(
            level="DEBUG",
            category="model_call",
            event="request",
            call_id=call_id,
            message=f"Model call request with {messages_count} message(s)",
            metadata={
                "messages_count": messages_count,
                "messages_preview": messages_preview,
                "messages_full": messages_full  # Add full messages
            }
        )

        # Execute the actual model call
        start_time = time.time()
        response: ModelResponse = handler(request)
        elapsed = time.time() - start_time

        # Extract response details
        response_preview = ""
        response_full = []
        total_tokens = 0
        usage_metadata = {}
        if response.result:
            last_message = response.result[-1]
            response_preview = format_message_for_log(last_message)

            # Extract full response for JSONL
            for msg in response.result:
                # Convert message to dict format for better logging
                if hasattr(msg, 'dict'):
                    response_full.append(msg.dict())
                elif hasattr(msg, 'to_dict'):
                    response_full.append(msg.to_dict())
                else:
                    response_full.append(str(msg))

            # Extract token usage if available
            input_tokens = 0
            output_tokens = 0
            if hasattr(last_message, "response_metadata") and "usage_metadata" in last_message.response_metadata:
                usage = last_message.response_metadata["usage_metadata"]
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)
                usage_metadata = dict(usage)  # Store full usage metadata
                if self.verbose and (input_tokens or output_tokens):
                    tprint(f"[LoggingMiddleware]   📊 Tokens: input={input_tokens}, output={output_tokens}, total={total_tokens}")

        # Log: Response details to JSONL
        self._log_event(
            level="DEBUG",
            category="model_call",
            event="response",
            call_id=call_id,
            message=f"Model call completed in {elapsed:.2f}s",
            metadata={
                "elapsed_seconds": elapsed,
                "response_preview": response_preview,
                "response_full": response_full,  # Add full response
                "total_tokens": total_tokens,
                "usage_metadata": usage_metadata  # Add full usage metadata
            }
        )

        if self.verbose:
            if response_preview:
                tprint(f"[LoggingMiddleware]   📬 Response: {response_preview}")
            role_task_info = ""
            if self.role and self.task:
                role_task_info = f" (role: {self.role}, task: {self.task})"
            elif self.role:
                role_task_info = f" (role: {self.role})"
            elif self.task:
                role_task_info = f" (task: {self.task})"
            tprint(f"[LoggingMiddleware] 🤖 Model Call #{call_id}{role_task_info} - COMPLETED in {elapsed:.2f}s")

        # Track global token usage
        if input_tokens > 0 or output_tokens > 0:
            try:
                from gamestudio_1984 import add_token_usage
                add_token_usage(input_tokens, output_tokens)
            except ImportError:
                pass
            except SystemExit as e:
                # Re-raise SystemExit to terminate the program
                if self.verbose:
                    tprint(f"[LoggingMiddleware] 🚨 Token limit reached!")
                raise

        return response

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        """
        Log tool call requests and results.

        Args:
            request: The tool call request containing tool name and arguments
            handler: The handler function to execute the actual tool call

        Returns:
            The tool execution result
        """
        self._tool_call_count += 1
        call_id = self._tool_call_count

        tool_name = request.tool_call.get("name", "unknown")
        tool_args = request.tool_call.get("args", {})

        # Log: Tool call start
        if self.verbose:
            tprint(f"[LoggingMiddleware] 🔧 Tool Call #{call_id} - START")
            tprint(f"[LoggingMiddleware]   Tool: {tool_name}")

            # Log arguments (truncate if too long)
            args_str = str(tool_args)
            if len(args_str) > 300:
                args_str = args_str[:300] + "..."
            tprint(f"[LoggingMiddleware]   Args: {args_str}")

        # Log: Tool call request to JSONL
        self._log_event(
            level="DEBUG",
            category="tool_call",
            event="request",
            call_id=call_id,
            message=f"Tool call requested: {tool_name}",
            metadata={
                "tool_name": tool_name,
                "tool_args": tool_args
            }
        )

        # Execute the actual tool call
        start_time = time.time()
        try:
            result = handler(request)
            elapsed = time.time() - start_time

            # Truncate result for logging
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."

            # Log: Tool call result to JSONL
            self._log_event(
                level="DEBUG",
                category="tool_call",
                event="result",
                call_id=call_id,
                message=f"Tool call completed in {elapsed:.2f}s",
                metadata={
                    "tool_name": tool_name,
                    "elapsed_seconds": elapsed,
                    "result_preview": result_str
                }
            )

            if self.verbose:
                tprint(f"[LoggingMiddleware]   ✅ Result: {result_str[:200] + '...' if len(result_str) > 200 else result_str}")
                tprint(f"[LoggingMiddleware] 🔧 Tool Call #{call_id} - SUCCESS in {elapsed:.2f}s")

            # Check if result is a "soft error" (tool returned error string instead of exception)
            # Multiple error patterns: "❌ Error:", "ERROR:", "FAILED:", etc.
            is_soft_error = False
            if result is not None:
                result_content = ""
                if hasattr(result, 'content'):
                    result_content = str(result.content)
                else:
                    result_content = str(result)

                # Check for multiple error patterns (case-insensitive)
                error_patterns = [
                    "❌ Error",      # smart_file_edit format
                    "ERROR:",        # Standard error format
                    "FAILED:",       # Failure indicator
                    "SKIPPED:",      # Skipped operation (treat as error for tracking)
                    "NOT_FOUND",     # File not found
                ]

                # Special case: file_exists tool should NOT treat NOT_FOUND as an error
                # For file_exists, NOT_FOUND is a normal result indicating the file doesn't exist
                if tool_name == "file_exists" and "NOT_FOUND" in result_content:
                    is_soft_error = False
                elif any(pattern in result_content for pattern in error_patterns):
                    is_soft_error = True
                    if self.verbose:
                        tprint(f"[LoggingMiddleware]   ⚠️ Detected soft error (tool returned error string): {result_content[:100]}")

                    # Record error in tool error tracker
                    # This may raise RepeatedToolErrorException if too many consecutive failures
                    if self.error_tracker:
                        self.error_tracker.record_error(tool_name, tool_args, result_content[:200])

            # Record success in tool error tracker (clear error history) - only if not a soft error
            if not is_soft_error and self.error_tracker:
                self.error_tracker.record_success(tool_name)

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)[:200]

            # Log: Tool call error to JSONL
            self._log_event(
                level="ERROR",
                category="tool_call",
                event="error",
                call_id=call_id,
                message=f"Tool call failed in {elapsed:.2f}s",
                metadata={
                    "tool_name": tool_name,
                    "elapsed_seconds": elapsed,
                    "error": error_msg
                }
            )

            if self.verbose:
                tprint(f"[LoggingMiddleware]   ❌ Error: {error_msg}")
                tprint(f"[LoggingMiddleware] 🔧 Tool Call #{call_id} - FAILED in {elapsed:.2f}s")

            # Record error in tool error tracker
            # This may raise RepeatedToolErrorException if too many consecutive failures
            if self.error_tracker:
                self.error_tracker.record_error(tool_name, tool_args, error_msg)
            
            # Increment global error count
            try:
                from gamestudio_1984 import increment_global_error_count
                increment_global_error_count()
                if self.verbose:
                    tprint(f"[LoggingMiddleware] 📊 Global error count updated")
            except ImportError:
                pass
            except SystemExit as e:
                # Re-raise SystemExit to terminate the program
                if self.verbose:
                    tprint(f"[LoggingMiddleware] 🚨 Global error limit reached!")
                raise

            raise


class TimeoutWaitMiddleware(AgentMiddleware):
    """
    Middleware that handles rate limit errors with automatic retry logic.

    This middleware specifically handles:
    - Google API ResourceExhausted errors (TPM limits)
    - Other rate limiting errors

    When a rate limit is detected, it:
    1. Attempts to extract the retry delay from the error message
       (e.g., "Please retry in 45.604366383s")
    2. Adds 60 seconds to the extracted delay
    3. Sleeps for that calculated duration before retrying
    4. Falls back to exponential backoff if delay cannot be extracted
    """

    def __init__(
        self,
        max_retries: int = 5,
        initial_wait_seconds: int = 60,
        max_wait_seconds: int = 300,
        exponential_backoff: bool = True
    ):
        """
        Initialize the timeout wait middleware.

        Args:
            max_retries: Maximum number of retry attempts
            initial_wait_seconds: Initial wait time in seconds
            max_wait_seconds: Maximum wait time in seconds
            exponential_backoff: If True, uses exponential backoff for wait times
        """
        self.max_retries = max_retries
        self.initial_wait_seconds = initial_wait_seconds
        self.max_wait_seconds = max_wait_seconds
        self.exponential_backoff = exponential_backoff
        self._retry_count = 0

    @property
    def name(self) -> str:
        return "TimeoutWaitMiddleware"

    def _calculate_wait_time(self, attempt: int) -> int:
        """
        Calculate wait time based on attempt number.

        Args:
            attempt: The current attempt number (0-indexed)

        Returns:
            Wait time in seconds
        """
        if self.exponential_backoff:
            # Exponential backoff: wait_time = initial * (2 ^ attempt)
            wait_time = self.initial_wait_seconds * (2 ** attempt)
        else:
            # Linear backoff: constant wait time
            wait_time = self.initial_wait_seconds

        # Cap at max_wait_seconds
        return min(wait_time, self.max_wait_seconds)

    def _extract_retry_delay(self, error: Exception) -> Optional[float]:
        """
        Extract retry delay from the error message.

        Args:
            error: The exception to parse

        Returns:
            Retry delay in seconds (float), or None if not found
        """
        error_msg = str(error)

        # Try to parse "Please retry in X.Xs" or "Please retry in Xs"
        # Example: "Please retry in 45.604366383s"
        match = re.search(r'Please retry in ([\d.]+)s', error_msg)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Try to parse "retry_delay { seconds: X }"
        # Example: "retry_delay { seconds: 45 }"
        match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', error_msg)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Check if the error has a retry_delay attribute (structured data)
        if hasattr(error, 'retry_delay'):
            try:
                retry_delay = error.retry_delay
                if hasattr(retry_delay, 'seconds'):
                    return float(retry_delay.seconds)
            except (AttributeError, ValueError):
                pass

        return None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if the error is a rate limit error.

        Args:
            error: The exception to check

        Returns:
            True if it's a rate limit error, False otherwise
        """
        # Check for Google API ResourceExhausted
        if isinstance(error, ResourceExhausted):
            return True

        # Check error message for common rate limit indicators
        error_msg = str(error).lower()
        rate_limit_keywords = [
            "rate limit",
            "quota exceeded",
            "too many requests",
            "429",
            "resource exhausted",
            "tpm limit"
        ]

        return any(keyword in error_msg for keyword in rate_limit_keywords)

    def wrap_model_call(self, request: ModelRequest, handler):
        """
        Wrap model call with retry logic for rate limit errors.

        Args:
            request: The model request
            handler: The handler function to execute the actual model call

        Returns:
            The model response

        Raises:
            The original exception if max retries exceeded or non-rate-limit error
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # Attempt the model call
                response = handler(request)

                # If successful and this was a retry, log success
                if attempt > 0:
                    tprint(f"[TimeoutWaitMiddleware] ✅ Model call succeeded after {attempt} retry attempt(s)")
                    self._retry_count = 0  # Reset retry counter on success

                return response

            except Exception as e:
                # Check if it's a rate limit error
                if not self._is_rate_limit_error(e):
                    # Not a rate limit error, re-raise immediately
                    raise

                last_error = e

                # If we've exhausted retries, re-raise
                if attempt >= self.max_retries:
                    tprint(f"[TimeoutWaitMiddleware] ❌ Max retries ({self.max_retries}) exceeded for rate limit error")
                    raise

                # Try to extract retry delay from error message
                extracted_delay = self._extract_retry_delay(e)

                if extracted_delay is not None:
                    # Use extracted delay + 60 seconds as requested
                    wait_time = int(extracted_delay + 60)
                    tprint(f"[TimeoutWaitMiddleware] 📊 Extracted retry delay: {extracted_delay:.2f}s (will wait {wait_time}s = delay + 60s)")
                else:
                    # Fall back to exponential backoff if we can't extract the delay
                    wait_time = self._calculate_wait_time(attempt)
                    tprint(f"[TimeoutWaitMiddleware] 📊 Using exponential backoff: {wait_time}s")

                # Cap at max_wait_seconds
                wait_time = min(wait_time, self.max_wait_seconds)

                # Log the retry attempt
                tprint(f"[TimeoutWaitMiddleware] ⏳ Rate limit detected (attempt {attempt + 1}/{self.max_retries + 1})")
                tprint(f"[TimeoutWaitMiddleware] 😴 Waiting {wait_time} seconds before retry...")
                tprint(f"[TimeoutWaitMiddleware] 📋 Error: {str(e)[:150]}")

                # Wait before retrying
                time.sleep(wait_time)

                tprint(f"[TimeoutWaitMiddleware] 🔄 Retrying model call now...")
                self._retry_count += 1

        # This should never be reached, but just in case
        if last_error:
            raise last_error

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        """
        Tool calls typically don't hit rate limits, so just pass through.

        Args:
            request: The tool call request
            handler: The handler function to execute the actual tool call

        Returns:
            The tool execution result
        """
        return handler(request)
