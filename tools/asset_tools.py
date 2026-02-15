"""
Asset generation tools for GameStudio 1984 v0.4.

Each function's docstring contains complete JSON specification so LLM can use tools
without needing separate documentation files.
"""

import os
import json
import subprocess
import hashlib
import struct
from langchain_core.tools import tool

# Loop detection for generate_svg
_generate_svg_call_history: dict[str, list[str]] = {}
_LOOP_THRESHOLD = 3

def _check_svg_loop_detected(output_path: str, svg_code: str) -> tuple[bool, str]:
    """
    Check if a loop has been detected for generate_svg.
    """
    global _generate_svg_call_history
    svg_hash = hashlib.md5(svg_code.encode()).hexdigest()
    if output_path not in _generate_svg_call_history:
        _generate_svg_call_history[output_path] = []
    history = _generate_svg_call_history[output_path]
    same_svg_count = sum(1 for h in history if h == svg_hash)
    history.append(svg_hash)
    if len(history) > 10:
        _generate_svg_call_history[output_path] = history[-10:]
    if same_svg_count >= _LOOP_THRESHOLD - 1:
        return (True, f"identical SVG called {same_svg_count + 1} times")
    return (False, "")


# Helper to get PROJECT_ROOT (must be set by main())
def _get_project_root() -> str:
    """Get PROJECT_ROOT from environment."""
    return os.environ.get("PROJECT_ROOT", "/")


@tool
def generate_image(output_path: str, pattern_json: str) -> str:
    """
    Generate a pixel art PNG image from JSON pattern specification.

    Args:
        output_path: Where to save the PNG file (e.g., "/public/assets/images/player.png")
        pattern_json: JSON string containing the image specification

    Returns:
        "SUCCESS: <path>" or "ERROR: <message>"

    ## JSON Specification

    ```json
    {
        "size": "32x32",
        "colors": ["transparent", "#FF0000", "#00FF00", "#0000FF"],
        "pattern": "A32:B16C16:...",
        "rle": true
    }
    ```

    ### Fields:
    - size: "WxH" format (e.g., "32x32", "16x16", "64x64")
    - colors: Array of up to 32 colors
      - "transparent" for alpha=0
      - "#RGB" or "#RRGGBB" hex format
      - Index 0 = first color (A), Index 1 = second (B), etc.
    - pattern: Pixel data as string
    - rle: (optional) Enable run-length encoding mode

    ### Pattern Format (RLE mode recommended):
    - A-Z = color indices 0-25
    - a-f = color indices 26-31
    - Numbers = repeat count for previous color
    - : = row delimiter
    - *N = repeat row N times

    ### Pattern Examples:
    ```
    "A32"           = 32 pixels of color A (index 0)
    "A16B16"        = 16 A's followed by 16 B's
    "A32:B32"       = Row 1: 32 A's, Row 2: 32 B's
    "A32*8"         = 8 rows of 32 A's each
    "ABCD"          = 1 pixel each: A, B, C, D
    ```

    ### Complete Example (8x8 red square with transparent border):
    ```json
    {
        "size": "8x8",
        "colors": ["transparent", "#FF0000"],
        "pattern": "A8:AB6A:AB6A:AB6A:AB6A:AB6A:AB6A:A8",
        "rle": true
    }
    ```

    ### Tips:
    - Use "transparent" as first color for sprites with alpha
    - Keep size ≤ 64x64 for retro aesthetic
    - Use RLE mode for simpler patterns (fewer characters)
    - Test with validate_asset() after generation
    """
    try:
        # Parse pattern JSON
        try:
            pattern_data = json.loads(pattern_json)
        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON pattern: {e}"

        # Resolve output path
        full_output_path = os.path.join(_get_project_root(), output_path.lstrip("/"))

        # Create output directory
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        # Get dotter script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dotter_script = os.path.join(script_dir, "doteditor", "dotter.py")

        if not os.path.exists(dotter_script):
            return f"ERROR: Dotter script not found at {dotter_script}"

        # Create JSON file in /work/sprite directory (not /tmp) for later review
        work_sprite_dir = os.path.join(_get_project_root(), "work", "sprite")
        os.makedirs(work_sprite_dir, exist_ok=True)

        # Generate JSON filename from output path (e.g., player.png -> player.json)
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        json_path = os.path.join(work_sprite_dir, f"{base_name}.json")

        with open(json_path, 'w') as f:
            json.dump(pattern_data, f, indent=2)

        try:
            # Run dotter
            command = [
                "python3", dotter_script,
                "--root_dir", _get_project_root(),
                "-o", output_path.lstrip("/"),
                json_path,
                "-q"
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)

            # Verify file was actually created
            if not os.path.exists(full_output_path):
                return f"ERROR: Dotter completed but PNG file not created at {output_path}"

            # Verify PNG header (89 50 4E 47 0D 0A 1A 0A)
            with open(full_output_path, 'rb') as f:
                header = f.read(8)
            png_magic = b'\x89PNG\r\n\x1a\n'
            if header != png_magic:
                return f"ERROR: Generated file is not a valid PNG (invalid header at {output_path})"

            # Keep JSON file for later review (don't delete)
            return f"SUCCESS: {output_path} (JSON: work/sprite/{base_name}.json)"

        except subprocess.CalledProcessError as e:
            return f"ERROR: Dotter failed: {e.stderr}"
        except Exception as e:
            raise

    except Exception as e:
        return f"ERROR: {e}"


@tool
def generate_svg(output_path: str, svg_code: str) -> str:
    """
    Generate a PNG image from SVG code using resvg.

    Best for larger or complex graphics (64x64+) where pixel patterns are hard to specify.
    For small pixel art (32x32 or less), use generate_image instead.

    Args:
        output_path: Output path (e.g., "/public/assets/images/background.png")
        svg_code: SVG markup string

    Returns:
        "SUCCESS: <path>" or "ERROR: <message>"

    ## SVG Format

    ```svg
    <svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="64" height="64" fill="#1a1a2e"/>
      <circle cx="32" cy="32" r="20" fill="#e94560"/>
    </svg>
    ```

    ## REQUIRED Attributes
    - width, height: Image dimensions in pixels (recommended: 64-256)
    - xmlns: Must be "http://www.w3.org/2000/svg"

    ## Tips
    - Use generate_svg for: backgrounds, large enemies, UI elements, complex shapes
    - Use generate_image for: small sprites (player, bullets, small items)
    - Keep SVG simple - complex paths may render slowly
    """
    # Check for loop detection FIRST
    is_loop, loop_reason = _check_svg_loop_detected(output_path, svg_code)
    if is_loop:
        return f"ERROR: LOOP DETECTED for '{output_path}' - {loop_reason}"

    try:
        # Validate SVG has required attributes
        if 'xmlns=' not in svg_code and 'xmlns:' not in svg_code:
            svg_code = svg_code.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ', 1)

        # Try to import resvg_py
        try:
            import resvg_py
        except ImportError:
            return "ERROR: resvg_py not installed. Run: pip install resvg_py"

        # Convert SVG to PNG bytes
        try:
            png_bytes = resvg_py.svg_to_bytes(svg_string=svg_code)
        except Exception as e:
            return f"ERROR: SVG rendering failed: {e}"

        # Resolve output path
        full_output_path = os.path.join(_get_project_root(), output_path.lstrip("/"))

        # Create output directory
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        # Save PNG file (forced .png extension for engine compatibility)
        if not full_output_path.endswith(".png"):
            full_output_path = os.path.splitext(full_output_path)[0] + ".png"
            output_path = os.path.splitext(output_path)[0] + ".png"

        with open(full_output_path, 'wb') as f:
            f.write(png_bytes)

        # Save SVG source in /work/svg directory for later review
        work_svg_dir = os.path.join(_get_project_root(), "work", "svg")
        os.makedirs(work_svg_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(output_path))[0]
        svg_path = os.path.join(work_svg_dir, f"{base_name}.svg")

        with open(svg_path, 'w') as f:
            f.write(svg_code)

        # Verify PNG and get dimensions
        with open(full_output_path, 'rb') as f:
            header = f.read(24)
        png_magic = b'\x89PNG\r\n\x1a\n'
        if header[:8] != png_magic:
            return f"ERROR: Generated file is not a valid PNG"

        width, height = struct.unpack('>II', header[16:24])

        return f"SUCCESS: {output_path} ({width}x{height}) (SVG: work/svg/{base_name}.svg)"

    except Exception as e:
        return f"ERROR: {e}"


# Loop detection for generate_sound
_generate_sound_call_history: dict[str, int] = {}
_SOUND_LOOP_THRESHOLD = 2

def _check_sound_loop_detected(output_path: str) -> tuple[bool, str]:
    """
    Check if a loop has been detected for generate_sound.
    """
    global _generate_sound_call_history
    if output_path not in _generate_sound_call_history:
        _generate_sound_call_history[output_path] = 0
    _generate_sound_call_history[output_path] += 1
    call_count = _generate_sound_call_history[output_path]
    if call_count >= _SOUND_LOOP_THRESHOLD:
        return (True, f"sound tool called {call_count} times for same file")
    return (False, "")


@tool
def generate_sfx(output_path: str, sfx_type: str, intensity: str = "medium",
                 pitch: str = "mid", duration: float = None) -> str:
    """
    Generate a preset-based sound effect. Simpler than generate_sound() for common game SFX.

    Args:
        output_path: Where to save the WAV file (e.g., "/public/assets/sounds/explosion.wav")
        sfx_type: Type of sound effect ("explosion", "laser", "hit", "powerup", "coin", "jump", "gameover", "victory", "damage", "select", "blip")
        intensity: Intensity level - "low", "medium", or "high" (default: "medium")
        pitch: Pitch level - "low", "mid", or "high" (default: "mid")
        duration: Optional duration override in seconds

    Returns:
        "SUCCESS: <path>" or "ERROR: <message>"
    """
    is_loop, loop_reason = _check_sound_loop_detected(output_path)
    if is_loop:
        return f"ERROR: LOOP DETECTED for '{output_path}' - {loop_reason}"

    try:
        full_output_path = os.path.join(_get_project_root(), output_path.lstrip("/"))
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        sfx_script = os.path.join(script_dir, "synthesizer", "sfx_generator.py")

        if not os.path.exists(sfx_script):
            return f"ERROR: SFX generator script not found at {sfx_script}"

        command = [
            "python3", sfx_script,
            sfx_type,
            "-o", output_path.lstrip("/"),
            "--intensity", intensity,
            "--pitch", pitch,
            "--root_dir", _get_project_root()
        ]
        if duration is not None:
            command.extend(["--duration", str(duration)])

        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return f"SUCCESS: {output_path}"

    except Exception as e:
        return f"ERROR: {e}"


@tool
def generate_sound(output_path: str, pattern_json: str) -> str:
    """
    Generate a WAV sound file from JSON pattern specification.

    Args:
        output_path: Where to save the WAV file (e.g., "/public/assets/sounds/shoot.wav")
        pattern_json: JSON string containing the sound specification

    Returns:
        "SUCCESS: <path>" or "ERROR: <message>"

    ## JSON Specification

    ```json
    {
        "bpm": 120,
        "patternLength": 16,
        "masterVolume": 0.7,
        "tracks": {
            "drum": { ... },
            "bass": { ... },
            "melody": { ... }
        }
    }
    ```

    ### Global Settings:
    - bpm: Tempo (60-300). Higher = shorter sound.
    - patternLength: Steps per pattern (2, 4, 8, or 16)
    - masterVolume: 0.0-1.0

    ### Sound Duration Formula:
    duration = (patternLength / bpm) * 60 seconds
    Example: 4 steps at 240 BPM = 1 second

    ---

    ## Track Types

    ### 1. Drum Track
    ```json
    "drum": {
        "volume": 0.8,
        "data": {
            "Kick": [true, false, false, false],
            "Snare": [false, false, true, false],
            "Hi-Hat": [true, true, true, true],
            "Clap": [false, false, false, true]
        }
    }
    ```
    Available drums: Kick, Snare, Hi-Hat, Clap

    ### 2. Oscillator Track (bass, melody)
    ```json
    "bass": {
        "volume": 0.7,
        "waveform": "sawtooth",
        "data": {
            "C2": [true, false, false, false],
            "G2": [false, false, true, false]
        }
    }
    ```
    Waveforms: sine, sawtooth, triangle, square
    Notes: C2-B2 (low), C3-B3 (mid), C4-C5 (high)

    ### 3. Chord Track
    ```json
    "chord": {
        "volume": 0.6,
        "waveform": "triangle",
        "data": {
            "C": [true, false, false, false],
            "G": [false, false, true, false]
        }
    }
    ```
    Chords: C, Dm, Em, F, G, Am, Bdim, C7

    ### 4. FM Synthesis Track
    ```json
    "fm": {
        "volume": 0.7,
        "ratio": 2.0,
        "depth": 500,
        "data": {
            "C4": [true, false, false, false]
        }
    }
    ```
    ratio: 1.0-5.0 (modulator frequency)
    depth: 100-1000 Hz (modulation depth)

    ---

    ## Sound Effect Recipes

    ### Laser/Shoot (short zap):
    ```json
    {
        "bpm": 300,
        "patternLength": 2,
        "masterVolume": 0.8,
        "tracks": {
            "melody": {
                "volume": 1.0,
                "waveform": "sine",
                "data": {
                    "C5": [true, false],
                    "C4": [false, true]
                }
            }
        }
    }
    ```

    ### Explosion:
    ```json
    {
        "bpm": 120,
        "patternLength": 4,
        "masterVolume": 0.9,
        "tracks": {
            "drum": {
                "volume": 1.0,
                "data": {
                    "Kick": [true, true, false, false],
                    "Snare": [false, true, true, false]
                }
            }
        }
    }
    ```

    ### Jump:
    ```json
    {
        "bpm": 300,
        "patternLength": 2,
        "masterVolume": 0.7,
        "tracks": {
            "melody": {
                "volume": 0.8,
                "waveform": "square",
                "data": {
                    "C4": [true, false],
                    "E4": [false, true]
                }
            }
        }
    }
    ```

    ### Power-Up (ascending):
    ```json
    {
        "bpm": 200,
        "patternLength": 4,
        "masterVolume": 0.7,
        "tracks": {
            "melody": {
                "volume": 0.8,
                "waveform": "square",
                "data": {
                    "C4": [true, false, false, false],
                    "E4": [false, true, false, false],
                    "G4": [false, false, true, false],
                    "C5": [false, false, false, true]
                }
            }
        }
    }
    ```

    ### Tips:
    - For very short sounds: BPM 240-300, patternLength 2-4
    - For BGM loops: BPM 100-140, patternLength 16
    - Test with validate_asset() after generation
    """
    try:
        # Parse pattern JSON
        try:
            pattern_data = json.loads(pattern_json)
        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON pattern: {e}"

        # Resolve output path
        full_output_path = os.path.join(_get_project_root(), output_path.lstrip("/"))

        # Create output directory
        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        # Get synthesizer script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        synth_script = os.path.join(script_dir, "synthesizer", "synth.py")

        if not os.path.exists(synth_script):
            return f"ERROR: Synthesizer script not found at {synth_script}"

        # Create JSON file in /work/sound directory (not /tmp) for later review
        work_sound_dir = os.path.join(_get_project_root(), "work", "sound")
        os.makedirs(work_sound_dir, exist_ok=True)

        # Generate JSON filename from output path (e.g., shoot.wav -> shoot.json)
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        json_path = os.path.join(work_sound_dir, f"{base_name}.json")

        with open(json_path, 'w') as f:
            json.dump(pattern_data, f, indent=2)

        try:
            # Run synthesizer
            command = [
                "python3", synth_script,
                "--root_dir", _get_project_root(),
                "-o", output_path.lstrip("/"),
                json_path,
                "-q"
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)

            # Verify file was actually created
            if not os.path.exists(full_output_path):
                return f"ERROR: Synthesizer completed but WAV file not created at {output_path}"

            # Verify WAV header (RIFF....WAVE)
            with open(full_output_path, 'rb') as f:
                header = f.read(12)
            if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                return f"ERROR: Generated file is not a valid WAV (invalid header at {output_path})"

            # Keep JSON file for later review (don't delete)
            return f"SUCCESS: {output_path} (JSON: work/sound/{base_name}.json)"

        except subprocess.CalledProcessError as e:
            return f"ERROR: Synthesizer failed: {e.stderr}"
        except Exception as e:
            raise

    except Exception as e:
        return f"ERROR: {e}"
