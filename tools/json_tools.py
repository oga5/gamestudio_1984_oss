"""
JSON operation tools for GameStudio 1984 v0.4.

Each function's docstring serves as documentation for the LLM.
"""

import os
import json
from typing import Any
from langchain_core.tools import tool

# Import utility functions
from .utils.get_json_item import get_json_item as get_json_item_impl
from .utils.edit_json_item import edit_json_item as edit_json_item_impl

# Helper to get PROJECT_ROOT (must be set by main())
def _get_project_root() -> str:
    """Get PROJECT_ROOT from environment."""
    return os.environ.get("PROJECT_ROOT", "/")


@tool
def get_json_item(file_path: str, selector: str) -> str:
    """
    Get a value from a JSON file using dot notation selector.

    Args:
        file_path: Path to JSON file (e.g., "/work/design.json")
        selector: Dot notation selector (e.g., "assets[id=30]", "settings.volume")

    Returns:
        JSON string of the selected value, or error message

    Selector Syntax:
        - Simple key: "name" → data["name"]
        - Nested key: "settings.volume" → data["settings"]["volume"]
        - List index: "assets[0]" → data["assets"][0]
        - List search: "assets[id=30]" → find item in assets where id=30
        - Combined: "game.levels[0].enemies[type=boss]"

    Example:
        get_json_item("/work/design.json", "name")
        # Returns: "Space Invaders"

        get_json_item("/work/design.json", "assets[id=30]")
        # Returns: {"id": 30, "type": "image", "name": "player.png"}

        get_json_item("/work/design.json", "settings.difficulty")
        # Returns: "hard"
    """
    try:
        # Normalize path
        full_path = os.path.join(_get_project_root(), file_path.lstrip("/"))

        if not os.path.exists(full_path):
            return f"ERROR: File not found: {file_path}"

        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        result = get_json_item_impl(data, selector)

        if result is not None:
            return json.dumps(result, indent=2, ensure_ascii=False)
        else:
            return f"ERROR: Item not found with selector: {selector}"

    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON in {file_path}: {e}"
    except Exception as e:
        return f"ERROR: {e}"


@tool
def edit_json_item(file_path: str, selector: str, value: str) -> str:
    """
    Edit a value in a JSON file using dot notation selector.

    Args:
        file_path: Path to JSON file (e.g., "/work/design.json")
        selector: Dot notation selector (e.g., "assets[id=30]", "settings.volume")
        value: New value as JSON string OR plain string/number.
               - JSON strings: '{"name": "player"}', '"easy"', '42', 'true', 'null'
               - Plain values: 'completed', 'pending', '100' (will be auto-converted)
               - For string values, use JSON format: '"completed"' (recommended)

    Returns:
        Success message or error description

    IMPORTANT:
        - If the JSON file is corrupted or has syntax errors, this tool will fail.
        - In that case, use file_edit() or replace_file() to manually fix the JSON structure.
        - Always ensure the JSON file is valid before using this tool.

    Selector Syntax:
        Same as get_json_item (see above)

    Behavior:
        - If item exists: Replace it
        - If item doesn't exist (list search): Append to list
        - If path doesn't exist: Error

    Examples:
        # String value (both formats work):
        edit_json_item("/work/design.json", "name", '"Galaga Clone"')  # Recommended
        edit_json_item("/work/design.json", "status", 'completed')      # Auto-converted to "completed"

        # Number:
        edit_json_item("/work/design.json", "settings.volume", '0.8')

        # Object:
        edit_json_item("/work/design.json", "assets[id=30]", '{"id": 30, "name": "enemy.png"}')

        # Boolean:
        edit_json_item("/work/design.json", "enabled", 'true')
    """
    try:
        # Normalize path
        full_path = os.path.join(_get_project_root(), file_path.lstrip("/"))

        if not os.path.exists(full_path):
            return f"ERROR: File not found: {file_path}"

        # Check file extension
        if not file_path.lower().endswith('.json'):
            return (
                f"ERROR: This tool only works with JSON files (.json extension).\n"
                f"File '{file_path}' is not a JSON file.\n"
                f"For HTML/JS/other files, use file_edit(), sed_edit(), or write_file() instead."
            )

        # Parse new value - be flexible with input
        try:
            new_value = json.loads(value)
        except json.JSONDecodeError:
            # If value is not valid JSON, try to auto-convert:
            # - If it looks like a number, convert to number
            # - If it's 'true'/'false', convert to boolean
            # - If it's 'null', convert to None
            # - Otherwise, treat as string
            if value.lower() == 'true':
                new_value = True
            elif value.lower() == 'false':
                new_value = False
            elif value.lower() == 'null':
                new_value = None
            else:
                # Try as number
                try:
                    # Check if it's an integer
                    if '.' not in value:
                        new_value = int(value)
                    else:
                        new_value = float(value)
                except ValueError:
                    # Treat as string
                    new_value = value

        # Load file
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return (
                f"ERROR: JSON file is corrupted: {e}\n"
                f"The file {file_path} contains invalid JSON syntax.\n"
                f"Use file_edit() or replace_file() to manually fix the JSON structure, "
                f"or read_file() to inspect the content."
            )

        # Check current value (idempotency check)
        try:
            current_value = get_json_item_impl(data, selector)
            if current_value == new_value:
                return f"SKIPPED: Value at '{selector}' is already set to {json.dumps(new_value)}"
        except:
            # If getting current value fails, proceed with edit
            pass

        # Edit item
        edit_json_item_impl(data, selector, new_value)

        # Save file
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return f"SUCCESS: Updated {file_path} at selector '{selector}'"

    except json.JSONDecodeError as e:
        return (
            f"ERROR: Invalid JSON in {file_path}: {e}\n"
            f"The JSON file is corrupted or contains syntax errors.\n"
            f"Use file_edit(), replace_file(), or read_file() to inspect and fix the file manually."
        )
    except Exception as e:
        return f"ERROR: {e}"
