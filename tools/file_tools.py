"""
File operation tools for GameStudio 1984 v0.6.
Optimized docstrings with essential error handling info.
"""

import os
from typing import Optional
from langchain_core.tools import tool

# Import implementations from file_tools_impl
from .file_tools_impl import (
    read_file_impl,
    read_binary_file_impl,
    file_edit_impl,
    replace_file_impl,
    ls_dir_impl,
    glob_search_impl,
    grep_search_impl,
    write_file_impl,
    copy_file_impl,
    copy_dir_impl,
    sed_edit_impl,
)

# Global variable to hold the current PROJECT_ROOT for tools
_CURRENT_PROJECT_ROOT = None

def set_project_root(project_root: str) -> None:
    """Set the PROJECT_ROOT for all file operation tools."""
    global _CURRENT_PROJECT_ROOT
    _CURRENT_PROJECT_ROOT = project_root
    os.environ["PROJECT_ROOT"] = project_root

def _get_project_root() -> str:
    """Get PROJECT_ROOT from global variable, environment, or default."""
    if _CURRENT_PROJECT_ROOT is not None:
        return _CURRENT_PROJECT_ROOT
    return os.environ.get("PROJECT_ROOT", "/")


@tool
def file_edit(file_path: str, old_string: str, new_string: str) -> str:
    """
    Replace a single, exact occurrence of a string in a file.

    Args:
        file_path: Project-relative path (e.g., "/public/game.js")
        old_string: Exact text to find (character-for-character match)
        new_string: Replacement text

    Returns:
        Success message or error

    Errors:
        - "ERROR: File not found" - file doesn't exist
        - "ERROR: String not found" - old_string not in file
        - "ERROR: Multiple matches" - use sed_edit() instead

    Tip: Copy exact text from read_file() output to ensure match.

    Example:
        file_edit("/public/game.js", 'score = 0', 'score = 100')
    """
    return file_edit_impl(_get_project_root(), file_path, old_string, new_string, error_tracker=None)


@tool
def read_file(file_path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Read file content with line numbers.

    Args:
        file_path: Project-relative path (e.g., "/public/game.js")
        start_line: Optional 1-indexed start line
        end_line: Optional 1-indexed end line

    Returns:
        File content with line numbers, or error message

    Example:
        read_file("/public/game.js")
        read_file("/public/game.js", start_line=10, end_line=20)
    """
    return read_file_impl(_get_project_root(), file_path, start_line, end_line)


@tool
def inspect_image(file_path: str) -> str:
    """
    Read a PNG image file to analyze its content/dimensions.
    Use to verify generated sprites match expectations.

    Args:
        file_path: Project-relative path (e.g., "/public/assets/images/player.png")

    Returns:
        Image data for visual inspection
    """
    return read_binary_file_impl(_get_project_root(), file_path)


@tool
def inspect_audio(file_path: str) -> str:
    """
    Read a WAV audio file to analyze its content.
    Use to verify generated sound effects.

    Args:
        file_path: Project-relative path (e.g., "/public/assets/sounds/shoot.wav")

    Returns:
        Audio data for analysis
    """
    return read_binary_file_impl(_get_project_root(), file_path)


@tool
def replace_file(file_path: str, content: str) -> str:
    """
    Overwrite entire file content (create or replace).
    Use when file_edit fails or for complete rewrites.

    Args:
        file_path: Project-relative path (e.g., "/public/game.js")
        content: New file content

    Returns:
        Success message or error

    Example:
        replace_file("/public/game.js", "class Game extends GameEngine { ... }")
    """
    return replace_file_impl(_get_project_root(), file_path, content)


@tool
def write_file(file_path: str, content: str) -> str:
    """
    Create a NEW file (fails if file exists).

    Args:
        file_path: Project-relative path (e.g., "/work/design.json")
        content: File content

    Returns:
        Success message or error

    Example:
        write_file("/work/design.json", '{"name": "Space Shooter"}')
    """
    return write_file_impl(_get_project_root(), file_path, content)


@tool
def mv_file(src: str, dst: str) -> str:
    """
    Move or rename a file.

    Args:
        src: Source path
        dst: Destination path

    Returns:
        Success message or error

    Example:
        mv_file("/public/old.js", "/public/new.js")
    """
    import shutil
    try:
        src_full = os.path.join(_get_project_root(), src.lstrip("/"))
        dst_full = os.path.join(_get_project_root(), dst.lstrip("/"))
        dst_dir = os.path.dirname(dst_full)
        if dst_dir and not os.path.exists(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
        shutil.move(src_full, dst_full)
        return f"Moved {src} to {dst}"
    except Exception as e:
        return f"ERROR: Could not move {src} to {dst}: {e}"


@tool
def copy_file(source_path: str, dest_path: str) -> str:
    """
    Copy a single file.

    Args:
        source_path: Source file path
        dest_path: Destination file path

    Returns:
        Success message or error

    Example:
        copy_file("/templates/game.js", "/public/game.js")
    """
    return copy_file_impl(_get_project_root(), source_path, dest_path)


@tool
def copy_dir(source_dir: str, dest_dir: str, overwrite: bool = False) -> str:
    """
    Copy an entire directory tree.

    Args:
        source_dir: Source directory path
        dest_dir: Destination directory path
        overwrite: Whether to overwrite existing files

    Returns:
        Success message or error
    """
    return copy_dir_impl(_get_project_root(), source_dir, dest_dir, overwrite)


@tool
def list_directory(path: str = "/", recursive: bool = False) -> str:
    """
    List files and directories.

    Args:
        path: Directory path (default: "/")
        recursive: Whether to list recursively

    Returns:
        Directory listing or error

    Example:
        list_directory("/public/assets/images")
    """
    detailed = False
    return ls_dir_impl(_get_project_root(), path, detailed)


@tool
def glob_search(pattern: str) -> str:
    """
    Find files using glob pattern (wildcards).

    Args:
        pattern: Glob pattern (e.g., "**/*.js", "assets/*.png")

    Returns:
        List of matching file paths

    Example:
        glob_search("**/*.js")       # All JS files
        glob_search("assets/**/*.png")  # All PNGs in assets
    """
    return glob_search_impl(_get_project_root(), pattern)


@tool
def sed_edit(
    file_path: str,
    pattern: str,
    replacement: str,
    global_replace: bool = False
) -> str:
    """
    Regex-based find and replace.
    Use when file_edit fails due to multiple matches.

    Args:
        file_path: Project-relative path
        pattern: Regex pattern (Python re syntax)
        replacement: Replacement string (\\1 for capture groups)
        global_replace: Replace all matches if True

    Returns:
        Success message or error

    Examples:
        # Replace first match
        sed_edit("/public/game.js", r"var (\\w+)", r"const \\1")

        # Replace all matches
        sed_edit("/public/game.js", r"oldName", "newName", global_replace=True)
    """
    return sed_edit_impl(
        _get_project_root(), file_path, pattern, replacement,
        global_replace=global_replace, error_tracker=None
    )


@tool
def grep_search(pattern: str, path: str = "/", file_type: str = None) -> str:
    """
    Search file contents using regex.

    Args:
        pattern: Regex pattern to search
        path: Search root directory or specific file path
        file_type: Extension filter (e.g., "js", "json")

    Returns:
        Matches with file paths and line numbers

    Example:
        grep_search("class Game", path="/public", file_type="js")
        grep_search("collides", path="/public/game.js")
    """
    # Determine file_pattern based on path and file_type
    if file_type:
        # If file_type is specified, combine with path
        if path.endswith(f".{file_type}"):
            # path is already a specific file
            file_pattern = path
        else:
            # path is a directory, add file_type filter
            file_pattern = f"{path.rstrip('/')}/**/*.{file_type}"
    else:
        # No file_type specified
        if path.endswith(('.js', '.py', '.json', '.md', '.txt', '.html', '.css')):
            # path looks like a specific file
            file_pattern = path
        elif path == "/":
            # Root search
            file_pattern = "**/*"
        else:
            # Directory search
            file_pattern = f"{path.rstrip('/')}/**/*"

    return grep_search_impl(_get_project_root(), pattern, file_pattern, context_lines=0, ignore_case=False)


@tool
def file_exists(file_path: str) -> str:
    """
    Check if file or directory exists.

    Args:
        file_path: Project-relative path

    Returns:
        "EXISTS" or "NOT_FOUND"

    Example:
        file_exists("/public/game.js")
    """
    try:
        full_path = os.path.join(_get_project_root(), file_path.lstrip("/"))
        if os.path.exists(full_path):
            return "EXISTS"
        else:
            return "NOT_FOUND"
    except Exception as e:
        return f"ERROR: {e}"


__all__ = [
    'file_edit',
    'sed_edit',
    'replace_file',
    'read_file',
    'inspect_image',
    'inspect_audio',
    'mv_file',
    'copy_file',
    'copy_dir',
    'list_directory',
    'glob_search',
    'grep_search',
    'write_file',
    'file_exists',
    'set_project_root',
]
