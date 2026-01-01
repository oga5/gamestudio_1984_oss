"""
File permission system for agent tools.

Controls which files each agent role can write to.
All roles can read any file, but write operations are restricted by patterns.
"""
import os
import re
import json
from pathlib import Path
from typing import List, Callable, Optional
from functools import wraps
import fnmatch


class FilePermissions:
    """Manage file write permissions for agents."""

    def __init__(self, writable_patterns: List[str]):
        """
        Initialize file permissions with writable patterns.

        Args:
            writable_patterns: List of glob patterns for writable paths
                              e.g., ["/work/*.json", "/public/**/*"]
                              Patterns starting with / are relative to project root
        """
        self.writable_patterns = writable_patterns

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for matching (remove leading /)."""
        return file_path.lstrip("/")

    def _pattern_matches(self, normalized_path: str, pattern: str) -> bool:
        """
        Check if a normalized path matches a pattern.

        Supports:
        - Simple wildcards: /work/*.json
        - Recursive wildcards: /public/**/*
        - Directory patterns: /public/assets/images/
        """
        pattern_normalized = self._normalize_path(pattern)

        # Handle ** recursive wildcard
        if "**" in pattern_normalized:
            # Convert ** to match any path segment
            # /public/**/* means /public/ followed by anything
            parts = pattern_normalized.split("**")
            if len(parts) == 2:
                prefix = parts[0].rstrip("/")
                suffix = parts[1].lstrip("/")

                # Check if path starts with prefix
                if prefix and not normalized_path.startswith(prefix):
                    return False

                # Check if path ends with suffix pattern
                if suffix and suffix != "*":
                    # Get the part after prefix
                    if prefix:
                        remaining = normalized_path[len(prefix):].lstrip("/")
                    else:
                        remaining = normalized_path

                    # Use fnmatch for the suffix
                    if not fnmatch.fnmatch(remaining, suffix):
                        return False

                return True

        # Simple glob pattern matching (shell-like: * does NOT match /)
        # Convert the pattern to regex that prevents * from matching /
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern_normalized)
        # Unescape * and ? for glob matching
        escaped = escaped.replace(r'\*', '[^/]*')  # * matches anything except /
        escaped = escaped.replace(r'\?', '[^/]')   # ? matches any single char except /
        # Anchors to ensure full path match
        regex = f'^{escaped}$'

        return bool(re.match(regex, normalized_path))

    def is_writable(self, file_path: str) -> bool:
        """
        Check if file path is writable according to patterns.

        Args:
            file_path: File path to check (e.g., "/public/game.js")

        Returns:
            True if path matches any writable pattern, False otherwise
        """
        normalized = self._normalize_path(file_path)

        for pattern in self.writable_patterns:
            if self._pattern_matches(normalized, pattern):
                return True

        return False

    def check_permission(self, file_path: str, operation: str) -> None:
        """
        Check if operation is allowed on file_path.

        Args:
            file_path: File path to check
            operation: Operation name (for error message)

        Raises:
            PermissionError: If operation is not allowed
        """
        if not self.is_writable(file_path):
            raise PermissionError(
                f"Permission denied: Cannot {operation} '{file_path}'\n"
                f"This agent can only write to: {', '.join(self.writable_patterns)}"
            )


def create_permission_wrapper(tool_func: Callable, permissions: FilePermissions) -> Callable:
    """
    Wrap a file tool with permission checks.

    Args:
        tool_func: Original tool function
        permissions: FilePermissions instance

    Returns:
        Wrapped function with permission checks
    """
    @wraps(tool_func)
    def wrapper(*args, **kwargs):
        # Extract file_path from args or kwargs
        file_path = None

        # Common parameter names for file paths
        file_path_params = ['file_path', 'output_path', 'dest_path', 'dst']

        # Check kwargs first
        for param_name in file_path_params:
            if param_name in kwargs:
                file_path = kwargs[param_name]
                break

        # If not in kwargs, check args (assume first arg is file_path for write operations)
        if file_path is None and len(args) > 0:
            # For most file tools, first argument is the file path
            file_path = args[0]

        # Check permission if we have a file path
        if file_path:
            operation = tool_func.__name__
            try:
                permissions.check_permission(file_path, operation)
            except PermissionError as e:
                return f"ERROR: {e}"

        # Call original function
        return tool_func(*args, **kwargs)

    # Preserve tool metadata for langchain
    wrapper.__name__ = tool_func.__name__
    wrapper.__doc__ = tool_func.__doc__
    if hasattr(tool_func, '__annotations__'):
        wrapper.__annotations__ = tool_func.__annotations__

    return wrapper


# ============================================================================
# Default Permission Configurations
# ============================================================================

# Based on task analysis in system_prompt/tasks/*/
DEFAULT_PERMISSIONS = {
    "manager": [
        "/work/workflow.json",           # generate_workflow task
        "/work/*.json",                  # Other workflow-related files
    ],

    "designer": [
        "/work/design.json",             # create_game_concept task
        "/work/asset_spec.json",         # create_asset_list task
        "/work/game_concept.json",       # Alternative naming
        "/work/*.json",                  # Other design files
    ],

    "programmer": [
        "/public/index.html",            # implement_game task (HTML structure)
        "/public/style.css",             # implement_game task (CSS styling)
        "/public/game.js",               # implement_game, fix_bugs, improve_game tasks
        "/public/**/*",                  # All files under /public for flexibility
    ],

    "graphic_artist": [
        "/public/assets/images/**/*",    # generate_sprites task (PNG files)
        "/work/sprite/**/*",             # Sprite JSON specifications
    ],

    "sound_artist": [
        "/public/assets/sounds/**/*",    # generate_sounds task (WAV files)
        "/work/sound/**/*",              # Sound JSON specifications
    ],

    "tester": [
        "/work/test/**/*",               # Test results in numbered directories (001/, 002/, etc.)
        "/public/index.html",            # Limited: Quick fixes (canvas element, etc.)
    ],
}


def load_permissions_from_config(config_path: str) -> dict:
    """
    Load permission overrides from config.json.

    Args:
        config_path: Path to config.json file

    Returns:
        Dictionary of role -> permission config, or empty dict if no config
    """
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get("file_permissions", {})
    except Exception as e:
        print(f"Warning: Could not load permissions from config.json: {e}")
        return {}


def create_role_permissions(config_path: Optional[str] = None) -> dict:
    """
    Create FilePermissions instances for each role.

    Merges default permissions with config.json overrides.

    Args:
        config_path: Path to config.json (optional)

    Returns:
        Dictionary mapping role name to FilePermissions instance
    """
    # Start with defaults
    permissions_config = DEFAULT_PERMISSIONS.copy()

    # Override with config.json if available
    if config_path:
        config_overrides = load_permissions_from_config(config_path)

        for role, config in config_overrides.items():
            if "writable_patterns" in config:
                # Override completely (not merge)
                permissions_config[role] = config["writable_patterns"]

    # Create FilePermissions instances
    role_permissions = {}
    for role, patterns in permissions_config.items():
        role_permissions[role] = FilePermissions(patterns)

    return role_permissions


def get_tools_with_permissions(base_tools: List, role: str, config_path: Optional[str] = None) -> List:
    """
    Create permission-wrapped tools for a specific role.

    Args:
        base_tools: List of base tool functions
        role: Role name (e.g., "programmer", "manager")
        config_path: Path to config.json (optional)

    Returns:
        List of tools with permission wrappers applied to write operations
    """
    # Get permissions for this role
    all_permissions = create_role_permissions(config_path)
    permissions = all_permissions.get(role)

    if not permissions:
        # No permissions defined = full access (backward compatible)
        return base_tools

    # Tools that need permission wrapping (write operations)
    WRITE_TOOLS = {
        'file_edit',
        'sed_edit',
        'replace_file',
        'write_file',
        'mv_file',
        'copy_file',
        'copy_dir',
        'edit_json_item',
    }

    wrapped_tools = []
    for tool in base_tools:
        tool_name = getattr(tool, '__name__', str(tool))

        if tool_name in WRITE_TOOLS:
            # Wrap with permission check
            wrapped = create_permission_wrapper(tool, permissions)
            wrapped_tools.append(wrapped)
        else:
            # No wrapping needed (read-only tools)
            wrapped_tools.append(tool)

    return wrapped_tools


# ============================================================================
# Utility Functions
# ============================================================================

def test_permissions():
    """Test permission system with example paths."""
    print("Testing File Permission System\n")

    for role, patterns in DEFAULT_PERMISSIONS.items():
        print(f"\n{role.upper()}:")
        print(f"  Patterns: {patterns}")

        perms = FilePermissions(patterns)

        # Test cases
        test_paths = [
            "/work/workflow.json",
            "/work/design.json",
            "/public/game.js",
            "/public/index.html",
            "/public/assets/images/player.png",
            "/public/assets/sounds/shoot.wav",
            "/work/test_report.json",
            "/secret/config.json",
        ]

        print("  Writable paths:")
        for path in test_paths:
            if perms.is_writable(path):
                print(f"    ✓ {path}")


if __name__ == "__main__":
    # Run tests when module is executed directly
    test_permissions()
