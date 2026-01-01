"""
Asset validation tools for GameStudio 1984 v0.4.

Validates that asset files have correct format matching their extension.
"""

import os
import struct
import glob as glob_module
from langchain_core.tools import tool

# Helper to get PROJECT_ROOT (must be set by main())
def _get_project_root() -> str:
    """Get PROJECT_ROOT from environment."""
    return os.environ.get("PROJECT_ROOT", "/")


def _validate_asset_impl(path: str) -> str:
    """
    Internal implementation of asset validation.
    Returns: "VALID: path (metadata)" or "INVALID: path renamed to path.err"
    """
    try:
        # Resolve full path
        full_path = os.path.join(_get_project_root(), path.lstrip("/"))

        if not os.path.exists(full_path):
            return f"ERROR: File not found: {path}"

        ext = os.path.splitext(full_path)[1].lower()
        metadata = ""

        with open(full_path, 'rb') as f:
            if ext == '.png':
                header = f.read(24)
                # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
                png_header = b'\x89PNG\r\n\x1a\n'
                if header[:8] == png_header:
                    # IHDR chunk: width (16-20), height (20-24) in Big Endian
                    width, height = struct.unpack('>II', header[16:24])
                    metadata = f" ({width}x{height})"
                    is_valid = True
                else:
                    is_valid = False

            elif ext == '.wav':
                # WAV header: RIFF....WAVE
                header = f.read(44) # Standard WAV header size
                if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                    # Byte rate is at offset 28 (4 bytes), Data size is at offset 40 (4 bytes)
                    byte_rate = struct.unpack('<I', header[28:32])[0]
                    data_size = struct.unpack('<I', header[40:44])[0]
                    if byte_rate > 0:
                        duration = data_size / byte_rate
                        metadata = f" ({duration:.2f}s)"
                    is_valid = True
                else:
                    is_valid = False
            else:
                return f"ERROR: Unsupported file type: {ext}"

        if is_valid:
            return f"VALID: {path}{metadata}"
        else:
            new_path = f"{full_path}.err"
            os.rename(full_path, new_path)
            return f"INVALID: {path} renamed to {path}.err"

    except Exception as e:
        return f"ERROR: Could not validate {path}: {e}"


@tool
def validate_asset(path: str) -> str:
    """
    Validate asset format and return metadata (dimensions/duration).

    Checks:
    - .png files: Valid PNG header + returns dimensions (e.g., "32x32")
    - .wav files: Valid WAV header + returns duration (e.g., "1.50s")

    Use this tool to:
    1. Verify asset integrity
    2. Get image dimensions (width x height) for code implementation
    3. Get sound duration for timing logic

    If invalid, renames file to <original>.err and returns error message.

    Args:
        path: Path to asset file (.png or .wav)

    Returns:
        "VALID: <path> (<metadata>)" or "INVALID: <path> renamed to <path>.err"

    Example:
        validate_asset("/public/assets/images/player.png")
        # Returns: "VALID: /public/assets/images/player.png (32x32)"

        validate_asset("/public/assets/sounds/shoot.wav")
        # Returns: "VALID: /public/assets/sounds/shoot.wav (0.45s)"
    """
    return _validate_asset_impl(path)


@tool
def validate_all_assets(asset_dir: str = "/public/assets") -> str:
    """
    Validate all .png and .wav files and report their metadata.

    Scans images/ and sounds/ subdirectories, validates each file,
    and returns a summary including dimensions and durations.

    Args:
        asset_dir: Root asset directory

    Returns:
        Summary of validation results with metadata

    Example:
        validate_all_assets("/public/assets")
        # Returns:
        # "Validated 5 assets: 5 valid, 0 invalid
        #  VALID: /public/assets/images/player.png (32x32)
        #  VALID: /public/assets/sounds/shoot.wav (0.45s)
        #  ..."
    """
    try:
        # Resolve full path
        full_asset_dir = os.path.join(_get_project_root(), asset_dir.lstrip("/"))

        if not os.path.exists(full_asset_dir):
            return f"ERROR: Asset directory not found: {asset_dir}"

        results = {"valid": [], "invalid": [], "error": []}

        for subdir in ["images", "sounds"]:
            dir_path = os.path.join(full_asset_dir, subdir)
            if not os.path.exists(dir_path):
                continue

            pattern = "*.png" if subdir == "images" else "*.wav"
            for filepath in glob_module.glob(os.path.join(dir_path, pattern)):
                # Convert to relative path from PROJECT_ROOT
                rel_path = os.path.relpath(filepath, _get_project_root())
                if not rel_path.startswith("/"):
                    rel_path = "/" + rel_path

                result = _validate_asset_impl(rel_path)
                if result.startswith("VALID"):
                    results["valid"].append(rel_path)
                elif result.startswith("INVALID"):
                    results["invalid"].append(result)
                else:
                    results["error"].append(result)

        total = len(results["valid"]) + len(results["invalid"])
        summary = f"Validated {total} assets: "
        summary += f"{len(results['valid'])} valid, {len(results['invalid'])} invalid"

        if results["invalid"]:
            summary += "\n" + "\n".join(results["invalid"])

        if results["error"]:
            summary += "\nErrors:\n" + "\n".join(results["error"])

        return summary

    except Exception as e:
        return f"ERROR: {e}"
