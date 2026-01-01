"""
GameStudio 1984 v0.4 - Tool Collection

All tools are defined with docstrings that serve as LLM documentation.
Import tools from here for agent creation.
"""

import os

from .file_tools import (
    file_edit,
    sed_edit,
    replace_file,
    read_file,
    inspect_image,
    inspect_audio,
    mv_file,
    copy_file,
    copy_dir,
    list_directory,
    glob_search,
    grep_search,
    write_file,
    file_exists,
    set_project_root,
)

from .json_tools import (
    get_json_item,
    edit_json_item,
)

from .asset_tools import (
    generate_image,
    generate_sound,
)

from .asset_validator import (
    validate_asset,
    validate_all_assets,
)

from .test_tools import (
    check_syntax,
    test_game,
)

from .permissions import (
    get_tools_with_permissions,
    FilePermissions,
    DEFAULT_PERMISSIONS,
)

# ============================================================================
# Base Tool Collections (without permissions)
# ============================================================================

BASE_DESIGNER_TOOLS = [
    read_file,
    file_edit,
    sed_edit,
    replace_file,
    write_file,
    get_json_item,
    edit_json_item,
    list_directory,
    copy_file,
]

BASE_PROGRAMMER_TOOLS = [
    read_file,
    validate_asset,
    file_edit,
    sed_edit,
    replace_file,
    write_file,
    check_syntax,
    glob_search,
    grep_search,
    list_directory,
]

BASE_GRAPHIC_ARTIST_TOOLS = [
    generate_image,
    inspect_image,
    validate_asset,
    list_directory,
    read_file,
]

BASE_SOUND_ARTIST_TOOLS = [
    generate_sound,
    inspect_audio,
    validate_asset,
    list_directory,
    read_file,
]

BASE_TESTER_TOOLS = [
    test_game,           # Run game tests
    check_syntax,        # Verify code syntax
    read_file,           # Read test results and game files
    file_exists,         # Check for test result files
    write_file,          # Write test_report.json (ONLY output file)
    mv_file,             # Backup old reports (required by test_game.md:163-166)
    file_edit,           # Limited HTML structure fixes only (tester.md:18-22)
    sed_edit,            # Pattern-based HTML fixes only (tester.md:18-22)
    # Removed: replace_file, glob_search, get_json_item, edit_json_item
    # Reason: These are not needed for testing role. See TESTER_WORKFLOW_BUG_FIX.md
]

BASE_MANAGER_TOOLS = [
    read_file,
    file_edit,
    sed_edit,
    replace_file,
    write_file,
    get_json_item,
    edit_json_item,
    list_directory,
    file_exists,
    validate_all_assets,
]

# ============================================================================
# Permission-Wrapped Tool Collections
# ============================================================================

# Get config path
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Create permission-wrapped tools for each role
DESIGNER_TOOLS = get_tools_with_permissions(BASE_DESIGNER_TOOLS, "designer", _CONFIG_PATH)
PROGRAMMER_TOOLS = get_tools_with_permissions(BASE_PROGRAMMER_TOOLS, "programmer", _CONFIG_PATH)
GRAPHIC_ARTIST_TOOLS = get_tools_with_permissions(BASE_GRAPHIC_ARTIST_TOOLS, "graphic_artist", _CONFIG_PATH)
SOUND_ARTIST_TOOLS = get_tools_with_permissions(BASE_SOUND_ARTIST_TOOLS, "sound_artist", _CONFIG_PATH)
TESTER_TOOLS = get_tools_with_permissions(BASE_TESTER_TOOLS, "tester", _CONFIG_PATH)
MANAGER_TOOLS = get_tools_with_permissions(BASE_MANAGER_TOOLS, "manager", _CONFIG_PATH)

__all__ = [
    # File tools
    'file_edit',
    'sed_edit',
    'replace_file',
    'read_file',
    'mv_file',
    'copy_file',
    'copy_dir',
    'list_directory',
    'glob_search',
    'grep_search',
    'write_file',
    'file_exists',
    'set_project_root',
    # JSON tools
    'get_json_item',
    'edit_json_item',
    # Asset tools
    'generate_image',
    'generate_sound',
    # Validation tools
    'validate_asset',
    'validate_all_assets',
    # Test tools
    'check_syntax',
    'test_game',
    # Permission system
    'get_tools_with_permissions',
    'FilePermissions',
    'DEFAULT_PERMISSIONS',
    # Base tool collections (without permissions)
    'BASE_DESIGNER_TOOLS',
    'BASE_PROGRAMMER_TOOLS',
    'BASE_GRAPHIC_ARTIST_TOOLS',
    'BASE_SOUND_ARTIST_TOOLS',
    'BASE_TESTER_TOOLS',
    'BASE_MANAGER_TOOLS',
    # Role tool collections (with permissions)
    'DESIGNER_TOOLS',
    'PROGRAMMER_TOOLS',
    'GRAPHIC_ARTIST_TOOLS',
    'SOUND_ARTIST_TOOLS',
    'TESTER_TOOLS',
    'MANAGER_TOOLS',
]
