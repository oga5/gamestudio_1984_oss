#!/usr/bin/env python3
"""
Firefox Headless Game Tester

Loads game index.html in Firefox headless mode, verifies initialization and
tap-to-start functionality, and checks for JavaScript errors.
"""

import argparse
import json
import os
import sys
import time
import http.server
import socketserver
import threading
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# For image analysis
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ErrorCapturingHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that provides wrapper HTML with error capture functionality"""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        # Return wrapper HTML with error handler for /__test__.html requests
        if self.path == '/__test__.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            # Load original index.html content
            original_html = self.server.original_html_content

            # Inject error handler at the beginning of <head>
            error_handler_script = '''
<script>
// Error handler - must be first script to catch all errors
window.__testErrors = [];
window.__testWarnings = [];
window.__consoleErrors = [];

// Capture window.onerror (uncaught exceptions)
window.onerror = function(msg, url, line, col, error) {
    window.__testErrors.push({
        message: String(msg),
        url: String(url),
        line: line,
        column: col,
        stack: error ? String(error.stack) : null,
        type: 'uncaught_exception'
    });
    console.error('[TEST ERROR]', msg, 'at', url, line, col);
    return false;
};

// Capture unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    window.__testErrors.push({
        message: 'Unhandled Promise Rejection: ' + String(event.reason),
        type: 'promise'
    });
});

// Override console.error to capture explicit console.error() calls
(function() {
    const originalConsoleError = console.error;
    console.error = function(...args) {
        // Store the console.error message
        const message = args.map(arg => {
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');

        window.__consoleErrors.push({
            message: message,
            timestamp: Date.now(),
            type: 'console_error'
        });

        // Call original console.error
        originalConsoleError.apply(console, args);
    };
})();

console.log('[TEST] Error handler installed');
</script>
'''
            # Inject error handler after <head> tag
            if '<head>' in original_html:
                modified_html = original_html.replace('<head>', '<head>' + error_handler_script, 1)
            elif '<HEAD>' in original_html:
                modified_html = original_html.replace('<HEAD>', '<HEAD>' + error_handler_script, 1)
            else:
                # If no <head>, prepend to document
                modified_html = error_handler_script + original_html

            self.wfile.write(modified_html.encode('utf-8'))
        else:
            # Handle other requests normally
            super().do_GET()


class LocalServer:
    """Local HTTP server for serving game files with error capture"""

    def __init__(self, directory: str, port: int = 8888, html_file: str = "index.html", port_range: tuple = (8888, 8899)):
        self.directory = directory
        self.port = port
        self.port_range = port_range
        self.html_file = html_file
        self.httpd = None
        self.thread = None
        self.original_cwd = None

    def start(self):
        self.original_cwd = os.getcwd()
        os.chdir(self.directory)

        # Load original HTML content
        html_path = os.path.join(self.directory, self.html_file)
        with open(html_path, 'r', encoding='utf-8') as f:
            original_html_content = f.read()

        handler = ErrorCapturingHTTPHandler
        socketserver.TCPServer.allow_reuse_address = True

        # Try to find an available port in the specified range
        last_error = None
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                self.httpd = socketserver.TCPServer(("", port), handler)
                self.port = port  # Record the actual port used
                break
            except OSError as e:
                last_error = e
                continue
        else:
            raise OSError(f"No available port in range {self.port_range[0]}-{self.port_range[1]}: {last_error}")

        self.httpd.original_html_content = original_html_content

        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print(f"  Local server started at http://localhost:{self.port}")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            print("  Local server stopped")
        if self.original_cwd:
            os.chdir(self.original_cwd)


class FirefoxGameTester:
    """Headless Firefox browser automation for testing games"""

    def __init__(self, geckodriver_path: str):
        self.geckodriver_path = geckodriver_path
        self.driver = None
        self.errors = []
        self.warnings = []
        self.logs = []

    def setup(self):
        """Setup Firefox webdriver"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--width=800")
        options.add_argument("--height=600")

        # Configure console logging
        options.set_preference("devtools.console.stdout.content", True)

        service = Service(executable_path=self.geckodriver_path)
        self.driver = webdriver.Firefox(service=service, options=options)
        print("  Firefox headless browser started")

    def teardown(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("  Firefox browser closed")

    def load_page(self, url: str, wait_seconds: float = 2.0):
        """Load a page in the browser"""
        print(f"  Loading: {url}")
        self.driver.get(url)
        time.sleep(wait_seconds)
        self._collect_console_logs()

    def _collect_console_logs(self):
        """Collect console logs (Firefox has limitations)

        Uses JavaScript to detect errors since Firefox restricts browser log access
        """
        try:
            # Setup error handler to collect errors
            script = """
            if (!window.__testErrors) {
                window.__testErrors = [];
                window.__testWarnings = [];
                window.__consoleErrors = [];
                window.onerror = function(msg, url, line, col, error) {
                    window.__testErrors.push({
                        message: msg,
                        url: url,
                        line: line,
                        column: col,
                        stack: error ? error.stack : null
                    });
                    return false;
                };
                window.addEventListener('unhandledrejection', function(event) {
                    window.__testErrors.push({
                        message: 'Unhandled Promise Rejection: ' + event.reason,
                        type: 'promise'
                    });
                });
            }
            return {
                errors: window.__testErrors,
                warnings: window.__testWarnings,
                consoleErrors: window.__consoleErrors || []
            };
            """
            result = self.driver.execute_script(script)
            if result:
                self.errors.extend(result.get('errors', []))
                self.errors.extend(result.get('consoleErrors', []))
                self.warnings.extend(result.get('warnings', []))
        except Exception as e:
            print(f"  Warning: Could not collect console logs: {e}")

    def inject_error_handler(self):
        """Inject error handler into the page"""
        script = """
        window.__testErrors = [];
        window.__testWarnings = [];
        window.onerror = function(msg, url, line, col, error) {
            window.__testErrors.push({
                message: msg,
                url: url,
                line: line,
                column: col,
                stack: error ? error.stack : null
            });
            return false;
        };
        window.addEventListener('unhandledrejection', function(event) {
            window.__testErrors.push({
                message: 'Unhandled Promise Rejection: ' + event.reason,
                type: 'promise'
            });
        });
        console.log('Error handler injected');
        """
        self.driver.execute_script(script)

    def get_collected_errors(self):
        """Get collected errors including console.error() calls"""
        try:
            script = """
            var allErrors = (window.__testErrors || []).slice();
            var consoleErrors = (window.__consoleErrors || []).slice();
            return allErrors.concat(consoleErrors);
            """
            errors = self.driver.execute_script(script)
            return errors
        except Exception as e:
            print(f"  Warning: Could not collect errors: {e}")
            return []

    def check_game_initialized(self):
        """Check if the game has been initialized

        Returns:
            tuple: (success: bool, error_details: dict or None)
        """
        try:
            # Verify canvas element exists (try both common IDs)
            canvas = None
            canvas_id = None
            for cid in ["game-canvas", "gameCanvas"]:
                try:
                    canvas = self.driver.find_element(By.ID, cid)
                    canvas_id = cid
                    break
                except:
                    continue

            if not canvas:
                error = {
                    "type": "initialization_error",
                    "message": "Canvas element not found in DOM (tried 'game-canvas', 'gameCanvas')",
                    "recommendation": "Add <canvas id=\"game-canvas\" width=\"360\" height=\"540\"></canvas> to your HTML file"
                }
                print("  ERROR: Canvas element not found")
                return False, error
            print(f"  Canvas element found (id={canvas_id})")

            # Check game objects
            script = f"""
            return {{
                hasCanvas: !!document.getElementById('{canvas_id}'),
                canvasWidth: document.getElementById('{canvas_id}')?.width || 0,
                canvasHeight: document.getElementById('{canvas_id}')?.height || 0,
                hasGameLoop: typeof gameLoop !== 'undefined' || typeof update !== 'undefined' || typeof game !== 'undefined',
                gameState: typeof gameState !== 'undefined' ? gameState : (typeof game !== 'undefined' && game.state ? game.state : 'unknown')
            }};
            """
            result = self.driver.execute_script(script)
            print(f"  Game state: {json.dumps(result, indent=2)}")
            return result.get('hasCanvas', False), None
        except Exception as e:
            error = {
                "type": "initialization_error",
                "message": f"Unable to locate canvas element",
                "details": str(e),
                "recommendation": "Add <canvas id=\"game-canvas\" width=\"360\" height=\"540\"></canvas> to your HTML file"
            }
            print(f"  ERROR checking game initialization: {e}")
            return False, error

    def tap_screen(self, x: int = None, y: int = None):
        """Tap the screen at specified coordinates or center"""
        try:
            # Try to find canvas element (try both common IDs)
            canvas = None
            for cid in ["game-canvas", "gameCanvas"]:
                try:
                    canvas = self.driver.find_element(By.ID, cid)
                    break
                except:
                    continue

            if not canvas:
                print("  ERROR: Canvas element not found for tap")
                return

            if x is None or y is None:
                # Click canvas center
                ActionChains(self.driver).move_to_element(canvas).click().perform()
                print("  Tapped center of canvas")
            else:
                ActionChains(self.driver).move_to_element_with_offset(canvas, x, y).click().perform()
                print(f"  Tapped canvas at ({x}, {y})")
            time.sleep(0.5)
            self._collect_console_logs()
        except Exception as e:
            print(f"  ERROR tapping screen: {e}")

    def take_screenshot(self, filename: str):
        """Save a screenshot to file"""
        try:
            self.driver.save_screenshot(filename)
            print(f"  Screenshot saved: {filename}")
        except Exception as e:
            print(f"  ERROR taking screenshot: {e}")

    def keypress(self, key: str):
        """Press a key

        Args:
            key: Key name ('A'-'Z', '0'-'9', 'SPACE', 'ENTER', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ESCAPE', etc.)
        """
        try:
            # Try to find canvas element (try both common IDs)
            canvas = None
            for cid in ["game-canvas", "gameCanvas"]:
                try:
                    canvas = self.driver.find_element(By.ID, cid)
                    break
                except:
                    continue

            if not canvas:
                print("  ERROR: Canvas element not found for keypress")
                return

            # Map special keys to Selenium keys
            special_keys = {
                'SPACE': Keys.SPACE,
                'ENTER': Keys.ENTER,
                'RETURN': Keys.RETURN,
                'ESCAPE': Keys.ESCAPE,
                'ESC': Keys.ESCAPE,
                'UP': Keys.UP,
                'DOWN': Keys.DOWN,
                'LEFT': Keys.LEFT,
                'RIGHT': Keys.RIGHT,
                'TAB': Keys.TAB,
                'BACKSPACE': Keys.BACKSPACE,
                'DELETE': Keys.DELETE,
                'SHIFT': Keys.SHIFT,
                'CONTROL': Keys.CONTROL,
                'CTRL': Keys.CONTROL,
                'ALT': Keys.ALT,
            }

            key_upper = key.upper()
            if key_upper in special_keys:
                send_key = special_keys[key_upper]
            else:
                # Regular keys (A-Z, 0-9, etc.)
                send_key = key.lower()

            # Focus canvas and send key
            canvas.click()
            ActionChains(self.driver).send_keys(send_key).perform()
            print(f"  Keypress: {key}")
            self._collect_console_logs()
        except Exception as e:
            print(f"  ERROR keypress: {e}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Perform a swipe/drag operation

        Args:
            x1, y1: Starting coordinates
            x2, y2: Ending coordinates
            duration_ms: Duration of swipe in milliseconds
        """
        try:
            # Try to find canvas element (try both common IDs)
            canvas = None
            for cid in ["game-canvas", "gameCanvas"]:
                try:
                    canvas = self.driver.find_element(By.ID, cid)
                    break
                except:
                    continue

            if not canvas:
                print("  ERROR: Canvas element not found for swipe")
                return

            # Simulate drag operation with ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(canvas, x1, y1)
            actions.click_and_hold()

            # Split into multiple steps for smooth swipe
            steps = max(5, duration_ms // 50)
            dx = (x2 - x1) / steps
            dy = (y2 - y1) / steps

            for i in range(steps):
                actions.move_by_offset(dx, dy)
                actions.pause(duration_ms / 1000 / steps)

            actions.release()
            actions.perform()

            print(f"  Swipe: ({x1},{y1}) -> ({x2},{y2}) duration={duration_ms}ms")
            self._collect_console_logs()
        except Exception as e:
            print(f"  ERROR swipe: {e}")

    def get_game_state(self) -> dict:
        """Get the current game state"""
        try:
            script = """
            return {
                gameState: typeof gameState !== 'undefined' ? gameState :
                           (typeof game !== 'undefined' && game.state ? game.state : 'unknown'),
                isRunning: typeof isRunning !== 'undefined' ? isRunning :
                           (typeof game !== 'undefined' ? game.isRunning : null),
                score: typeof score !== 'undefined' ? score :
                       (typeof game !== 'undefined' && game.score !== undefined ? game.score : null),
                errors: window.__testErrors || [],
                consoleErrors: window.__consoleErrors || []
            };
            """
            state = self.driver.execute_script(script)
            print(f"  Game state: {json.dumps(state, indent=2)}")
            return state
        except Exception as e:
            print(f"  ERROR getting game state: {e}")
            return {"error": str(e)}


    def execute_command(self, cmd: dict) -> dict:
        """Execute a single command

        Args:
            cmd: Command dictionary {"cmd": "...", ...params}

        Examples:
            {"cmd": "tap", "x": 100, "y": 200}
            {"cmd": "keypress", "key": "D"}
            {"cmd": "sleep", "ms": 1000}
            {"cmd": "swipe", "x1": 0, "y1": 100, "x2": 200, "y2": 100, "duration": 300}
            {"cmd": "screenshot", "filename": "test.png"}
            {"cmd": "get_state"}
        """
        command = cmd.get("cmd", "").lower()
        result = {"cmd": command, "success": True}

        try:
            if command == "tap":
                x = cmd.get("x")
                y = cmd.get("y")
                self.tap_screen(x, y)

            elif command == "keypress":
                key = cmd.get("key", "")
                self.keypress(key)

            elif command == "sleep":
                ms = cmd.get("ms", 1000)
                time.sleep(ms / 1000)
                print(f"  Sleep: {ms}ms")
                self._collect_console_logs()

            elif command == "swipe":
                x1 = cmd.get("x1", 0)
                y1 = cmd.get("y1", 0)
                x2 = cmd.get("x2", 0)
                y2 = cmd.get("y2", 0)
                duration = cmd.get("duration", 300)
                self.swipe(x1, y1, x2, y2, duration)

            elif command == "screenshot":
                filename = cmd.get("filename", "script_screenshot.png")
                self.take_screenshot(filename)
                result["screenshot_path"] = filename

            elif command == "get_state":
                state = self.get_game_state()
                result["state"] = state

            else:
                result["success"] = False
                result["error"] = f"Unknown command: {command}"
                print(f"  ERROR: Unknown command: {command}")

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"  ERROR executing {command}: {e}")

        return result

    def run_script(self, commands: list) -> dict:
        """Execute a list of commands in sequence

        Args:
            commands: List of commands to execute

        Returns:
            Dictionary with execution results
        """
        results = {
            "success": True,
            "commands_executed": 0,
            "results": [],
            "errors": [],
            "screenshots": []
        }

        print(f"\n[Script Execution] {len(commands)} commands")
        print("-" * 40)

        for i, cmd in enumerate(commands):
            print(f"\n[{i+1}/{len(commands)}] {cmd.get('cmd', 'unknown')}")
            result = self.execute_command(cmd)
            results["results"].append(result)
            results["commands_executed"] += 1

            # Track screenshots
            if result.get("screenshot_path"):
                results["screenshots"].append(result["screenshot_path"])

            if not result.get("success", False):
                results["success"] = False
                results["errors"].append(result)

        # Get final game state
        final_state = self.get_game_state()
        results["final_state"] = final_state

        # Collect JavaScript errors
        collected_errors = self.get_collected_errors()
        if collected_errors:
            results["js_errors"] = collected_errors
            results["success"] = False

        # Compare screenshots if multiple were taken
        if len(results["screenshots"]) >= 2:
            print("\n[Screenshot Comparison]")
            print("-" * 40)
            screenshot_comparisons = []
            has_any_changes = False

            for i in range(len(results["screenshots"]) - 1):
                img1 = results["screenshots"][i]
                img2 = results["screenshots"][i + 1]
                print(f"\nComparing {os.path.basename(img1)} → {os.path.basename(img2)}")

                comparison = compare_images(img1, img2)
                screenshot_comparisons.append({
                    "from": img1,
                    "to": img2,
                    "comparison": comparison
                })

                has_changes = comparison.get("has_significant_changes", False)
                similarity = comparison.get("similarity", 0)
                pixel_diff = comparison.get("pixel_diff_percentage", 0)

                print(f"  Similarity: {similarity}% ({pixel_diff:.1f}% diff)")
                print(f"  {'✓ Changed' if has_changes else '✗ No significant change'}")

                if has_changes:
                    has_any_changes = True

            results["screenshot_comparisons"] = screenshot_comparisons

            # If no screenshots showed significant changes, mark as failure
            if not has_any_changes:
                error_msg = {
                    "type": "validation_error",
                    "message": "No significant visual changes detected between screenshots - game may not be responding to input",
                    "recommendation": "Check if game is actually running and responding to tap/key events"
                }
                results["errors"].append(error_msg)
                results["success"] = False
                print("\n✗ VALIDATION FAILED: No visual changes detected - game appears static")
            else:
                print("\n✓ Visual changes confirmed - game is responding")

        print("-" * 40)
        print(f"[Script Complete] {results['commands_executed']} commands executed, success={results['success']}")

        return results

    def run_script_test(self, html_path: str, commands: list, port: int = 8888) -> dict:
        """Run a script test

        Args:
            html_path: Path to HTML file
            commands: List of commands to execute
            port: Server port number

        Returns:
            Test results
        """
        results = {
            "success": False,
            "html_path": html_path,
            "script_results": None,
            "errors": []
        }

        html_dir = os.path.dirname(os.path.abspath(html_path))
        html_file = os.path.basename(html_path)

        server = LocalServer(html_dir, port, html_file)

        try:
            server.start()
            self.setup()

            # Load page
            url = f"http://localhost:{server.port}/__test__.html"
            print(f"  Loading: {url}")
            self.load_page(url, wait_seconds=2.0)

            # Check initialization
            print("\n[Initialization Check]")
            init_ok, init_error = self.check_game_initialized()

            if not init_ok:
                if init_error:
                    results["errors"].append(init_error)
                else:
                    results["errors"].append({"message": "Game initialization failed"})
                results["success"] = False
                return results

            # Run script
            script_results = self.run_script(commands)
            results["script_results"] = script_results
            results["success"] = script_results.get("success", False)

            if not script_results.get("success", False):
                results["errors"].extend(script_results.get("errors", []))

        except Exception as e:
            print(f"\nERROR during script test: {e}")
            results["errors"].append({"message": str(e), "type": "test_error"})
        finally:
            self.teardown()
            server.stop()

        return results

    def run_game_verification_test(self, html_path: str, control_keys: list = None, output_dir: str = None, port: int = 8888) -> dict:
        """
        Run a 3-step game verification test

        Step 1: Load game → Capture title screen screenshot
        Step 2: Tap screen center to start game → Capture screenshot (compare with title)
        Step 3: Simulate controller operations → Capture screenshot (compare with started)

        Args:
            html_path: Path to game index.html
            control_keys: List of keys to press (default: ['UP', 'DOWN', 'LEFT', 'RIGHT'])
            output_dir: Directory to save screenshots (default: project_root/work)
            port: Local server port number

        Returns:
            {
                "success": bool,
                "html_path": str,
                "errors": list,
                "verification_results": {
                    "initialization": bool,
                    "title_screen": {"screenshot_path": str, "analysis": dict},
                    "game_started": {"screenshot_path": str, "comparison": dict},
                    "game_playing": {"screenshot_path": str, "comparison": dict}
                }
            }
        """
        if control_keys is None:
            control_keys = ['UP', 'DOWN', 'LEFT', 'RIGHT']

        results = {
            "success": False,
            "html_path": html_path,
            "errors": [],
            "verification_results": {
                "initialization": False,
                "title_screen": {"screenshot_path": None, "analysis": None},
                "game_started": {"screenshot_path": None, "comparison": None},
                "game_playing": {"screenshot_path": None, "comparison": None}
            }
        }

        # Determine output directory
        if output_dir is None:
            html_dir = os.path.dirname(os.path.abspath(html_path))
            project_root = os.path.dirname(html_dir)
            output_dir = os.path.join(project_root, "work")
        os.makedirs(output_dir, exist_ok=True)

        html_dir = os.path.dirname(os.path.abspath(html_path))
        html_file = os.path.basename(html_path)
        server = LocalServer(html_dir, port, html_file)

        try:
            server.start()
            self.setup()

            # Load page
            url = f"http://localhost:{server.port}/__test__.html"
            print(f"\n[Step 0] Loading game: {url}")
            self.load_page(url, wait_seconds=2.0)

            # Check initialization
            print("\n[Verification] Game Initialization Check")
            init_ok, init_error = self.check_game_initialized()
            results["verification_results"]["initialization"] = init_ok

            if not init_ok:
                if init_error:
                    results["errors"].append(init_error)
                else:
                    results["errors"].append({"message": "Game initialization failed"})
                results["success"] = False
                return results

            # ========== Step 1: Title screen screenshot ==========
            print("\n[Step 1] Waiting for assets to load (10 seconds)...")
            time.sleep(10.0)
            print("\n[Step 1] Taking title screen screenshot...")
            title_screenshot_path = os.path.join(output_dir, "01_title_screen.png")
            self.take_screenshot(title_screenshot_path)
            time.sleep(0.5)

            # Expected background color #0f0f0f = RGB(15, 15, 15)
            expected_bg_color = (15, 15, 15)
            title_analysis = analyze_screenshot(title_screenshot_path, expected_bg_color=expected_bg_color)
            results["verification_results"]["title_screen"]["screenshot_path"] = title_screenshot_path
            results["verification_results"]["title_screen"]["analysis"] = title_analysis
            print(f"  Recommendation: {title_analysis.get('analysis', {}).get('recommendation', 'N/A')}")

            # ========== Step 2: Tap to start game ==========
            print("\n[Step 2] Tapping screen center to start game...")
            self.tap_screen()
            time.sleep(1.0)

            game_started_screenshot_path = os.path.join(output_dir, "02_game_started.png")
            self.take_screenshot(game_started_screenshot_path)
            time.sleep(0.5)

            # Compare with title screen (threshold: 2% for title→started)
            print("  Comparing with title screen...")
            comparison_1_2 = compare_images(title_screenshot_path, game_started_screenshot_path, threshold=2.0)
            results["verification_results"]["game_started"]["screenshot_path"] = game_started_screenshot_path
            results["verification_results"]["game_started"]["comparison"] = {
                "has_changes": comparison_1_2.get("has_significant_changes", False),
                "similarity": comparison_1_2.get("similarity", 0),
                "pixel_diff_percentage": comparison_1_2.get("pixel_diff_percentage", 0)
            }
            print(f"  Similarity: {comparison_1_2.get('similarity', 0)}% ({comparison_1_2.get('pixel_diff_percentage', 0):.1f}% diff)")
            print(f"  {comparison_1_2.get('analysis', {}).get('recommendation', 'N/A')}")

            # ========== Step 3: Virtual controller operations ==========
            # Extended input sequence: direction keys + A/B buttons
            extended_keys = control_keys + ['Z', 'X'] * 5  # Add A(Z) and B(X) buttons, repeated 5 times
            print(f"\n[Step 3] Simulating virtual controller operations ({len(extended_keys)} key presses)...")
            print(f"  Keys: {', '.join(control_keys)} + A/B buttons (Z/X) x 5")

            for i, key in enumerate(extended_keys, 1):
                key_label = key
                if key == 'Z':
                    key_label = 'A (Z)'
                elif key == 'X':
                    key_label = 'B (X)'
                print(f"  [{i}/{len(extended_keys)}] Pressing {key_label}...")
                self.keypress(key)
                time.sleep(0.3)

            time.sleep(0.5)
            game_playing_screenshot_path = os.path.join(output_dir, "03_game_playing.png")
            self.take_screenshot(game_playing_screenshot_path)
            time.sleep(0.5)

            # Compare with game started screen (threshold: 0.02% for started→playing)
            print("  Comparing with game started screen...")
            comparison_2_3 = compare_images(game_started_screenshot_path, game_playing_screenshot_path, threshold=0.02)
            results["verification_results"]["game_playing"]["screenshot_path"] = game_playing_screenshot_path
            results["verification_results"]["game_playing"]["comparison"] = {
                "has_changes": comparison_2_3.get("has_significant_changes", False),
                "similarity": comparison_2_3.get("similarity", 0),
                "pixel_diff_percentage": comparison_2_3.get("pixel_diff_percentage", 0)
            }
            print(f"  Similarity: {comparison_2_3.get('similarity', 0)}% ({comparison_2_3.get('pixel_diff_percentage', 0):.1f}% diff)")
            print(f"  {comparison_2_3.get('analysis', {}).get('recommendation', 'N/A')}")

            # ========== Collect errors ==========
            print("\n[Verification] Collecting JavaScript Errors")
            collected_errors = self.get_collected_errors()
            results["errors"] = collected_errors

            if collected_errors:
                print(f"  ✗ Found {len(collected_errors)} JavaScript error(s):")
                for err in collected_errors:
                    print(f"    - {err.get('message', 'Unknown error')}")
                    if err.get('url'):
                        print(f"      at {err.get('url')}:{err.get('line')}:{err.get('column')}")
            else:
                print("  ✓ No JavaScript errors detected")

            # ========== Final verdict ==========
            print("\n" + "=" * 60)
            print("VERIFICATION RESULTS SUMMARY")
            print("=" * 60)

            game_has_changes_1_2 = comparison_1_2.get("has_significant_changes", False)
            game_has_changes_2_3 = comparison_2_3.get("has_significant_changes", False)
            no_errors = len(collected_errors) == 0

            print(f"  Game Initialization: {'✓' if init_ok else '✗'}")
            print(f"  Title → Started: {'✓ Changed' if game_has_changes_1_2 else '✗ No change'}")
            print(f"  Started → Playing: {'✓ Changed' if game_has_changes_2_3 else '✗ No change'}")
            print(f"  No Console Errors: {'✓' if no_errors else '✗'}")

            # Success condition: initialization OK, both image changes detected, no errors
            results["success"] = (
                init_ok and
                game_has_changes_1_2 and
                game_has_changes_2_3 and
                no_errors
            )

            if results["success"]:
                print("\n✓ GAME VERIFICATION PASSED - Game is working correctly!")
            else:
                print("\n✗ GAME VERIFICATION FAILED - See details above")

        except Exception as e:
            print(f"\nERROR during verification test: {e}")
            import traceback
            traceback.print_exc()
            results["errors"].append({"message": str(e), "type": "test_error"})
        finally:
            self.teardown()
            server.stop()

        return results

    def run_test(self, html_path: str, port: int = 8888) -> dict:
        """Run a standard game test"""
        results = {
            "success": False,
            "html_path": html_path,
            "errors": [],
            "warnings": [],
            "checks": {}
        }

        # Get HTML directory
        html_dir = os.path.dirname(os.path.abspath(html_path))
        html_file = os.path.basename(html_path)

        # Start local server with error capture
        server = LocalServer(html_dir, port, html_file)

        try:
            server.start()
            self.setup()

            # Load wrapper HTML with error handler
            # server.port is the actual port used (within the configured range)
            url = f"http://localhost:{server.port}/__test__.html"
            print(f"  Loading test wrapper: {url}")
            self.load_page(url, wait_seconds=2.0)

            # Check initialization
            print("\n[Check 1] Game Initialization")
            init_ok, init_error = self.check_game_initialized()
            results["checks"]["initialization"] = init_ok
            if init_error:
                results["errors"].append(init_error)

            # If initialization failed, return early
            if not init_ok:
                results["success"] = False
                return results

            # Screen tap test
            print("\n[Check 2] Screen Tap Test")
            self.tap_screen()
            time.sleep(1.0)

            # Check state after tap
            script = """
            return {
                gameState: typeof gameState !== 'undefined' ? gameState :
                           (typeof game !== 'undefined' && game.state ? game.state : 'unknown'),
                isRunning: typeof isRunning !== 'undefined' ? isRunning :
                           (typeof game !== 'undefined' ? game.isRunning : null)
            };
            """
            post_tap_state = self.driver.execute_script(script)
            print(f"  Post-tap state: {json.dumps(post_tap_state, indent=2)}")
            results["checks"]["post_tap_state"] = post_tap_state

            # Additional tap tests
            print("\n[Check 3] Additional Tap Tests")
            for i in range(3):
                self.tap_screen()
                time.sleep(0.3)

            # Collect JavaScript runtime errors
            print("\n[Check 4] Collecting Errors")
            collected_errors = self.get_collected_errors()
            # Append JavaScript errors to existing errors (don't overwrite initialization errors)
            results["errors"].extend(collected_errors)

            if collected_errors:
                print(f"  Found {len(collected_errors)} JavaScript error(s):")
                for err in collected_errors:
                    print(f"    - {err.get('message', 'Unknown error')}")
                    if err.get('url'):
                        print(f"      at {err.get('url')}:{err.get('line')}:{err.get('column')}")
            else:
                print("  No JavaScript errors detected")

            # Save screenshot to work directory
            project_root = os.path.dirname(html_dir)
            work_dir = os.path.join(project_root, "work")
            os.makedirs(work_dir, exist_ok=True)
            screenshot_path = os.path.join(work_dir, "test_screenshot.png")
            self.take_screenshot(screenshot_path)
            results["screenshot"] = screenshot_path

            # Determine success
            results["success"] = init_ok and len(collected_errors) == 0

        except Exception as e:
            print(f"\nERROR during test: {e}")
            results["errors"].append({"message": str(e), "type": "test_error"})
        finally:
            self.teardown()
            server.stop()
            
        return results


def compare_images(image1_path: str, image2_path: str, threshold: float = 0.1) -> dict:
    """
    Compare two images and detect differences

    Args:
        image1_path: Path to first image
        image2_path: Path to second image
        threshold: Pixel difference percentage threshold for detecting significant changes (default: 0.1%)

    Returns:
        {
            "valid": bool,
            "similarity": float,  # 0-100 similarity percentage
            "pixel_diff_percentage": float,  # Percentage of different pixels
            "has_significant_changes": bool,  # True if >= threshold% pixel difference
            "analysis": {
                "image1": str,
                "image2": str,
                "resolution_match": bool,
                "changed_regions": list,
                "recommendation": str
            }
        }
    """
    result = {
        "valid": False,
        "similarity": 0.0,
        "pixel_diff_percentage": 0.0,
        "has_significant_changes": False,
        "analysis": {}
    }

    if not HAS_PIL:
        result["analysis"]["recommendation"] = "PIL not available - skipping image comparison"
        return result

    if not os.path.exists(image1_path) or not os.path.exists(image2_path):
        result["analysis"]["recommendation"] = "One or both image files not found"
        return result

    try:
        img1 = Image.open(image1_path).convert('RGB')
        img2 = Image.open(image2_path).convert('RGB')

        # Check resolution
        if img1.size != img2.size:
            # Resize to match for comparison
            img2 = img2.resize(img1.size)

        width, height = img1.size
        pixels1 = img1.load()
        pixels2 = img2.load()

        # Calculate pixel-level differences
        total_pixels = width * height
        diff_pixels = 0
        changed_regions = []

        # Grid-based region analysis (16x12 grid)
        grid_width = max(1, width // 16)
        grid_height = max(1, height // 12)
        grid_diff_count = 0

        for gx in range(16):
            for gy in range(12):
                x_start = gx * grid_width
                y_start = gy * grid_height
                x_end = min(x_start + grid_width, width)
                y_end = min(y_start + grid_height, height)

                region_diff = 0
                region_total = 0

                for x in range(x_start, x_end):
                    for y in range(y_start, y_end):
                        p1 = pixels1[x, y]
                        p2 = pixels2[x, y]

                        # Euclidean distance of RGB values
                        diff = ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2) ** 0.5
                        if diff > 30:  # Threshold: 30+ indicates difference
                            region_diff += 1
                            diff_pixels += 1
                        region_total += 1

                # Record regions with >= 5% difference
                if region_total > 0:
                    region_diff_percentage = (region_diff / region_total) * 100
                    if region_diff_percentage >= 5:
                        changed_regions.append({
                            "grid": [gx, gy],
                            "position": [x_start, y_start, x_end, y_end],
                            "diff_percentage": round(region_diff_percentage, 2)
                        })
                        grid_diff_count += 1

        pixel_diff_percentage = (diff_pixels / total_pixels) * 100
        similarity = 100.0 - pixel_diff_percentage
        has_significant_changes = pixel_diff_percentage >= threshold   # >= threshold% considered significant

        result["valid"] = True
        result["similarity"] = round(similarity, 2)
        result["pixel_diff_percentage"] = round(pixel_diff_percentage, 2)
        result["has_significant_changes"] = has_significant_changes
        result["analysis"] = {
            "image1": image1_path,
            "image2": image2_path,
            "resolution_match": img1.size == img2.size,
            "resolution": list(img1.size),
            "changed_grid_count": grid_diff_count,
            "changed_regions": changed_regions[:10],  # Record up to 10 regions
            "recommendation": (
                f"✓ Significant changes detected ({pixel_diff_percentage:.1f}% diff) - Game state changed"
                if has_significant_changes
                else f"✗ No significant changes ({pixel_diff_percentage:.1f}% diff) - Similar screens"
            )
        }

        return result

    except Exception as e:
        result["analysis"]["recommendation"] = f"Error comparing images: {str(e)}"
        return result


def analyze_screenshot(screenshot_path: str, expected_bg_color: tuple = None) -> dict:
    """
    Analyze a screenshot image

    Game start check:
    - If upper half is not pitch black (RGB < 50), game started successfully

    Background color check:
    - If expected_bg_color is specified, checks if the background matches

    Args:
        screenshot_path: Path to screenshot image file
        expected_bg_color: Expected background color as (R, G, B) tuple (e.g., (15, 15, 15) for #0f0f0f)

    Returns:
        {
            "valid": bool,
            "game_started": bool,
            "background_color_match": bool (if expected_bg_color specified),
            "analysis": {
                "upper_half_avg_brightness": float,
                "is_upper_half_black": bool,
                "sample_count": int,
                "brightness_range": list,
                "avg_background_color": tuple (if expected_bg_color specified),
                "recommendation": str
            }
        }
    """
    result = {
        "valid": False,
        "game_started": False,
        "analysis": {}
    }

    if not HAS_PIL:
        result["analysis"]["recommendation"] = "PIL not available - skipping image analysis"
        return result

    if not os.path.exists(screenshot_path):
        result["analysis"]["recommendation"] = f"Screenshot file not found: {screenshot_path}"
        return result

    try:
        img = Image.open(screenshot_path)
        img_rgb = img.convert('RGB')
        width, height = img_rgb.size

        # Analyze upper half of image
        upper_half_height = height // 2

        # Sample points evenly from upper half
        sample_points = []
        brightness_values = []
        color_values = []

        # Grid sampling: 10x5 points (total 50 points)
        x_step = width // 10
        y_step = upper_half_height // 5

        for x_idx in range(10):
            for y_idx in range(5):
                x = x_idx * x_step + x_step // 2
                y = y_idx * y_step + y_step // 2

                if x < width and y < upper_half_height:
                    pixel = img_rgb.getpixel((x, y))
                    # Calculate brightness using Rec.709 formula
                    brightness = int(0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2])
                    brightness_values.append(brightness)
                    color_values.append(pixel)
                    sample_points.append({"x": x, "y": y, "brightness": brightness, "color": pixel})

        # Calculate average brightness
        avg_brightness = sum(brightness_values) / len(brightness_values) if brightness_values else 0

        # Check if upper half is pitch black (threshold: 50)
        # Average brightness <= 50 = pitch black = game not started
        is_upper_half_black = avg_brightness < 50
        game_started = not is_upper_half_black

        result["valid"] = True
        result["game_started"] = game_started
        result["analysis"] = {
            "upper_half_avg_brightness": round(avg_brightness, 2),
            "is_upper_half_black": is_upper_half_black,
            "sample_count": len(sample_points),
            "brightness_range": [min(brightness_values), max(brightness_values)],
            "recommendation": (
                "✓ Game started - graphics rendered on upper half" if game_started
                else "✗ Game not started - upper half remains pitch black"
            )
        }

        # Background color check
        if expected_bg_color is not None:
            # Calculate average background color
            avg_r = sum(c[0] for c in color_values) / len(color_values) if color_values else 0
            avg_g = sum(c[1] for c in color_values) / len(color_values) if color_values else 0
            avg_b = sum(c[2] for c in color_values) / len(color_values) if color_values else 0
            avg_bg_color = (round(avg_r), round(avg_g), round(avg_b))

            # Check if color is within tolerance (±10 for each channel)
            tolerance = 10
            color_match = (
                abs(avg_bg_color[0] - expected_bg_color[0]) <= tolerance and
                abs(avg_bg_color[1] - expected_bg_color[1]) <= tolerance and
                abs(avg_bg_color[2] - expected_bg_color[2]) <= tolerance
            )

            result["background_color_match"] = color_match
            result["analysis"]["avg_background_color"] = avg_bg_color
            result["analysis"]["expected_background_color"] = expected_bg_color

            if color_match:
                result["analysis"]["recommendation"] += f" | ✓ Background color matches expected {expected_bg_color}"
            else:
                result["analysis"]["recommendation"] += f" | ✗ Background color {avg_bg_color} does not match expected {expected_bg_color}"

        return result

    except Exception as e:
        result["analysis"]["recommendation"] = f"Error analyzing screenshot: {str(e)}"
        return result


def load_config() -> dict:
    """Load config.json from various locations"""
    # Look for config.json relative to script location
    script_dir = Path(__file__).parent
    config_paths = [
        Path.cwd() / "work/config.json",  # Project work directory (primary)
        script_dir / "../../config.json",
        Path.cwd() / "config.json",
        Path.home() / "github/gamestudio_1984/config.json"
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)

    return {}


def resolve_path(path: str, root_dir: str = None) -> str:
    """
    Resolve path with optional root directory

    Args:
        path: File path (relative or absolute)
        root_dir: Optional root directory to prepend

    Returns:
        Resolved absolute path
    """
    if root_dir:
        return os.path.join(root_dir, path)
    return path


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Firefox Headless Game Tester - Verify game initialization and tap functionality"
        )
        parser.add_argument(
            "html_path",
            help="Path to index.html to test"
        )
        parser.add_argument(
            "--geckodriver",
            help="Path to geckodriver (if not specified, loads from config.json)"
        )
        parser.add_argument(
            "--root_dir",
            help="Root directory (base path for html_path and output)"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8888,
            help="Local server port number (default: 8888)"
        )
        parser.add_argument(
            "--output",
            help="Output test results to JSON file"
        )
        parser.add_argument(
            "--script",
            help="Execute script commands (JSON format array)"
        )
        parser.add_argument(
            "--script_file",
            help="Script file path (JSON file)"
        )
        parser.add_argument(
            "--verification",
            action="store_true",
            help="Run 3-step game verification test (title → tap → controller)"
        )
        parser.add_argument(
            "--control_keys",
            help="Comma-separated keys for controller simulation (default: UP,DOWN,LEFT,RIGHT)"
        )
        parser.add_argument(
            "--output_dir",
            help="Directory to save screenshots (default: project_root/work)"
        )

        args = parser.parse_args()

        # Determine geckodriver path
        geckodriver_path = args.geckodriver
        if not geckodriver_path:
            config = load_config()
            geckodriver_path = config.get("tools", {}).get("geckodriver_path")

        if not geckodriver_path:
            print("ERROR: geckodriver path not specified.")
            print("  Use --geckodriver option or set 'geckodriver_path' in config.json")
            sys.exit(1)

        if not os.path.exists(geckodriver_path):
            print(f"ERROR: geckodriver not found at: {geckodriver_path}")
            sys.exit(1)

        # Resolve paths
        html_path = resolve_path(args.html_path, args.root_dir)
        output_path = resolve_path(args.output, args.root_dir) if args.output else None

        # Verify HTML file exists
        if not os.path.exists(html_path):
            print(f"ERROR: HTML file not found: {html_path}")
            sys.exit(1)

        # Load script commands
        script_commands = None
        if args.script:
            try:
                script_commands = json.loads(args.script)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid script JSON: {e}")
                sys.exit(1)
        elif args.script_file:
            script_file_path = resolve_path(args.script_file, args.root_dir)
            try:
                with open(script_file_path, 'r') as f:
                    script_commands = json.load(f)
            except Exception as e:
                print(f"ERROR: Could not read script file: {e}")
                sys.exit(1)

        # Parse control keys
        control_keys = None
        if args.control_keys:
            control_keys = [k.strip().upper() for k in args.control_keys.split(',')]

        print("=" * 60)
        print("Firefox Headless Game Tester")
        print("=" * 60)
        print(f"  HTML: {html_path}")
        if args.root_dir:
            print(f"  Root Dir: {args.root_dir}")
        print(f"  Geckodriver: {geckodriver_path}")
        print(f"  Port: {args.port}")
        if args.verification:
            print(f"  Mode: 3-Step Game Verification Test")
            if control_keys:
                print(f"  Control Keys: {', '.join(control_keys)}")
        elif script_commands:
            print(f"  Mode: Script ({len(script_commands)} commands)")
        else:
            print(f"  Mode: Standard Test")
        print("=" * 60)

        # Run test
        tester = FirefoxGameTester(geckodriver_path)

        if args.verification:
            # 3-step verification test
            output_dir = resolve_path(args.output_dir, args.root_dir) if args.output_dir else None
            results = tester.run_game_verification_test(
                html_path,
                control_keys=control_keys,
                output_dir=output_dir,
                port=args.port
            )
        elif script_commands:
            # Script mode
            results = tester.run_script_test(html_path, script_commands, args.port)
        else:
            # Standard mode
            results = tester.run_test(html_path, args.port)

        # Output results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        if results["success"]:
            print("✓ All checks passed!")
        else:
            print("✗ Some checks failed")
            if results["errors"]:
                print(f"\nErrors ({len(results['errors'])}):")
                for err in results["errors"]:
                    print(f"  - {err.get('message', 'Unknown')}")

        # Save results to JSON
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {output_path}")

        return 0 if results["success"] else 1

    except Exception as e:
        print(f"\nFATAL ERROR: Unexpected exception occurred", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error message: {str(e)}", file=sys.stderr)
        import traceback
        print("\nFull traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Try to save error to output file if specified
        if 'args' in locals() and args.output:
            try:
                output_path = resolve_path(args.output, args.root_dir) if args.root_dir else args.output
                error_result = {
                    "success": False,
                    "errors": [{
                        "type": "fatal_exception",
                        "message": f"{type(e).__name__}: {str(e)}",
                        "traceback": traceback.format_exc()
                    }]
                }
                with open(output_path, 'w') as f:
                    json.dump(error_result, f, indent=2, ensure_ascii=False)
                print(f"\nError details saved to: {output_path}", file=sys.stderr)
            except:
                pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
