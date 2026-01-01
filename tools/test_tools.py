"""
Testing tools for GameStudio 1984 v0.4.

Each function's docstring serves as documentation for the LLM.
"""

import os
import json
import subprocess
import glob as glob_module
from typing import List, Optional
from langchain_core.tools import tool

# Import test directory helper
from .test_directory_helper import (
    get_next_test_directory,
    create_test_directory,
)

# Helper to get PROJECT_ROOT (must be set by main())
def _get_project_root() -> str:
    """Get PROJECT_ROOT from environment."""
    return os.environ.get("PROJECT_ROOT", "/")


@tool
def check_syntax(file_path: str) -> str:
    """
    Check JavaScript/HTML file for syntax errors.

    Args:
        file_path: Path to file or glob pattern
            - Single file: "/public/game.js"
            - Glob pattern: "**/*.js" (checks all JS files)

    Returns:
        "OK: <file>" for valid files, or error details with line numbers

    Example:
        check_syntax("/public/game.js")
        # Returns: "OK: /public/game.js"

        check_syntax("/public/game.js")
        # Returns: "ERROR: /public/game.js:45:12 - Unexpected token '}'"

        check_syntax("**/*.js")
        # Returns: "Checked 5 files: 4 OK, 1 error\nERROR: game.js:23:5 - ..."

    Tips:
        - ALWAYS run after editing JS/HTML files
        - Use glob patterns to check all files at once
        - If error line looks correct, check surrounding lines
    """
    def check_single_file(path: str) -> str:
        """Internal function to check a single file."""
        full_path = os.path.join(_get_project_root(), path.lstrip("/"))

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            if path.endswith(".js"):
                # Check for escaped backticks (common error)
                import re
                if '\\`' in content:
                    lines_with_issue = []
                    for i, line in enumerate(content.split('\n'), 1):
                        if '\\`' in line:
                            lines_with_issue.append(f"  Line {i}: {line.strip()[:80]}")
                    issue_summary = '\n'.join(lines_with_issue[:5])
                    return (
                        f"ERROR: Escaped backticks detected in {path}\n"
                        f"Template literals should NOT have escaped backticks.\n"
                        f"Wrong: \\`text \\${{var}}\\`\n"
                        f"Correct: `text ${{var}}`\n\n"
                        f"Found in:\n{issue_summary}"
                    )

                # Check JavaScript syntax with Node.js
                result = subprocess.run(
                    ["node", "--check", full_path],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    return f"OK: {path}"
                else:
                    error_msg = result.stderr
                    return f"ERROR: {path} - {error_msg.strip()}"

            elif path.endswith(".py"):
                # Check Python syntax
                import ast
                ast.parse(content)
                return f"OK: {path}"

            else:
                return f"OK: {path} (no syntax check available for this file type)"

        except SyntaxError as e:
            return f"ERROR: {path} - {e}"
        except Exception as e:
            return f"ERROR: {path} - {e}"

    # Detect glob pattern
    is_glob = '*' in file_path or '?' in file_path or '[' in file_path

    if is_glob:
        # Glob mode: check multiple files
        pattern = os.path.join(_get_project_root(), file_path.lstrip("/"))
        matched_files = glob_module.glob(pattern, recursive=True)

        if not matched_files:
            return f"No files found matching pattern: {file_path}"

        # Filter to only code files
        file_list = [f for f in matched_files if f.endswith('.js') or f.endswith('.py')]

        if not file_list:
            return f"No code files found matching pattern: {file_path}"

        # Check each file
        errors = []
        ok_count = 0

        for full_file_path in file_list:
            rel_path = "/" + os.path.relpath(full_file_path, _get_project_root())
            result = check_single_file(rel_path)

            if result.startswith("OK"):
                ok_count += 1
            else:
                errors.append(result)

        # Format output
        if not errors:
            return f"All files OK - Checked {ok_count} files, 0 errors"

        error_summary = '\n'.join(errors)
        return f"{error_summary}\n{'─' * 40}\nChecked {ok_count + len(errors)} files, {len(errors)} errors"

    # Single file mode
    return check_single_file(file_path)


@tool
def test_game(html_path: str, mode: str = "standard",
              control_keys: Optional[List[str]] = None, output_dir: Optional[str] = None) -> str:
    """
    Test game in headless Firefox browser.

    Args:
        html_path: Path to index.html (e.g., "/public/index.html")
        mode: Test mode
            - "standard": Basic initialization + tap test
            - "verification": 3-step test with screenshots
        control_keys: Keys to simulate (default: ["UP", "DOWN", "LEFT", "RIGHT"])
        output_dir: Where to save screenshots (default: auto-numbered /work/test/NNN)

    Returns:
        JSON string with test results

    ## Standard Mode
    1. Load page in Firefox headless
    2. Check canvas element exists
    3. Tap screen center
    4. Check for JavaScript errors
    5. Take screenshot

    ## Verification Mode (3-step test)
    1. Load game → Screenshot "01_title_screen.png"
    2. Tap to start → Screenshot "02_game_started.png"
    3. Simulate controls → Screenshot "03_game_playing.png"
    4. Compare screenshots for changes

    ## Output Directory
    All files are saved to a numbered test directory:
    - /work/test/001/ (first test)
    - /work/test/002/ (second test after fixes)
    - etc.

    Files saved:
    - 01_title_screen.png, 02_game_started.png, 03_game_playing.png
    - test_result.json (raw test output)

    ## Result Format
    ```json
    {
        "success": true,
        "html_path": "/public/index.html",
        "test_directory": "/work/test/001",
        "errors": [],
        "checks": {
            "initialization": true,
            "post_tap_state": {"gameState": "playing"}
        },
        "screenshot": "/work/test/001/test_screenshot.png"
    }
    ```

    ## Error Result Format
    ```json
    {
        "success": false,
        "errors": [
            {
                "message": "Cannot read property 'x' of undefined",
                "url": "game.js",
                "line": 42,
                "column": 15
            }
        ]
    }
    ```

    ## Verification Result Format
    ```json
    {
        "success": true,
        "test_directory": "/work/test/001",
        "verification_results": {
            "initialization": true,
            "title_screen": {"screenshot_path": "01_title_screen.png"},
            "game_started": {
                "screenshot_path": "02_game_started.png",
                "comparison": {"has_changes": true, "similarity": 65.2}
            },
            "game_playing": {
                "screenshot_path": "03_game_playing.png",
                "comparison": {"has_changes": true, "similarity": 71.8}
            }
        }
    }
    ```

    ## Success Criteria (Verification Mode)
    - initialization: Canvas element found
    - title_screen → game_started: ≥0.1% pixel difference
    - game_started → game_playing: ≥0.1% pixel difference
    - No JavaScript errors

    ## Available Control Keys
    Letters: A-Z
    Numbers: 0-9
    Special: SPACE, ENTER, ESCAPE, UP, DOWN, LEFT, RIGHT, TAB

    ## Example Usage
    ```python
    # Basic test
    test_game("/public/index.html")

    # Full verification with custom keys
    test_game(
        "/public/index.html",
        mode="verification",
        control_keys=["SPACE", "UP", "LEFT", "RIGHT"]
    )
    ```

    ## Common Errors and Fixes
    - "Canvas element not found": Add <canvas id="game-canvas" width="360" height="540">
    - "Unexpected token": Run check_syntax first
    - "Cannot read property": Check undefined variable access
    - "No significant changes": Game may not be responding to input
    """
    try:
        # Set defaults
        if control_keys is None:
            control_keys = ["UP", "DOWN", "LEFT", "RIGHT"]

        project_root = _get_project_root()

        # Get next numbered test directory if output_dir not specified
        if output_dir is None:
            output_dir = get_next_test_directory(project_root)

        # Resolve paths
        full_html_path = os.path.join(project_root, html_path.lstrip("/"))
        full_output_dir = create_test_directory(project_root, output_dir)

        if not os.path.exists(full_html_path):
            return json.dumps({
                "success": False,
                "errors": [{"message": f"HTML file not found: {html_path}"}]
            })

        # Get firefoxtester script path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        firefoxtester_script = os.path.join(script_dir, "firefoxtester", "firefoxtester.py")

        if not os.path.exists(firefoxtester_script):
            return json.dumps({
                "success": False,
                "errors": [{"message": f"FirefoxTester not found at {firefoxtester_script}"}]
            })

        # Get geckodriver path from config
        # config.json is in the same directory as gamestudio_1984.py (parent of tools/)
        config_path = os.path.join(os.path.dirname(script_dir), "config.json")
        if not os.path.exists(config_path):
            return json.dumps({
                "success": False,
                "errors": [{"message": f"config.json not found at {config_path}"}]
            })

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        geckodriver_path = config.get("tools", {}).get("geckodriver_path")
        if not geckodriver_path:
            return json.dumps({
                "success": False,
                "errors": [{"message": "geckodriver_path not configured in config.json"}]
            })

        # Build test script commands based on mode
        if mode == "verification":
            script_commands = [
                {"cmd": "screenshot", "filename": os.path.join(full_output_dir, "01_title_screen.png")},  # Title screen
                {"cmd": "tap"},         # Start game
                {"cmd": "sleep", "ms": 1000},
                {"cmd": "screenshot", "filename": os.path.join(full_output_dir, "02_game_started.png")},  # Game started
            ]
            # Add control keys
            for key in control_keys:
                script_commands.append({"cmd": "keypress", "key": key})
                script_commands.append({"cmd": "sleep", "ms": 500})
            script_commands.append({"cmd": "screenshot", "filename": os.path.join(full_output_dir, "03_game_playing.png")})  # Game playing
            script_json = json.dumps(script_commands)
        else:
            # Standard mode: basic test
            script_json = json.dumps([
                {"cmd": "tap"},
                {"cmd": "sleep", "ms": 1000},
                {"cmd": "screenshot", "filename": os.path.join(full_output_dir, "test_screenshot.png")}
            ])

        # Run firefoxtester - output to numbered test directory
        output_path = os.path.join(output_dir, "test_result.json")
        full_output_path = os.path.join(project_root, output_path.lstrip("/"))

        cmd = [
            "python3",
            firefoxtester_script,
            html_path.lstrip("/"),
            "--root_dir", os.path.abspath(project_root),
            "--geckodriver", os.path.expanduser(geckodriver_path),
            "--output", output_path.lstrip("/"),
            "--output_dir", output_dir.lstrip("/"),
            "--script", script_json
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.abspath(project_root),
            timeout=120
        )

        if result.returncode != 0:
            return json.dumps({
                "success": False,
                "test_directory": output_dir,
                "errors": [{
                    "message": f"FirefoxTester failed: {result.stderr}",
                    "stdout": result.stdout
                }]
            })

        # Load and return results
        if not os.path.exists(full_output_path):
            return json.dumps({
                "success": False,
                "test_directory": output_dir,
                "errors": [{"message": "Test results not generated"}]
            })

        with open(full_output_path, "r", encoding="utf-8") as f:
            results_dict = json.load(f)

        # Add test_directory to results
        results_dict["test_directory"] = output_dir

        return json.dumps(results_dict)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "test_directory": output_dir if output_dir else None,
            "errors": [{"message": "Test timed out after 120 seconds"}]
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "test_directory": output_dir if 'output_dir' in dir() else None,
            "errors": [{"message": str(e)}]
        })
