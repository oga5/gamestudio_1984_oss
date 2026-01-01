"""
Test Directory Helper - Manage numbered test result directories

Provides utilities for creating and finding numbered test directories
under /work/test/ to avoid backup file management.
"""
import os
import re
from typing import Optional, List
from pathlib import Path


def get_next_test_directory(project_root: str) -> str:
    """
    Get the next available test directory number.

    Creates /work/test/ if it doesn't exist, then finds the next
    available numbered directory (001, 002, 003, etc.).

    Args:
        project_root: Absolute path to project root

    Returns:
        Relative path to next test directory (e.g., "/work/test/001")

    Example:
        >>> get_next_test_directory("/path/to/project")
        "/work/test/001"  # First test

        # After test 001 exists:
        >>> get_next_test_directory("/path/to/project")
        "/work/test/002"  # Second test
    """
    test_base = os.path.join(project_root, "work", "test")

    # Create /work/test/ if it doesn't exist
    os.makedirs(test_base, exist_ok=True)

    # Find existing numbered directories
    existing_nums = []
    if os.path.exists(test_base):
        for entry in os.listdir(test_base):
            if os.path.isdir(os.path.join(test_base, entry)):
                # Match 3-digit numbers (001, 002, etc.)
                match = re.match(r'^(\d{3})$', entry)
                if match:
                    existing_nums.append(int(match.group(1)))

    # Get next number
    if existing_nums:
        next_num = max(existing_nums) + 1
    else:
        next_num = 1

    # Format as 3-digit number
    next_dir = f"{next_num:03d}"

    # Return relative path
    return f"/work/test/{next_dir}"


def get_latest_test_directory(project_root: str) -> Optional[str]:
    """
    Get the most recent test directory.

    Args:
        project_root: Absolute path to project root

    Returns:
        Relative path to latest test directory, or None if no tests exist

    Example:
        >>> get_latest_test_directory("/path/to/project")
        "/work/test/003"  # If 001, 002, 003 exist
    """
    test_base = os.path.join(project_root, "work", "test")

    if not os.path.exists(test_base):
        return None

    # Find existing numbered directories
    existing_nums = []
    for entry in os.listdir(test_base):
        if os.path.isdir(os.path.join(test_base, entry)):
            match = re.match(r'^(\d{3})$', entry)
            if match:
                existing_nums.append(int(match.group(1)))

    if not existing_nums:
        return None

    # Get latest number
    latest_num = max(existing_nums)
    latest_dir = f"{latest_num:03d}"

    return f"/work/test/{latest_dir}"


def list_test_directories(project_root: str) -> List[str]:
    """
    List all test directories in chronological order.

    Args:
        project_root: Absolute path to project root

    Returns:
        List of relative paths to test directories (oldest to newest)

    Example:
        >>> list_test_directories("/path/to/project")
        ["/work/test/001", "/work/test/002", "/work/test/003"]
    """
    test_base = os.path.join(project_root, "work", "test")

    if not os.path.exists(test_base):
        return []

    # Find existing numbered directories
    existing_nums = []
    for entry in os.listdir(test_base):
        if os.path.isdir(os.path.join(test_base, entry)):
            match = re.match(r'^(\d{3})$', entry)
            if match:
                existing_nums.append(int(match.group(1)))

    # Sort and format
    existing_nums.sort()
    return [f"/work/test/{num:03d}" for num in existing_nums]


def create_test_directory(project_root: str, test_dir: str) -> str:
    """
    Create a test directory and return its absolute path.

    Args:
        project_root: Absolute path to project root
        test_dir: Relative path (e.g., "/work/test/001")

    Returns:
        Absolute path to created directory

    Example:
        >>> create_test_directory("/proj", "/work/test/001")
        "/proj/work/test/001"
    """
    # Normalize path (remove leading /)
    normalized = test_dir.lstrip("/")
    full_path = os.path.join(project_root, normalized)

    # Create directory
    os.makedirs(full_path, exist_ok=True)

    return full_path


def get_test_report_path(test_dir: str) -> str:
    """
    Get the test report path for a given test directory.

    Args:
        test_dir: Test directory path (e.g., "/work/test/001")

    Returns:
        Path to test_report.json

    Example:
        >>> get_test_report_path("/work/test/001")
        "/work/test/001/test_report.json"
    """
    return os.path.join(test_dir, "test_report.json")


def get_test_result_path(test_dir: str) -> str:
    """
    Get the test result path for a given test directory.

    Args:
        test_dir: Test directory path (e.g., "/work/test/001")

    Returns:
        Path to test_result.json

    Example:
        >>> get_test_result_path("/work/test/001")
        "/work/test/001/test_result.json"
    """
    return os.path.join(test_dir, "test_result.json")


# ============================================================================
# Utility Functions for LLM Tools
# ============================================================================

def format_test_directory_info(project_root: str) -> str:
    """
    Format test directory information for LLM context.

    Args:
        project_root: Absolute path to project root

    Returns:
        Formatted string with test directory information

    Example output:
        ```
        Test Directory Information:
        - Next test: /work/test/004
        - Latest test: /work/test/003
        - All tests: /work/test/001, /work/test/002, /work/test/003
        ```
    """
    next_dir = get_next_test_directory(project_root)
    latest_dir = get_latest_test_directory(project_root)
    all_dirs = list_test_directories(project_root)

    lines = ["Test Directory Information:"]
    lines.append(f"- Next test: {next_dir}")

    if latest_dir:
        lines.append(f"- Latest test: {latest_dir}")
    else:
        lines.append("- Latest test: None (no tests yet)")

    if all_dirs:
        lines.append(f"- All tests: {', '.join(all_dirs)}")
    else:
        lines.append("- All tests: None")

    return "\n".join(lines)
