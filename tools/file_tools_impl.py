#!/usr/bin/env python3
"""
Custom File Operation Tools - Complete FileMiddleware Replacement Implementation

File operation toolset optimized for project-specific needs without dependency
on DeepAgents' FileMiddleware.

Main Features:
- file_edit: Simple exact-match file editing
- sed_edit: Stream editing (regex-based)
- replace_file: Full file replacement
- read_file: Extended file reading (with line range support)
- ls_dir: Directory listing
- glob_search: Pattern matching
- grep_search: File content search
"""

import os
import re
import json
import glob as glob_module
import hashlib
import base64
from typing import Optional, Any


# =====================================================
# Utility Functions
# =====================================================

def normalize_path_safe(file_path: str, project_root: str) -> tuple[str, str]:
    """
    Safely normalize path and return relative and absolute paths

    Security measures:
    - Immediately reject paths containing '../' (Path Traversal attack prevention)
    - Resolve symbolic links with os.path.realpath()
    - Verify result path is within project_root

    Returns:
        (relative_path, absolute_path)

    Raises:
        ValueError: When Path Traversal or access outside project_root is detected
    """
    # Remove leading /
    if file_path.startswith("/"):
        file_path = file_path[1:]

    # Path Traversal check: immediately error if '../' detected
    if "../" in file_path or file_path.endswith(".."):
        raise ValueError(f"Access denied: Path traversal detected in '{file_path}'")

    # Build absolute path within project_root
    full_path = os.path.join(project_root, file_path)

    # Normalize (resolve symbolic links)
    real_full = os.path.realpath(full_path)
    real_root = os.path.realpath(project_root)

    # Verify it's within project_root
    try:
        rel = os.path.relpath(real_full, real_root)
        if rel.startswith(".."):
            raise ValueError(f"Access denied: Path is outside project_root")
    except ValueError as e:
        # In case of different drives, etc.
        raise ValueError(f"Access denied: Invalid path")

    return file_path, real_full


def normalize_path(file_path: str, project_root: str) -> tuple[str, str]:
    """
    [DEPRECATED] Use normalize_path_safe instead

    Normalize path and return relative and absolute paths

    Returns:
        (relative_path, absolute_path)
    """
    # Remove leading /
    if file_path.startswith("/"):
        file_path = file_path[1:]

    full_path = os.path.join(project_root, file_path)
    return file_path, full_path


def create_backup(file_path: str) -> Optional[str]:
    """Create a backup of the file"""
    if not os.path.exists(file_path):
        return None

    backup_path = f"{file_path}.backup"
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception:
        return None


# =====================================================
# Core Tool Implementations
# =====================================================

def read_file_impl(
    project_root: str,
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None
) -> str:
    """
    Extended file reading with line range support (start, end, full)

    Read file content with flexible line range options. Supports reading the entire file,
    from a specific line to the end, or a specific range of lines. All line numbers are
    1-indexed (first line is 1, not 0).

    Security:
        - Uses normalize_path_safe() to prevent path traversal attacks
        - Blocks access to files outside project_root
        - Validates line ranges before reading

    Args:
        project_root: Project root directory (automatically provided)
        file_path: File path relative to project root (e.g., "/work/file.txt")
        start_line: Starting line number (1-indexed). If None, reads from beginning
        end_line: Ending line number (1-indexed, inclusive). If None, reads to end

    Returns:
        String containing the file content with metadata header, or error message

    Examples:
        >>> read_file("/work/file.txt")
        # Reads entire file from beginning to end

        >>> read_file("/work/file.txt", 10)
        # Reads from line 10 to end of file

        >>> read_file("/work/file.txt", 10, 20)
        # Reads lines 10 through 20 (inclusive)

    Error Handling:
        - Returns error if file doesn't exist
        - Returns error if line numbers are out of range
        - Returns error if path traversal is detected
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(full_path):
        return f"❌ Error: File not found: {rel_path}"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # No arguments → entire file
        if start_line is None and end_line is None:
            content = ''.join(lines)
            return f"File: {rel_path} (Total: {total_lines} lines)\n{'='*60}\n{content}"

        # Start position only → from start to end
        if start_line is not None and end_line is None:
            if start_line < 1 or start_line > total_lines:
                return f"❌ Error: start_line {start_line} out of range (1-{total_lines})"
            content = ''.join(lines[start_line-1:])
            return f"File: {rel_path} (Lines {start_line}-{total_lines})\n{'='*60}\n{content}"

        # end_line only → read from beginning to end_line
        if start_line is None and end_line is not None:
            if end_line < 1 or end_line > total_lines:
                return f"❌ Error: end_line {end_line} out of range (1-{total_lines})"
            content = ''.join(lines[:end_line])
            return f"File: {rel_path} (Lines 1-{end_line})\n{'='*60}\n{content}"

        # Range specified
        if start_line is not None and end_line is not None:
            if start_line < 1 or start_line > total_lines:
                return f"❌ Error: start_line {start_line} out of range (1-{total_lines})"
            if end_line < start_line or end_line > total_lines:
                return f"❌ Error: end_line {end_line} invalid (must be >= {start_line} and <= {total_lines})"

            content = ''.join(lines[start_line-1:end_line])
            return f"File: {rel_path} (Lines {start_line}-{end_line})\n{'='*60}\n{content}"

        return f"❌ Error: Invalid arguments"

    except Exception as e:
        return f"❌ Error: {e}"


def read_binary_file_impl(
    project_root: str,
    file_path: str
) -> str:
    """
    Read binary file (PNG, WAV, etc.) and return as base64.

    Args:
        project_root: Project root directory
        file_path: File path relative to project root

    Returns:
        String containing base64 data and metadata, or error message
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(full_path):
        return f"❌ Error: File not found: {rel_path}"

    try:
        with open(full_path, 'rb') as f:
            binary_data = f.read()

        base64_data = base64.b64encode(binary_data).decode('utf-8')
        file_size = len(binary_data)

        # Detect mime type based on extension
        ext = os.path.splitext(rel_path)[1].lower()
        mime_type = "application/octet-stream"
        if ext == ".png":
            mime_type = "image/png"
        elif ext == ".wav":
            mime_type = "audio/wav"

        return f"FILE_BINARY:{rel_path}:{mime_type}:{file_size}:{base64_data}"

    except Exception as e:
        return f"❌ Error: {e}"


def inspect_image_metadata_impl(
    project_root: str,
    file_path: str
) -> str:
    """
    Get PNG image dimensions and basic info without base64 encoding.

    Returns metadata only, saving tokens compared to full base64 encoding.

    Args:
        project_root: Project root directory
        file_path: File path relative to project root

    Returns:
        String containing image metadata (dimensions, file size), or error message
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(full_path):
        return f"❌ Error: File not found: {rel_path}"

    try:
        with open(full_path, 'rb') as f:
            # Read PNG header to get dimensions
            # PNG format: 8-byte signature + IHDR chunk
            signature = f.read(8)

            # Verify PNG signature
            if signature != b'\x89PNG\r\n\x1a\n':
                return f"❌ Error: Not a valid PNG file: {rel_path}"

            # Read IHDR chunk (first chunk after signature)
            # Skip chunk length (4 bytes)
            f.read(4)
            # Verify chunk type is IHDR
            chunk_type = f.read(4)
            if chunk_type != b'IHDR':
                return f"❌ Error: Invalid PNG structure: {rel_path}"

            # Read width and height (4 bytes each, big-endian)
            width_bytes = f.read(4)
            height_bytes = f.read(4)

            width = int.from_bytes(width_bytes, byteorder='big')
            height = int.from_bytes(height_bytes, byteorder='big')

        # Get file size
        file_size = os.path.getsize(full_path)

        return f"✅ Image: {rel_path}\n   Dimensions: {width}x{height}\n   File size: {file_size} bytes"

    except Exception as e:
        return f"❌ Error: {e}"


def inspect_audio_metadata_impl(
    project_root: str,
    file_path: str
) -> str:
    """
    Get WAV audio metadata and silence detection without base64 encoding.

    Analyzes audio to detect silence and provide basic metadata,
    saving tokens compared to full base64 encoding.

    Args:
        project_root: Project root directory
        file_path: File path relative to project root

    Returns:
        String containing audio metadata (duration, silence status, peak amplitude), or error message
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(full_path):
        return f"❌ Error: File not found: {rel_path}"

    try:
        with open(full_path, 'rb') as f:
            # Read WAV header
            # RIFF header
            riff = f.read(4)
            if riff != b'RIFF':
                return f"❌ Error: Not a valid WAV file: {rel_path}"

            file_size_header = f.read(4)
            wave = f.read(4)
            if wave != b'WAVE':
                return f"❌ Error: Not a valid WAV file: {rel_path}"

            # Find fmt chunk
            while True:
                chunk_id = f.read(4)
                if not chunk_id:
                    return f"❌ Error: Invalid WAV structure: {rel_path}"

                chunk_size = int.from_bytes(f.read(4), byteorder='little')

                if chunk_id == b'fmt ':
                    # Read format chunk
                    audio_format = int.from_bytes(f.read(2), byteorder='little')
                    num_channels = int.from_bytes(f.read(2), byteorder='little')
                    sample_rate = int.from_bytes(f.read(4), byteorder='little')
                    byte_rate = int.from_bytes(f.read(4), byteorder='little')
                    block_align = int.from_bytes(f.read(2), byteorder='little')
                    bits_per_sample = int.from_bytes(f.read(2), byteorder='little')

                    # Skip any extra format bytes
                    if chunk_size > 16:
                        f.read(chunk_size - 16)
                    break
                else:
                    # Skip this chunk
                    f.read(chunk_size)

            # Find data chunk
            while True:
                chunk_id = f.read(4)
                if not chunk_id:
                    return f"❌ Error: No data chunk found: {rel_path}"

                chunk_size = int.from_bytes(f.read(4), byteorder='little')

                if chunk_id == b'data':
                    # Read audio data
                    audio_data = f.read(chunk_size)
                    break
                else:
                    # Skip this chunk
                    f.read(chunk_size)

            # Calculate duration
            num_samples = len(audio_data) // (num_channels * (bits_per_sample // 8))
            duration = num_samples / sample_rate

            # Analyze for silence (check peak amplitude)
            max_amplitude = 0
            bytes_per_sample = bits_per_sample // 8

            # Sample every 100th frame to save processing time
            for i in range(0, len(audio_data) - bytes_per_sample, bytes_per_sample * 100):
                if bytes_per_sample == 1:
                    # 8-bit unsigned
                    sample = audio_data[i] - 128
                    max_amplitude = max(max_amplitude, abs(sample))
                elif bytes_per_sample == 2:
                    # 16-bit signed
                    sample = int.from_bytes(audio_data[i:i+2], byteorder='little', signed=True)
                    max_amplitude = max(max_amplitude, abs(sample))

            # Determine if silent (threshold: less than 1% of max amplitude)
            max_possible = (2 ** (bits_per_sample - 1)) - 1
            peak_ratio = max_amplitude / max_possible if max_possible > 0 else 0
            is_silent = peak_ratio < 0.01

            silence_status = "⚠️ SILENT" if is_silent else "✅ NOT_SILENT"

        # Get file size
        file_size = os.path.getsize(full_path)

        return (
            f"✅ Audio: {rel_path}\n"
            f"   Duration: {duration:.3f}s\n"
            f"   Sample rate: {sample_rate} Hz\n"
            f"   Channels: {num_channels}\n"
            f"   Bits per sample: {bits_per_sample}\n"
            f"   Peak amplitude: {peak_ratio:.2%}\n"
            f"   Status: {silence_status}\n"
            f"   File size: {file_size} bytes"
        )

    except Exception as e:
        return f"❌ Error: {e}"


def file_edit_impl(
    project_root: str,
    file_path: str,
    old_string: str,
    new_string: str,
    error_tracker: Any = None
) -> str:
    """
    Simple exact-match file editing (no fuzzy matching).

    Replaces old_string with new_string ONLY if:
    - old_string is found EXACTLY once in the file
    - No whitespace normalization applied
    - Character-by-character exact match required

    Security:
        - Uses normalize_path_safe() to prevent path traversal
        - Creates automatic backups before editing
        - Validates file existence before editing

    Args:
        project_root: Project root directory (automatically provided)
        file_path: File path relative to project root (e.g., "/public/game.js")
        old_string: Exact text to find (must match character-for-character)
        new_string: Replacement text
        error_tracker: Optional error tracking

    Returns:
        Success message or clear error

    Error Cases:
        - "❌ Error: File not found" - file doesn't exist
        - "❌ Error: String not found" - old_string is not in file
        - "❌ Error: Multiple matches found" - ambiguous (use sed_edit for patterns)
    """
    # Validate: old_string and new_string must be different
    if old_string == new_string:
        error_msg = f"❌ Error: old_string and new_string are identical. No changes needed."
        if error_tracker:
            error_tracker.record_error("file_edit", {"file_path": file_path}, error_msg)
        return error_msg

    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        error_msg = f"❌ Error: {e}"
        if error_tracker:
            error_tracker.record_error("file_edit", {"file_path": file_path}, error_msg)
        return error_msg

    if not os.path.exists(full_path):
        error_msg = f"❌ Error: File not found: {rel_path}"
        if error_tracker:
            error_tracker.record_error("file_edit", {"file_path": file_path}, error_msg)
        return error_msg

    try:
        # Read file
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Count matches
        match_count = original_content.count(old_string)

        if match_count == 0:
            # String not found - provide helpful context by showing similar content
            lines = original_content.split('\n')
            # Find lines that might be similar (contain some words from old_string)
            old_words = set(old_string.split()[:5])  # First 5 words
            similar_lines = []
            for i, line in enumerate(lines, 1):
                line_words = set(line.split())
                if old_words & line_words:  # Intersection
                    similar_lines.append((i, line))
                if len(similar_lines) >= 3:
                    break

            hint = ""
            if similar_lines:
                hint = "\n\n💡 HINT - Similar lines found (use read_file to verify current content):"
                for line_num, line_text in similar_lines:
                    hint += f"\n  Line {line_num}: {line_text[:80]}..."

            error_msg = f"❌ Error: String not found in {rel_path}{hint}\n\n🔍 TIP: Call read_file(\"{file_path}\") to see current file content."
            if error_tracker:
                error_tracker.record_error(
                    "file_edit",
                    {"file_path": file_path, "old_string": old_string},
                    error_msg
                )
            return error_msg

        if match_count > 1:
            error_msg = f"❌ Error: Multiple matches found ({match_count}) in {rel_path}. Use sed_edit() for pattern-based replacement."
            if error_tracker:
                error_tracker.record_error(
                    "file_edit",
                    {"file_path": file_path, "old_string": old_string},
                    error_msg
                )
            return error_msg

        # Create backup
        create_backup(full_path)

        # Replace (exactly once)
        new_content = original_content.replace(old_string, new_string, 1)

        # Write to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        if error_tracker:
            error_tracker.record_success("file_edit")

        return f"✅ File edited: {rel_path}"

    except Exception as e:
        error_msg = f"❌ Error: {e}"
        if error_tracker:
            error_tracker.record_error(
                "file_edit",
                {"file_path": file_path, "old_string": old_string},
                error_msg
            )
        return error_msg


def ls_dir_impl(project_root: str, dir_path: str = "/", detailed: bool = False) -> str:
    """
    Directory listing with detailed mode

    List directory contents with optional detailed information including file sizes and
    modification times. Directories are marked with trailing slash for easy identification.

    Security:
        - Uses normalize_path_safe() to prevent path traversal attacks
        - Only lists contents within project_root
        - Validates directory existence before listing

    Args:
        project_root: Project root directory (automatically provided)
        dir_path: Directory path relative to project root (default: "/" = project root)
        detailed: If True, shows file sizes and modification times (default: False)

    Returns:
        Formatted directory listing with file/directory entries, or error message

    Output Format (detailed=False):
        Directory: /path
        ============================================================
          file1.txt
          file2.json
          subdirectory/

    Output Format (detailed=True):
        Directory: /path
        ============================================================
        [FILE] 2025-12-11 14:30      1024 file1.txt
        [FILE] 2025-12-11 14:35       512 file2.json
        [DIR]  2025-12-11 14:00            subdirectory/

    Examples:
        >>> ls_dir("/work")
        # Lists files and directories in /work

        >>> ls_dir("/", detailed=True)
        # Lists project root with sizes and timestamps

        >>> ls_dir("/src/components")
        # Lists contents of src/components directory

    Error Handling:
        - Returns error if directory doesn't exist
        - Returns error if path is a file, not a directory
        - Returns error if path traversal is detected
    """
    try:
        rel_path, full_path = normalize_path_safe(dir_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(full_path):
        return f"❌ Error: Directory not found: {rel_path}"

    if not os.path.isdir(full_path):
        return f"❌ Error: Not a directory: {rel_path}"

    try:
        items = sorted(os.listdir(full_path))

        if not items:
            return f"Directory {rel_path} is empty"

        lines = [f"Directory: {rel_path}", "=" * 60]

        for item in items:
            item_path = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_path)

            if detailed:
                size = os.path.getsize(item_path) if not is_dir else 0
                mtime = os.path.getmtime(item_path)
                from datetime import datetime
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

                if is_dir:
                    lines.append(f"[DIR]  {mtime_str}            {item}/")
                else:
                    lines.append(f"[FILE] {mtime_str}  {size:>10} {item}")
            else:
                if is_dir:
                    lines.append(f"  {item}/")
                else:
                    lines.append(f"  {item}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error: {e}"


def glob_search_impl(project_root: str, pattern: str) -> str:
    """
    Pattern-based file searching

    Search for files using glob patterns with support for recursive matching. Returns a
    sorted list of all files and directories matching the pattern within the project root.

    Pattern Syntax:
        * - Matches any characters except /
        ** - Matches any characters including / (recursive)
        ? - Matches any single character
        [seq] - Matches any character in seq
        [!seq] - Matches any character not in seq

    Security:
        - Blocks path traversal patterns (../)
        - Only searches within project_root
        - Validates pattern before execution

    Args:
        project_root: Project root directory (automatically provided)
        pattern: Glob pattern (e.g., "**/*.js", "work/*.json", "src/**/*.py")

    Returns:
        Formatted list of matching files/directories with total count, or error message

    Output Format:
        Files matching 'pattern':
        ============================================================
          path/to/file1.js
          path/to/file2.js
          directory/

        Total: 3 items

    Examples:
        >>> glob_search("**/*.js")
        # Finds all JavaScript files recursively

        >>> glob_search("work/*.json")
        # Finds JSON files in work directory (non-recursive)

        >>> glob_search("src/**/*.py")
        # Finds all Python files under src/ recursively

        >>> glob_search("public/images/*.png")
        # Finds PNG images in public/images

        >>> glob_search("js/screens/title.js")
        # Finds title.js anywhere under js/screens/ (auto-adds **/ prefix)
        # Matches: public/js/screens/title.js, src/js/screens/title.js, etc.

        >>> glob_search("config.json")
        # Finds config.json anywhere in the project (auto-adds **/ prefix)
        # Matches: work/config.json, public/config.json, etc.

    Auto-Prefix Behavior:
        - Patterns WITHOUT wildcards (* or ?) automatically get **/ prefix
        - "js/screens/title.js" → searches as "**/js/screens/title.js"
        - Patterns WITH wildcards are used as-is
        - "**/*.js" → searches exactly as "**/*.js"

    Common Patterns:
        - "**/*" - All files recursively
        - "*.txt" - Text files in root only
        - "src/**/*.ts" - TypeScript files in src
        - "**/test_*.py" - Test files anywhere
        - "components/Button.jsx" - Button.jsx anywhere under components/

    Error Handling:
        - Returns error if path traversal is detected
        - Returns "No files found" if pattern matches nothing
        - Handles glob errors gracefully
    """
    try:
        # Path Traversal check
        if "../" in pattern or pattern.endswith(".."):
            return "❌ Error: Access denied: Path traversal detected in pattern"

        # Relative pattern from project root
        if pattern.startswith("/"):
            pattern = pattern[1:]

        # Auto-enable partial path matching
        # If pattern doesn't contain * or **, prepend **/
        original_pattern = pattern
        if '*' not in pattern and '?' not in pattern:
            pattern = f"**/{pattern}"

        full_pattern = os.path.join(project_root, pattern)
        matches = glob_module.glob(full_pattern, recursive=True)

        # Convert to relative paths
        rel_matches = []
        for match in matches:
            rel_path = os.path.relpath(match, project_root)
            rel_matches.append(rel_path)

        if not rel_matches:
            return f"No files found matching pattern: {original_pattern}"

        lines = [f"Files matching '{original_pattern}':", "=" * 60]
        for match in sorted(rel_matches):
            is_dir = os.path.isdir(os.path.join(project_root, match))
            if is_dir:
                lines.append(f"  {match}/")
            else:
                lines.append(f"  {match}")

        lines.append("")
        lines.append(f"Total: {len(rel_matches)} items")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error: {e}"


def grep_search_impl(
    project_root: str,
    pattern: str,
    file_pattern: str = "**/*",
    context_lines: int = 0,
    ignore_case: bool = False
) -> str:
    """
    Content searching with context lines

    Search file contents using regex patterns with optional context lines before and after
    each match. Combines glob-based file filtering with content search for powerful code
    exploration. Matching lines are highlighted with ">>>" prefix.

    Search Features:
        - Regex pattern matching in file contents
        - Glob pattern for file filtering
        - Context lines before/after matches
        - Case-sensitive or case-insensitive search
        - Line number display for all results

    Security:
        - Blocks path traversal in file_pattern
        - Only searches files within project_root
        - Safely handles binary files (errors='ignore')

    Args:
        project_root: Project root directory (automatically provided)
        pattern: Search pattern (regular expression)
        file_pattern: Glob pattern to filter files (default: "**/*" = all files)
        context_lines: Number of lines to show before/after match (default: 0)
        ignore_case: If True, case-insensitive search (default: False)

    Returns:
        Formatted search results with file paths, line numbers, and context, or error message

    Output Format:
        Search results for 'pattern'
        ============================================================

        File: path/to/file.js
        ------------------------------------------------------------
            10: context before
        >>> 11: matching line with pattern
            12: context after

        File: another/file.py
        ------------------------------------------------------------
        >>> 25: another matching line

        ============================================================
        Total matches: 2 in 2 files

    Examples:
        >>> grep_search("TODO", "**/*.js")
        # Find all TODO comments in JavaScript files

        >>> grep_search("class.*:", "**/*.py", context_lines=2)
        # Find Python class definitions with 2 lines of context

        >>> grep_search("function\\s+\\w+", "src/**/*.js")
        # Find function declarations in src directory

        >>> grep_search("error", "**/*.log", ignore_case=True)
        # Case-insensitive search for "error" in log files

        >>> grep_search("console.log", "js/screens/title.js")
        # Search in title.js anywhere under js/screens/ (auto-adds **/ prefix)
        # Searches: public/js/screens/title.js, src/js/screens/title.js, etc.

        >>> grep_search("import", "components/Button.jsx")
        # Search for imports in Button.jsx anywhere under components/

    Auto-Prefix Behavior (file_pattern):
        - file_pattern WITHOUT wildcards (* or ?) automatically gets **/ prefix
        - "js/screens/title.js" → searches as "**/js/screens/title.js"
        - file_pattern WITH wildcards are used as-is
        - "**/*.js" → searches exactly as "**/*.js"

    Common Use Cases:
        - Finding TODOs: grep_search("TODO|FIXME", "**/*.py")
        - Finding imports: grep_search("^import ", "**/*.js")
        - Finding class definitions: grep_search("class \\w+", "**/*.py")
        - Finding function calls: grep_search("myFunc\\(", "**/*")
        - Search in specific file: grep_search("error", "config.json")

    Error Handling:
        - Returns error if path traversal detected in file_pattern
        - Returns "No matches found" if pattern matches nothing
        - Skips files that can't be read (binary, permissions)
        - Handles regex errors gracefully
    """
    # Directories and file patterns to exclude from search
    EXCLUDED_DIRS = {'logs', 'backup', '__pycache__', 'node_modules', '.git', '.venv', 'venv'}
    EXCLUDED_EXTENSIONS = {'.out', '.log', '.backup', '.bak', '.pyc', '.pyo'}

    try:
        # Path Traversal check
        if "../" in file_pattern or file_pattern.endswith(".."):
            return "❌ Error: Access denied: Path traversal detected in file_pattern"

        # File search
        if file_pattern.startswith("/"):
            file_pattern = file_pattern[1:]

        # Auto-enable partial path matching
        # If pattern doesn't contain * or **, prepend **/
        if '*' not in file_pattern and '?' not in file_pattern:
            file_pattern = f"**/{file_pattern}"

        full_pattern = os.path.join(project_root, file_pattern)
        all_files = glob_module.glob(full_pattern, recursive=True)

        # Filter out excluded directories and file types
        files = []
        for file_path in all_files:
            rel_path = os.path.relpath(file_path, project_root)
            path_parts = rel_path.split(os.sep)

            # Skip if any path component is in excluded dirs
            if any(part in EXCLUDED_DIRS for part in path_parts):
                continue

            # Skip if file extension is excluded
            _, ext = os.path.splitext(file_path)
            if ext.lower() in EXCLUDED_EXTENSIONS:
                continue

            files.append(file_path)

        # Compile regex
        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        results = []
        total_matches = 0
        files_with_matches = 0
        MAX_MATCHES = 50  # Limit to prevent token overflow
        MAX_FILES = 20    # Limit number of files to search
        truncated = False

        for file_path in files:
            if not os.path.isfile(file_path):
                continue

            # Stop if we've hit the file limit
            if files_with_matches >= MAX_FILES:
                truncated = True
                break

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                rel_path = os.path.relpath(file_path, project_root)
                file_matches = []

                for i, line in enumerate(lines, 1):
                    # Stop if we've hit the match limit
                    if total_matches >= MAX_MATCHES:
                        truncated = True
                        break

                    if regex.search(line):
                        # Get context before and after
                        context_start = max(0, i - 1 - context_lines)
                        context_end = min(len(lines), i + context_lines)

                        context = []
                        for j in range(context_start, context_end):
                            line_num = j + 1
                            prefix = ">>> " if line_num == i else "    "
                            context.append(f"{prefix}{line_num:4d}: {lines[j].rstrip()}")

                        file_matches.append("\n".join(context))
                        total_matches += 1

                if file_matches:
                    results.append(f"\nFile: {rel_path}\n{'-' * 60}")
                    results.extend(file_matches)
                    files_with_matches += 1

                # Check if we need to stop after processing this file
                if total_matches >= MAX_MATCHES:
                    truncated = True
                    break

            except Exception:
                continue

        if not results:
            return f"No matches found for pattern: {pattern}"

        header = [
            f"Search results for '{pattern}'",
            "=" * 60
        ]

        truncation_notice = ""
        if truncated:
            truncation_notice = f"\n⚠️ Results truncated (limit: {MAX_MATCHES} matches, {MAX_FILES} files). Use a more specific file_pattern to narrow search."

        footer = [
            "",
            "=" * 60,
            f"Total matches: {total_matches} in {files_with_matches} files{truncation_notice}"
        ]

        return "\n".join(header + results + footer)

    except Exception as e:
        return f"❌ Error: {e}"


def sed_edit_impl(
    project_root: str,
    file_path: str,
    pattern: str,
    replacement: str,
    global_replace: bool = False,
    error_tracker: Any = None
) -> str:
    """
    Stream editor for regex-based editing

    Perform regex-based find-and-replace operations on files, similar to the sed command.
    Supports both single replacement (first match only) and global replacement (all matches).
    Uses Python regex syntax for powerful pattern matching with capture groups and backreferences.

    Regex Features:
        - Full Python regex syntax (re module)
        - Capture groups: (pattern) referenced as \\1, \\2, etc.
        - Character classes: \\d, \\w, \\s, etc.
        - Quantifiers: *, +, ?, {n,m}
        - Anchors: ^, $, \\b

    Security:
        - Uses normalize_path_safe() to prevent path traversal
        - Creates automatic backup before editing
        - Validates file existence before editing

    Args:
        project_root: Project root directory (automatically provided)
        file_path: File to edit (relative to project root)
        pattern: Regular expression pattern to find
        replacement: Replacement string (can use \\1, \\2 for capture groups)
        global_replace: If True, replace all occurrences; if False, replace first only (default: False)

    Returns:
        Success message with replacement count, or error message

    Examples:
        >>> sed_edit("/work/file.txt", r"old", "new", global_replace=True)
        # Replace all occurrences of "old" with "new"

        >>> sed_edit("/work/file.js", r"var\\s+(\\w+)", r"const \\1", global_replace=True)
        # Convert all "var x" to "const x" using capture group

        >>> sed_edit("/work/config.json", r'"debug":\\s*true', '"debug": false')
        # Replace first occurrence of debug:true with debug:false

        >>> sed_edit("/work/readme.md", r"Version (\\d+)\\.(\\d+)", r"Version \\1.\\2.1")
        # Update version number using capture groups

    Common Use Cases:
        - Rename variables: r"oldName" → "newName"
        - Update syntax: r"var (\\w+)" → r"const \\1"
        - Fix formatting: r"\\s+$" → "" (remove trailing spaces)
        - Update values: r'"version": "[^"]+"' → '"version": "2.0.0"'

    Comparison with file_edit:
        - sed_edit: Regex-based, good for patterns and bulk changes
        - file_edit: Exact string matching, good for single replacements

    Error Handling:
        - Returns error if file doesn't exist
        - Returns error if pattern not found
        - Returns error if path traversal detected
        - Creates backup before editing (can be restored manually)
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        error_msg = f"❌ Error: {e}"
        if error_tracker:
            error_tracker.record_error(
                "sed_edit",
                {"file_path": file_path, "pattern": pattern},
                error_msg
            )
        return error_msg

    if not os.path.exists(full_path):
        error_msg = f"❌ Error: File not found: {rel_path}"
        if error_tracker:
            error_tracker.record_error(
                "sed_edit",
                {"file_path": file_path, "pattern": pattern},
                error_msg
            )
        return error_msg

    try:
        # Read file
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Create backup
        create_backup(full_path)

        # Regex replacement
        if global_replace:
            new_content, count = re.subn(pattern, replacement, content)
        else:
            new_content, count = re.subn(pattern, replacement, content, count=1)

        if count == 0:
            error_msg = f"❌ Error: Pattern not found: {pattern}"
            if error_tracker:
                error_tracker.record_error(
                    "sed_edit",
                    {"file_path": file_path, "pattern": pattern, "replacement": replacement},
                    error_msg
                )
            return error_msg

        # Write to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        if error_tracker:
            error_tracker.record_success("sed_edit")
        return f"✅ Replaced {count} occurrence(s) in {rel_path}"

    except Exception as e:
        error_msg = f"❌ Error: {e}"
        if error_tracker:
            error_tracker.record_error(
                "sed_edit",
                {"file_path": file_path, "pattern": pattern, "replacement": replacement},
                error_msg
            )
        return error_msg


def replace_file_impl(project_root: str, file_path: str, content: str) -> str:
    """
    Replace entire file content (create new or overwrite existing).

    Args:
        project_root: Project root directory
        file_path: File path relative to project root
        content: New file content
            ⚠️ IMPORTANT: Pass the EXACT text to write to the file.
            Do NOT add Python string escaping (no \\n, \\t, \\\\, \\`, \\$ etc.).
            For JavaScript: Use `text ${var}` NOT \\`text \\${var}\\`
            What you pass is what gets written to the file.

    Returns:
        Success message or error message
    """
    try:
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    try:
        # Create backup if file exists
        if os.path.exists(full_path):
            create_backup(full_path)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"✅ File replaced: {rel_path}"
    except Exception as e:
        return f"❌ Error: {e}"


def copy_file_impl(project_root: str, source_path: str, dest_path: str) -> str:
    """
    Copy a single file from source to destination.

    Copy an entire file from one location to another. Creates parent directories
    as needed. Useful for creating backups, duplicating templates, and file snapshots.

    Security:
        - Uses normalize_path_safe() to prevent path traversal attacks
        - Both source and destination must be within project_root
        - Preserves file metadata (timestamps, permissions)

    Args:
        project_root: Project root directory (automatically provided)
        source_path: Source file path relative to project root (e.g., "/public/js/game.js")
        dest_path: Destination file path relative to project root (e.g., "/backup/game.js.bak")

    Returns:
        Success message with file size, or error message if operation fails

    Examples:
        >>> copy_file("/public/js/game.js", "/backup/game.js.v1")
        ✅ File copied: /public/js/game.js → /backup/game.js.v1 (2048 bytes)

        >>> copy_file("/work/design.json", "/work/design.json.backup")
        ✅ File copied: /work/design.json → /work/design.json.backup (512 bytes)

    Use Cases:
        - Create snapshots before iteration: copy_file("/public/", "/backup/public_iteration_1")
        - Backup configuration files
        - Duplicate template files
        - Create checkpoints at critical stages

    Error Handling:
        - Returns error if source file doesn't exist
        - Returns error if source is not a file (is a directory)
        - Returns error if path traversal is detected
    """
    try:
        # Validate source
        src_rel, src_full = normalize_path_safe(source_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(src_full):
        return f"❌ Error: Source file not found: {source_path}"

    if not os.path.isfile(src_full):
        return f"❌ Error: Source is not a file: {source_path}"

    try:
        # Validate destination
        dst_rel, dst_full = normalize_path_safe(dest_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    try:
        # Create parent directory if needed
        os.makedirs(os.path.dirname(dst_full), exist_ok=True)

        # Copy file
        import shutil
        shutil.copy2(src_full, dst_full)  # Preserves metadata

        # Get file size for reporting
        file_size = os.path.getsize(dst_full)

        return f"✅ File copied: {src_rel} → {dst_rel} ({file_size} bytes)"
    except Exception as e:
        return f"❌ Error: {e}"


def copy_dir_impl(project_root: str, source_dir: str, dest_dir: str, overwrite: bool = False) -> str:
    """
    Copy an entire directory tree from source to destination.

    Recursively copy a directory with all its files and subdirectories. Creates
    parent directories as needed. Ideal for creating iteration checkpoints,
    full project snapshots, and recovery backups.

    Security:
        - Uses normalize_path_safe() to prevent path traversal attacks
        - Both source and destination must be within project_root
        - Validates directory existence before copying

    Args:
        project_root: Project root directory (automatically provided)
        source_dir: Source directory path relative to project root (e.g., "/public")
        dest_dir: Destination directory path relative to project root (e.g., "/backup/public_iter1")
        overwrite: If True, remove existing destination before copy. If False, fail if destination exists.

    Returns:
        Success message with file count and total size, or error message if operation fails

    Examples:
        >>> copy_dir("/public", "/backup/public_iteration_1")
        ✅ Directory copied: /public → /backup/public_iteration_1
           Files copied: 42
           Total size: 1.2 MB

        >>> copy_dir("/work/assets/sprites", "/backup/sprites_v2", overwrite=True)
        ✅ Directory copied (overwrote existing): /work/assets/sprites → /backup/sprites_v2
           Files copied: 8
           Total size: 256 KB

    Use Cases (RECOVERY WORKFLOW):
        RECOMMENDED AT ITERATION START:
        1. When starting new iteration, copy public directory:
           copy_dir("/public", "/backup/public_before_iteration_N")

        2. If iteration fails, restore from backup:
           copy_dir("/backup/public_before_iteration_N", "/public", overwrite=True)

        ITERATION CHECKPOINT PATTERN:
        → Task starts: copy_dir("/public", "/backup/public_iter_X")
        → Task executes: Programmer modifies /public/
        → If error: Restore: copy_dir("/backup/public_iter_X", "/public", overwrite=True)
        → If success: Keep backup for next iteration

    Use Cases (ASSET MANAGEMENT):
        - Backup sprite assets before regeneration
        - Create versioned snapshots of complete game directories
        - Duplicate theme/asset directories for variants

    Error Handling:
        - Returns error if source directory doesn't exist
        - Returns error if destination exists and overwrite=False
        - Returns error if path traversal is detected
        - Lists number of files copied and total size even on partial success
    """
    try:
        # Validate source
        src_rel, src_full = normalize_path_safe(source_dir, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    if not os.path.exists(src_full):
        return f"❌ Error: Source directory not found: {source_dir}"

    if not os.path.isdir(src_full):
        return f"❌ Error: Source is not a directory: {source_dir}"

    try:
        # Validate destination
        dst_rel, dst_full = normalize_path_safe(dest_dir, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    try:
        import shutil

        # Check if destination exists
        if os.path.exists(dst_full):
            if not overwrite:
                return f"❌ Error: Destination already exists: {dest_dir}. Use overwrite=True to replace."
            else:
                # Remove existing destination
                shutil.rmtree(dst_full)

        # Create parent directory
        os.makedirs(os.path.dirname(dst_full), exist_ok=True)

        # Copy entire directory tree
        shutil.copytree(src_full, dst_full)

        # Calculate statistics
        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(dst_full):
            file_count += len(files)
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)

        # Format size for display
        if total_size > 1024 * 1024:
            size_str = f"{total_size / (1024*1024):.1f} MB"
        elif total_size > 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size} bytes"

        return f"✅ Directory copied: {src_rel} → {dst_rel}\n   Files copied: {file_count}\n   Total size: {size_str}"

    except Exception as e:
        return f"❌ Error: {e}"


def write_file_impl(project_root: str, file_path: str, content: str) -> str:
    """
    Create a NEW file with specified content. Dedicated new file creation tool.

    Simple, straightforward tool for creating new files. This is the PRIMARY tool
    for all new file creation operations. Fails clearly if file already exists,
    making it impossible to accidentally overwrite existing files.

    ✅ WHEN TO USE:
    - Creating new files (ONLY use for new files)
    - Initial project setup
    - Creating asset specification files
    - Creating game configuration files
    - Any new file creation

    ❌ DO NOT USE FOR:
    - Editing existing files (use file_edit() or sed_edit() instead)
    - Replacing file content (use replace_file() instead)
    - Copying files (use copy_file() instead)

    Security:
        - Uses normalize_path_safe() to prevent path traversal attacks
        - Both source and destination must be within project_root
        - FAILS if file already exists (prevents accidental overwrites)
        - Creates parent directories automatically

    Args:
        project_root: Project root directory (automatically provided)
        file_path: Path to NEW file (must not exist) relative to project root
        content: Full file content to write
            ⚠️ IMPORTANT: Pass the EXACT text to write to the file.
            Do NOT add Python string escaping (no \\n, \\t, \\\\, \\`, \\$ etc.).
            For JavaScript template literals: Use `text ${var}` NOT \\`text \\${var}\\`
            What you pass is what gets written to the file.

    Returns:
        Success message with file size, or error message if operation fails

    Examples:
        >>> write_file("/public/js/game.js", "class Game { ... }")
        ✅ File created: /public/js/game.js (1024 bytes)

        >>> # JavaScript with template literals - CORRECT (NO escaping):
        >>> write_file("/public/js/ui.js", "console.log(`Score: ${score}`);")
        ✅ File created: /public/js/ui.js (35 bytes)
        # ✅ Correct: Backticks ` and ${} are NOT escaped
        # ❌ WRONG: "console.log(\\`Score: \\${score}\\`);"

        >>> write_file("/work/design.json", '{"game": "shooter"}')
        ✅ File created: /work/design.json (256 bytes)

        >>> write_file("/public/js/game.js", "new content")
        ❌ Error: File already exists: /public/js/game.js
           Use replace_file() to overwrite or smart_file_edit() to modify

    Use Cases:
        - Create config files: write_file("/work/config.json", "{...}")
        - Create HTML files: write_file("/public/index.html", "<html>...</html>")
        - Create CSS files: write_file("/public/css/style.css", "body { ... }")
        - Create specifications: write_file("/work/asset_spec.json", "{...}")

    Error Handling:
        - Returns error if file already exists (clear failure)
        - Returns error if path traversal is detected
        - Returns error if parent directory creation fails
        - Creates parent directories automatically (unlike some tools)

    Design Note:
        write_file is intentionally simple and single-purpose.
        - No mode parameter (only creates new files)
        - No fuzzy matching (exact file path required)
        - No versioning (fails if exists)
        This simplicity makes it reliable and prevents errors.
    """
    try:
        # Validate path
        rel_path, full_path = normalize_path_safe(file_path, project_root)
    except ValueError as e:
        return f"❌ Error: {e}"

    # Check if file already exists
    if os.path.exists(full_path):
        return (
            f"❌ Error: File already exists at {rel_path}\n"
            f"To overwrite, use replace_file()\n"
            f"To edit, use file_edit() or sed_edit()"
        )

    try:
        # Create parent directories
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Get file size for reporting
        file_size = os.path.getsize(full_path)

        return f"✅ File created: {rel_path} ({file_size} bytes)"

    except Exception as e:
        return f"❌ Error: {e}"
