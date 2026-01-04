"""
GameStudio 1984 Web UI - FastAPI Backend (OSS Version)
Provides web interface to run GameStudio 1984 agent and monitor execution
"""
import json
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import uvicorn
import asyncio

app = FastAPI(title="GameStudio 1984 WebUI (OSS)")

# Base directories - OSS version uses single directory structure
BASE_DIR = Path(__file__).parent.parent  # oss/ directory
WORKSPACE_DIR = BASE_DIR / "workspace"
STATE_FILE = Path(__file__).parent / "state.json"
LOGS_DIR = WORKSPACE_DIR / "webui_logs"

# OSS version - single version
OSS_VERSION = "oss"

def get_version_dir(version: str = None) -> Path:
    """Get the base directory (OSS has single version)"""
    return BASE_DIR

def get_workspace_dir(version: str = None) -> Path:
    """Get workspace directory"""
    return WORKSPACE_DIR

def find_workspace_version(workspace_name: str) -> str:
    """Return OSS version for all workspaces"""
    return OSS_VERSION

# Ensure directories exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict:
    """Load current execution state"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[load_state] Error decoding JSON from {STATE_FILE}, returning default state")
        except Exception as e:
            print(f"[load_state] Error reading state file: {e}")
            
    return {
        "status": "idle",
        "pid": None,
        "workspace": None,
        "version": None,
        "prompt": None,
        "start_time": None,
        "log_file": None,
        "completed_workspace": None,
        "session_id": None,
        "jsonl_offset": 0,  # For incremental JSONL reading
        "token_data": {     # Accumulated token data
            "current_task": None,
            "tasks_history": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }
    }


def get_session_state_file(state: Dict) -> Optional[Path]:
    """
    Get session-specific state file path based on workspace, version, and session_id.

    Returns workspace/<project_name>/logs/<session_id>_state.json if all required info is available.
    Otherwise returns None.
    """
    workspace = state.get("workspace")
    version = state.get("version")
    session_id = state.get("session_id")

    if not workspace or not version or not session_id:
        return None

    # Get version-specific workspace directory
    version_workspace_dir = get_workspace_dir(version)

    # Build path: workspace/<project_name>/logs/<session_id>_state.json
    session_state_file = version_workspace_dir / workspace / "logs" / f"{session_id}_state.json"

    return session_state_file


def save_state(state: Dict):
    """
    Save execution state atomically.

    Saves to two locations:
    1. Global state file (webui/state.json) - always
    2. Session-specific file (workspace/<project>/logs/<session_id>_state.json) - only when session_id exists
    """
    # Always save to global state file
    temp_file = STATE_FILE.with_suffix('.tmp')
    try:
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        os.replace(temp_file, STATE_FILE)
    except Exception as e:
        print(f"[save_state] Error saving state to global file: {e}")
        if temp_file.exists():
            try:
                os.remove(temp_file)
            except:
                pass

    # Also save to session-specific location if session_id exists
    session_state_file = get_session_state_file(state)
    if session_state_file:
        temp_session_file = None
        try:
            # Ensure logs directory exists
            session_state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first then rename to ensure atomic write
            temp_session_file = session_state_file.with_suffix('.tmp')
            with open(temp_session_file, 'w') as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            os.replace(temp_session_file, session_state_file)
        except Exception as e:
            print(f"[save_state] Error saving state to session file: {e}")
            if temp_session_file and temp_session_file.exists():
                try:
                    os.remove(temp_session_file)
                except:
                    pass


def check_process_running(pid: Optional[int]) -> bool:
    """Check if process is still running, handling zombies"""
    if pid is None:
        return False
    try:
        # Check if process exists
        os.kill(pid, 0)
        
        # On Linux, check for zombie process via /proc
        if os.path.exists(f"/proc/{pid}/stat"):
            try:
                with open(f"/proc/{pid}/stat", 'r') as f:
                    stat_data = f.read().split()
                    # 3rd field is state (man 5 proc). 'Z' is zombie.
                    if len(stat_data) > 2 and stat_data[2] == 'Z':
                        # It is a zombie. If we are the parent, waitpid will reap it.
                        # Even if we are not the parent, it's effectively dead for our purposes.
                        try:
                            # WNOHANG: return immediately if no child has exited
                            os.waitpid(pid, os.WNOHANG)
                        except (ChildProcessError, OSError):
                            pass
                        return False
            except (IOError, ValueError):
                pass
                
        return True
    except OSError:
        return False


def extract_session_id_from_log(log_file_path: Path) -> Optional[str]:
    """Extract session_id from stdout log file (e.g., 'Session ID: 20251225_103045')"""
    import re

    if not log_file_path.exists():
        return None

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Read first 100 lines (session_id is usually at the top)
            for i, line in enumerate(f):
                if i > 100:
                    break
                match = re.search(r'Session ID:\s*(\d{8}_\d{6})', line)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"[extract_session_id_from_log] Error reading log file: {e}")

    return None


def init_state_on_startup():
    """Initialize state on startup - reset to idle if process is not running"""
    if STATE_FILE.exists():
        state = load_state()
        # If status is running or complete, but process is not actually running, reset to idle
        if state["status"] in ["running", "complete"]:
            if not check_process_running(state.get("pid")):
                state["status"] = "idle"
                state["pid"] = None
                save_state(state)
                print(f"[Startup] Reset state from previous session to idle (process not running)")


# Initialize state on module load
init_state_on_startup()


@app.get("/")
async def root():
    """Root endpoint - main UI"""
    state = load_state()

    # Update state if process has finished
    if state["status"] == "running" and not check_process_running(state["pid"]):
        state["status"] = "complete"
        state["completed_workspace"] = state["workspace"]
        state["pid"] = None
        save_state(state)

    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GameStudio 1984 OSS - WebUI</title>
        <style>
            * {
                box-sizing: border-box;
            }

            body {
                font-family: 'Courier New', monospace;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background: #1a1a1a;
                color: #00ff00;
            }

            h1 {
                color: #00ff00;
                text-shadow: 0 0 10px #00ff00;
                border-bottom: 2px solid #00ff00;
                padding-bottom: 10px;
                margin: 0 0 20px 0;
                font-size: 1.8rem;
            }

            h2 {
                font-size: 1.3rem;
                margin: 15px 0 10px 0;
            }

            .container {
                background: #0a0a0a;
                padding: 20px;
                border-radius: 8px;
                border: 2px solid #00ff00;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
                margin-bottom: 20px;
            }

            .prompt-input {
                width: 100%;
                padding: 12px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                background: #000;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 4px;
                margin-bottom: 10px;
                min-height: 44px;
            }

            .btn {
                padding: 12px 20px;
                min-height: 44px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                font-weight: bold;
                background: #00ff00;
                color: #000;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-right: 10px;
                margin-bottom: 10px;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                white-space: nowrap;
                touch-action: manipulation;
            }

            .btn:hover {
                background: #00cc00;
                box-shadow: 0 0 10px #00ff00;
            }

            .btn:active {
                transform: scale(0.98);
            }

            .btn-danger {
                background: #ff0000;
                color: #fff;
            }

            .btn-danger:hover {
                background: #cc0000;
                box-shadow: 0 0 10px #ff0000;
            }

            .btn:disabled {
                background: #333;
                color: #666;
                cursor: not-allowed;
                opacity: 0.6;
            }

            .log-container {
                background: #000;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #00ff00;
                max-height: 600px;
                overflow-y: auto;
                font-size: 12px;
                line-height: 1.4;
                -webkit-overflow-scrolling: touch;
            }

            .log-line {
                margin: 2px 0;
                white-space: pre-wrap;
                word-wrap: break-word;
                word-break: break-word;
            }

            .asset-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }

            .asset-item {
                background: #000;
                padding: 10px;
                border-radius: 4px;
                border: 1px solid #00ff00;
                text-align: center;
                min-width: 0;
            }

            .asset-item img {
                max-width: 100%;
                height: auto;
                background: #222;
                image-rendering: pixelated;
            }

            .asset-item audio {
                width: 100%;
                margin-top: 10px;
                min-height: 40px;
            }

            .status {
                padding: 5px 10px;
                border-radius: 4px;
                display: inline-block;
                font-weight: bold;
            }

            .status-idle {
                background: #333;
                color: #999;
            }

            .status-running {
                background: #00ff00;
                color: #000;
                animation: pulse 2s infinite;
            }

            .status-complete {
                background: #0080ff;
                color: #fff;
                font-weight: bold;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .workspace-list {
                list-style: none;
                padding: 0;
            }

            .workspace-item {
                padding: 15px;
                margin: 5px 0;
                background: #000;
                border: 1px solid #00ff00;
                border-radius: 4px;
                transition: all 0.2s;
                min-height: 44px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .workspace-item:hover {
                background: #003300;
            }

            .workspace-item a {
                color: #00ff00;
                text-decoration: none;
                flex: 1;
                cursor: pointer;
            }

            .workspace-item a:hover {
                text-decoration: underline;
            }

            .workspace-delete-btn {
                background: #ff0000;
                color: #fff;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.2s;
                min-height: 36px;
                min-width: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .workspace-delete-btn:hover {
                background: #cc0000;
                box-shadow: 0 0 10px #ff0000;
            }

            .workspace-delete-btn:active {
                transform: scale(0.95);
            }

            .workspace-log-btn {
                background: #0066cc;
                color: #fff;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
                margin-right: 5px;
            }

            .workspace-log-btn:hover {
                background: #0055aa;
                box-shadow: 0 0 10px #0066cc;
            }

            .workspace-log-btn:active {
                transform: scale(0.95);
            }

            .log-file-item {
                padding: 12px;
                margin: 5px 0;
                background: #000;
                border: 1px solid #00ff00;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.2s;
            }

            .log-file-item:hover {
                background: #003300;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
            }

            .log-file-item .file-name {
                color: #00ff00;
                font-weight: bold;
            }

            .log-file-item .file-info {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }

            .log-entry {
                padding: 10px;
                margin: 8px 0;
                background: #001100;
                border-left: 3px solid #00ff00;
                border-radius: 3px;
            }

            .log-entry.error {
                border-left-color: #ff0000;
                background: #110000;
            }

            .log-entry.warning {
                border-left-color: #ffaa00;
                background: #110800;
            }

            .log-entry .log-timestamp {
                color: #666;
                font-size: 0.85em;
            }

            .log-entry .log-level {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 0.8em;
                font-weight: bold;
                margin-left: 10px;
            }

            .log-entry .log-level.DEBUG {
                background: #333;
                color: #aaa;
            }

            .log-entry .log-level.INFO {
                background: #003366;
                color: #66ccff;
            }

            .log-entry .log-level.WARNING {
                background: #663300;
                color: #ffaa00;
            }

            .log-entry .log-level.ERROR {
                background: #660000;
                color: #ff6666;
            }

            .log-entry .log-message {
                color: #00ff00;
                margin: 8px 0;
            }

            .log-entry .log-metadata {
                color: #888;
                font-size: 0.85em;
                margin-top: 5px;
                padding-top: 5px;
                border-top: 1px solid #222;
            }

            .text-log-content {
                font-family: monospace;
                color: #00ff00;
                white-space: pre-wrap;
                line-height: 1.4;
            }

            .tab-container {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }

            .tab {
                padding: 12px 20px;
                min-height: 44px;
                background: #000;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 4px 4px 0 0;
                cursor: pointer;
                transition: all 0.2s;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                font-weight: bold;
                display: flex;
                align-items: center;
                touch-action: manipulation;
            }

            .tab.active {
                background: #00ff00;
                color: #000;
            }

            .tab-content {
                display: none;
            }

            .tab-content.active {
                display: block;
            }

            .form-group {
                margin-bottom: 15px;
            }

            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }

            .form-row {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                align-items: flex-end;
            }

            .form-row > * {
                flex: 1;
                min-width: 200px;
            }

            .form-row .btn {
                margin-right: 0;
                margin-bottom: 0;
            }

            .button-group {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 15px;
            }

            .button-group .btn {
                margin-right: 0;
            }

            /* Mobile Responsive Styles */
            @media (max-width: 768px) {
                body {
                    padding: 15px;
                }

                h1 {
                    font-size: 1.5rem;
                }

                h2 {
                    font-size: 1.1rem;
                }

                .container {
                    padding: 15px;
                    margin-bottom: 15px;
                }

                .prompt-input {
                    font-size: 16px;
                    padding: 15px;
                }

                .btn {
                    padding: 15px 20px;
                    font-size: 15px;
                    width: 100%;
                    margin-right: 0;
                    margin-bottom: 10px;
                }

                .form-row {
                    flex-direction: column;
                    gap: 10px;
                }

                .form-row > * {
                    min-width: 100%;
                }

                .button-group {
                    flex-direction: column;
                    gap: 10px;
                }

                .button-group .btn {
                    width: 100%;
                    margin-bottom: 0;
                }

                .log-container {
                    max-height: 400px;
                    font-size: 13px;
                    padding: 12px;
                }

                .asset-grid {
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                    gap: 10px;
                }

                .tab-container {
                    gap: 8px;
                }

                .tab {
                    padding: 12px 15px;
                    font-size: 13px;
                }

                .workspace-item {
                    padding: 12px;
                    min-height: auto;
                }
            }

            @media (max-width: 480px) {
                body {
                    padding: 10px;
                }

                h1 {
                    font-size: 1.3rem;
                    margin-bottom: 15px;
                }

                .container {
                    padding: 12px;
                    margin-bottom: 12px;
                    border-width: 1px;
                }

                .prompt-input {
                    font-size: 16px;
                    padding: 12px;
                    margin-bottom: 8px;
                }

                .btn {
                    padding: 12px 15px;
                    font-size: 14px;
                    margin-bottom: 8px;
                }

                .log-container {
                    max-height: 300px;
                    font-size: 12px;
                    padding: 10px;
                }

                .asset-grid {
                    grid-template-columns: 1fr;
                    gap: 8px;
                }

                .asset-item {
                    padding: 8px;
                }

                .tab {
                    padding: 10px 12px;
                    font-size: 12px;
                }

                label {
                    font-size: 14px;
                }
            }

            /* Modal for image zoom */
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.9);
                justify-content: center;
                align-items: center;
            }

            .modal.active {
                display: flex;
            }

            .modal-content {
                max-width: 90vw;
                max-height: 90vh;
                image-rendering: pixelated;
                border: 2px solid #00ff00;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
            }

            .modal-close {
                position: absolute;
                top: 20px;
                right: 30px;
                color: #00ff00;
                font-size: 40px;
                font-weight: bold;
                cursor: pointer;
            }

            .modal-close:hover {
                color: #00cc00;
            }

            .modal-filename {
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                color: #00ff00;
                font-size: 16px;
                background: rgba(0, 0, 0, 0.8);
                padding: 10px 20px;
                border: 1px solid #00ff00;
                border-radius: 4px;
            }

            /* Created Assets section */
            .created-assets-section {
                margin-top: 20px;
            }

            .created-assets-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 10px;
                margin-top: 10px;
            }

            .created-asset-item {
                background: #000;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #00ff00;
                text-align: center;
                cursor: pointer;
                transition: all 0.2s;
            }

            .created-asset-item:hover {
                background: #003300;
                box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
            }

            .created-asset-item img {
                max-width: 100%;
                height: auto;
                background: #222;
                image-rendering: pixelated;
                min-height: 32px;
            }

            .created-asset-item .asset-filename {
                font-size: 10px;
                color: #00ff00;
                margin-top: 5px;
                word-break: break-all;
            }

            .created-asset-item audio {
                width: 100%;
                margin-top: 5px;
                height: 32px;
            }

            .asset-type-label {
                color: #00ff00;
                font-size: 14px;
                margin: 15px 0 8px 0;
                border-bottom: 1px solid #00ff00;
                padding-bottom: 5px;
            }

            /* Current Status and Tokens section */
            .current-status-section {
                background: #000;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #00ff00;
                margin-bottom: 15px;
            }

            .current-status-section h3 {
                margin: 0 0 10px 0;
                font-size: 1.1rem;
                color: #00ff00;
            }

            .current-status-info {
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 8px 15px;
                font-size: 14px;
            }

            .current-status-info .label {
                font-weight: bold;
                color: #00ff00;
            }

            .current-status-info .value {
                color: #fff;
            }

            .tokens-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 13px;
            }

            .tokens-table th,
            .tokens-table td {
                padding: 8px;
                text-align: left;
                border: 1px solid #00ff00;
            }

            .tokens-table th {
                background: #003300;
                color: #00ff00;
                font-weight: bold;
            }

            .tokens-table td {
                background: #000;
                color: #fff;
            }

            .tokens-table tr:hover td {
                background: #001a00;
            }

            .tokens-table tfoot td {
                background: #003300;
                color: #00ff00;
                font-weight: bold;
            }

            .tokens-table .num {
                text-align: right;
            }

            @media (max-width: 768px) {
                .current-status-info {
                    grid-template-columns: 1fr;
                    gap: 5px;
                }

                .tokens-table {
                    font-size: 11px;
                }

                .tokens-table th,
                .tokens-table td {
                    padding: 5px;
                }
            }
        </style>
    </head>
    <body>
        <h1>🎮 GameStudio 1984 OSS</h1>

        <div class="tab-container">
            <div id="agent-tab-btn" class="tab active" onclick="switchTab('agent')">Agent Execution</div>
            <div id="workspaces-tab-btn" class="tab" onclick="switchTab('workspaces')">Workspaces</div>
            <div id="logs-tab-btn" class="tab" onclick="switchTab('logs')" style="display: none;">Logs</div>
        </div>

        <!-- Agent Execution Tab -->
        <div id="agent-tab" class="tab-content active">
            <div class="container">
                <h2>
                    Status: <span id="status" class="status status-idle">IDLE</span>
                    <button id="new-agent-btn" class="btn" onclick="startNewAgent()" style="display: none; margin-left: 15px;">🚀 New Agent</button>
                </h2>
                <div id="current-info" style="margin-top: 10px; display: none;">
                    <div>Workspace: <strong id="current-workspace"></strong></div>
                    <div>Version: <strong id="current-version"></strong></div>
                    <div>Prompt: <strong id="current-prompt"></strong></div>
                    <div>Started: <strong id="current-start-time"></strong></div>
                </div>
            </div>

            <div class="container" id="prompt-form">
                <h2>Start New Agent</h2>
                <div class="form-group">
                    <label for="project-input">Project Name:</label>
                    <input type="text" id="project-input" class="prompt-input"
                           placeholder="Enter project name (e.g., 'space_shooter')">
                </div>
                <div class="form-group">
                    <label for="prompt-input">Game Request:</label>
                    <textarea id="prompt-input" class="prompt-input" rows="4"
                              placeholder="Enter your game request (e.g., 'Create a space shooter game')"></textarea>
                </div>
                <!-- OSS version - no version selection needed -->
                <input type="hidden" id="version-select" value="oss">
                <div class="form-group">
                    <label for="model-select">Default Model:</label>
                    <select id="model-select" class="prompt-input" style="padding: 12px;">
                        <option value="gemini-2.5-flash-lite-preview-09-2025" selected>gemini-2.5-flash-lite-preview-09-2025</option>
                        <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                        <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                        <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                        <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                    </select>
                </div>
                <details style="margin-top: 10px;">
                    <summary style="cursor: pointer; color: #00ff00; margin-bottom: 10px;">⚙️ Per-Role Model Configuration (Optional)</summary>
                    <div class="form-group">
                        <label for="designer-model">Designer:</label>
                        <select id="designer-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="programmer-model">Programmer:</label>
                        <select id="programmer-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview" selected>gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="graphic-artist-model">Graphic Artist:</label>
                        <select id="graphic-artist-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="sound-artist-model">Sound Artist:</label>
                        <select id="sound-artist-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="tester-model">Tester:</label>
                        <select id="tester-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview" selected>gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="manager-model">Manager:</label>
                        <select id="manager-model" class="prompt-input" style="padding: 12px;">
                            <option value="">Use default</option>
                            <option value="gemini-2.5-flash-lite-preview-09-2025">gemini-2.5-flash-lite-preview-09-2025</option>
                            <option value="gemini-2.5-flash-preview-09-2025">gemini-2.5-flash-preview-09-2025</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                            <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                            <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                        </select>
                    </div>
                </details>
                <div class="button-group">
                    <button class="btn" onclick="startAgent()">🚀 Start Agent</button>
                </div>
            </div>

            <div class="container" id="execution-panel" style="display: none;">
                <h2>Execution Log</h2>
                <div class="button-group">
                    <button class="btn btn-danger" onclick="stopAgent()">🛑 Stop Agent</button>
                    <button class="btn" onclick="refreshLog()">🔄 Refresh Log</button>
                </div>
                <div class="log-container" id="log-output"></div>

                <!-- Current Status Section -->
                <div class="current-status-section" id="current-status-display" style="display: none;">
                    <h3>📊 Current Status</h3>
                    <div class="current-status-info">
                        <div class="label">Role:</div>
                        <div class="value" id="current-role">-</div>
                        <div class="label">Task:</div>
                        <div class="value" id="current-task-name">-</div>
                        <div class="label">Model:</div>
                        <div class="value" id="current-model">-</div>
                        <div class="label">Input Tokens:</div>
                        <div class="value" id="current-input-tokens">0</div>
                        <div class="label">Output Tokens:</div>
                        <div class="value" id="current-output-tokens">0</div>
                    </div>
                </div>

                <!-- Tokens History Section -->
                <div class="current-status-section" id="tokens-history-display" style="display: none;">
                    <h3>💰 Tokens</h3>
                    <table class="tokens-table">
                        <thead>
                            <tr>
                                <th>Role</th>
                                <th>Task</th>
                                <th>Model</th>
                                <th class="num">Input Tokens</th>
                                <th class="num">Output Tokens</th>
                                <th class="num">Cost (USD)</th>
                            </tr>
                        </thead>
                        <tbody id="tokens-history-body">
                            <!-- Populated by JavaScript -->
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="3"><strong>Total</strong></td>
                                <td class="num" id="total-input-tokens">0</td>
                                <td class="num" id="total-output-tokens">0</td>
                                <td class="num" id="total-cost">$0.00</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div class="created-assets-section">
                    <h2>Created Assets</h2>
                    <div class="asset-type-label">🖼️ Images</div>
                    <div class="created-assets-grid" id="images-grid"></div>
                    <div class="asset-type-label">🔊 Sounds</div>
                    <div class="created-assets-grid" id="sounds-grid"></div>
                    <div class="asset-type-label">📸 Screen Shots</div>
                    <div class="created-assets-grid" id="screenshots-grid"></div>
                </div>
            </div>
        </div>

        <!-- Image Modal -->
        <div id="image-modal" class="modal" onclick="closeModal()">
            <span class="modal-close">&times;</span>
            <img id="modal-image" class="modal-content" src="" alt="Zoomed Image">
            <div id="modal-filename" class="modal-filename"></div>
        </div>

        <!-- Workspaces Tab -->
        <div id="workspaces-tab" class="tab-content">
            <div class="container">
                <h2>Available Workspaces</h2>
                <div class="button-group">
                    <button class="btn" onclick="refreshWorkspaces()">🔄 Refresh</button>
                </div>
                <ul class="workspace-list" id="workspace-list">
                    <li>Loading...</li>
                </ul>
            </div>
        </div>

        <!-- Logs Tab -->
        <div id="logs-tab" class="tab-content">
            <div class="container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <h2 id="logs-workspace-title">Logs</h2>
                        <p id="logs-workspace-info" style="color: #666; margin: 5px 0;"></p>
                    </div>
                    <button class="btn" onclick="switchTab('workspaces')" style="background: #666;">← Back to Workspaces</button>
                </div>
                <div id="logs-file-list" style="margin-bottom: 20px;">
                    <h3>Log Files</h3>
                    <ul class="workspace-list" id="log-files-list">
                        <li>Loading...</li>
                    </ul>
                </div>
                <div id="log-viewer" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h3 id="log-file-title">Log Content</h3>
                        <button class="btn" onclick="closeLogViewer()" style="background: #666;">← Back to File List</button>
                    </div>
                    <div id="log-content" style="background: #000; border: 1px solid #00ff00; border-radius: 4px; padding: 15px; max-height: 600px; overflow-y: auto;">
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentTab = 'agent';
            let eventSource = null;
            let currentWorkspace = null;
            let currentVersionFilter = 'all';  // Track current version filter
            let createdImages = new Map();  // filename -> path (to avoid duplicates)
            let createdSounds = new Map();  // filename -> path (to avoid duplicates)
            let createdScreenshots = new Map();  // path -> path (to show all test screenshots)

            function switchTab(tab) {
                currentTab = tab;
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

                if (tab === 'agent') {
                    document.getElementById('agent-tab-btn').classList.add('active');
                    document.getElementById('agent-tab').classList.add('active');
                    updateStatus();
                } else if (tab === 'workspaces') {
                    document.getElementById('workspaces-tab-btn').classList.add('active');
                    document.getElementById('workspaces-tab').classList.add('active');
                    refreshWorkspaces();
                } else if (tab === 'logs') {
                    document.getElementById('logs-tab-btn').classList.add('active');
                    document.getElementById('logs-tab').classList.add('active');
                }
            }

            async function updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const state = await response.json();

                    const statusEl = document.getElementById('status');
                    const newAgentBtn = document.getElementById('new-agent-btn');
                    const promptForm = document.getElementById('prompt-form');
                    const executionPanel = document.getElementById('execution-panel');
                    const currentInfo = document.getElementById('current-info');

                    if (state.status === 'running') {
                        statusEl.className = 'status status-running';
                        statusEl.textContent = 'RUNNING';
                        newAgentBtn.style.display = 'none';
                        promptForm.style.display = 'none';
                        executionPanel.style.display = 'block';
                        currentInfo.style.display = 'block';

                        document.getElementById('current-workspace').textContent = state.workspace;
                        document.getElementById('current-version').textContent = state.version || 'v0.4';
                        document.getElementById('current-prompt').textContent = state.prompt;
                        document.getElementById('current-start-time').textContent = state.start_time;

                        currentWorkspace = state.workspace;

                        if (!eventSource) {
                            startLogStreaming();
                        }

                        // Scan for existing screenshots
                        scanAndLoadScreenshots();

                        // Update tokens display when running
                        updateTokensDisplay();
                    } else if (state.status === 'complete') {
                        statusEl.className = 'status status-complete';
                        statusEl.textContent = 'COMPLETE';
                        newAgentBtn.style.display = 'inline-flex';
                        promptForm.style.display = 'none';
                        executionPanel.style.display = 'block';
                        currentInfo.style.display = 'block';

                        document.getElementById('current-workspace').textContent = state.workspace || state.completed_workspace;
                        document.getElementById('current-version').textContent = state.version || 'v0.4';
                        document.getElementById('current-prompt').textContent = state.prompt;
                        document.getElementById('current-start-time').textContent = state.start_time;

                        currentWorkspace = state.workspace || state.completed_workspace;

                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }

                        // Scan for screenshots when complete
                        scanAndLoadScreenshots();

                        // Update tokens display when complete
                        updateTokensDisplay();
                    } else {
                        statusEl.className = 'status status-idle';
                        statusEl.textContent = 'IDLE';
                        newAgentBtn.style.display = 'none';
                        promptForm.style.display = 'block';
                        executionPanel.style.display = 'none';
                        currentInfo.style.display = 'none';

                        if (eventSource) {
                            eventSource.close();
                            eventSource = null;
                        }
                    }
                } catch (error) {
                    console.error('Error updating status:', error);
                }
            }

            async function startAgent() {
                const project = document.getElementById('project-input').value.trim();
                const prompt = document.getElementById('prompt-input').value.trim();
                const version = document.getElementById('version-select').value;
                const model = document.getElementById('model-select').value;

                // Collect per-role model selections
                const roleModels = {};
                const designerModel = document.getElementById('designer-model').value;
                const programmerModel = document.getElementById('programmer-model').value;
                const graphicArtistModel = document.getElementById('graphic-artist-model').value;
                const soundArtistModel = document.getElementById('sound-artist-model').value;
                const testerModel = document.getElementById('tester-model').value;
                const managerModel = document.getElementById('manager-model').value;

                if (designerModel) roleModels.designer = designerModel;
                if (programmerModel) roleModels.programmer = programmerModel;
                if (graphicArtistModel) roleModels.graphic_artist = graphicArtistModel;
                if (soundArtistModel) roleModels.sound_artist = soundArtistModel;
                if (testerModel) roleModels.tester = testerModel;
                if (managerModel) roleModels.manager = managerModel;

                if (!prompt) {
                    alert('Please enter a prompt');
                    return;
                }

                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        prompt: prompt,
                        project: project,
                        version: version,
                        model: model,
                        role_models: roleModels
                    })
                });

                const result = await response.json();
                if (response.ok) {
                    document.getElementById('project-input').value = '';
                    document.getElementById('prompt-input').value = '';
                    updateStatus();
                } else {
                    alert('Error: ' + result.error);
                }
            }

            async function stopAgent() {
                if (!confirm('Are you sure you want to stop the agent?')) {
                    return;
                }

                const response = await fetch('/api/stop', {method: 'POST'});
                const result = await response.json();

                if (response.ok) {
                    updateStatus();
                } else {
                    alert('Error: ' + result.error);
                }
            }

            async function startNewAgent() {
                const response = await fetch('/api/reset', {method: 'POST'});
                const result = await response.json();

                if (response.ok) {
                    // Clear the log output and assets
                    document.getElementById('log-output').innerHTML = '';
                    createdImages.clear();
                    createdSounds.clear();
                    createdScreenshots.clear();
                    document.getElementById('images-grid').innerHTML = '';
                    document.getElementById('sounds-grid').innerHTML = '';
                    document.getElementById('screenshots-grid').innerHTML = '';

                    // Update status to show the prompt form
                    updateStatus();
                } else {
                    alert('Error: ' + result.error);
                }
            }

            function startLogStreaming() {
                const logOutput = document.getElementById('log-output');
                logOutput.innerHTML = '';

                // Clear asset lists
                createdImages.clear();
                createdSounds.clear();
                createdScreenshots.clear();
                document.getElementById('images-grid').innerHTML = '';
                document.getElementById('sounds-grid').innerHTML = '';
                document.getElementById('screenshots-grid').innerHTML = '';

                eventSource = new EventSource('/api/logs/stream');

                eventSource.addEventListener('log', (event) => {
                    const logData = JSON.parse(event.data);
                    appendLogLine(logData);
                });

                eventSource.addEventListener('complete', (event) => {
                    const data = JSON.parse(event.data);
                    appendCompletionMessage(data);
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                    // Update status immediately and again after delay to ensure UI refresh
                    updateStatus();
                    setTimeout(updateStatus, 1000);
                    setTimeout(updateStatus, 2000);
                });

                eventSource.onerror = (error) => {
                    console.error('EventSource error:', error);
                    eventSource.close();
                    eventSource = null;
                };
            }

            function appendLogLine(logData) {
                const logOutput = document.getElementById('log-output');

                // Check if user is at the bottom before adding new content
                const isAtBottom = logOutput.scrollHeight - logOutput.scrollTop - logOutput.clientHeight < 50;

                const logLine = document.createElement('div');
                logLine.className = 'log-line';

                if (logData.type === 'text') {
                    logLine.textContent = logData.content;
                } else if (logData.type === 'image') {
                    // Create text content
                    const textSpan = document.createElement('span');
                    textSpan.textContent = logData.content;
                    logLine.appendChild(textSpan);
                    logLine.appendChild(document.createElement('br'));

                    // Create image with retry logic
                    const img = document.createElement('img');
                    img.style.maxWidth = '400px';
                    img.style.margin = '10px 0';
                    img.style.border = '1px solid #00ff00';
                    img.style.background = '#222';
                    img.style.imageRendering = 'pixelated';
                    img.alt = 'Screenshot';
                    addImageWithRetry(img, logData.image_path);
                    logLine.appendChild(img);

                    // Add to Created Assets if it's an asset image
                    if (logData.image_path.includes('/assets/') && logData.image_path.includes('/images/')) {
                        const filename = logData.image_path.split('/').pop();
                        addCreatedImage(filename, logData.image_path);
                    }
                    // Add to Screen Shots if it's from work/test directory
                    else if (logData.image_path.includes('/work/') && logData.image_path.includes('/test/')) {
                        const filename = logData.image_path.split('/').pop();
                        addCreatedScreenshot(filename, logData.image_path);
                    }
                } else if (logData.type === 'test_screenshots') {
                    // Display multiple screenshots from test_result.json
                    const textSpan = document.createElement('span');
                    textSpan.textContent = logData.content;
                    logLine.appendChild(textSpan);
                    logLine.appendChild(document.createElement('br'));

                    // Create container for screenshots
                    const screenshotsContainer = document.createElement('div');
                    screenshotsContainer.style.display = 'flex';
                    screenshotsContainer.style.flexWrap = 'wrap';
                    screenshotsContainer.style.margin = '10px 0';

                    // Create each screenshot with retry logic
                    logData.screenshots.forEach(path => {
                        const img = document.createElement('img');
                        img.style.maxWidth = '250px';
                        img.style.margin = '5px';
                        img.style.border = '1px solid #00ff00';
                        img.style.background = '#222';
                        img.style.imageRendering = 'pixelated';
                        img.alt = 'Test Screenshot';
                        addImageWithRetry(img, path);
                        screenshotsContainer.appendChild(img);

                        // Add to Screen Shots section
                        const filename = path.split('/').pop();
                        addCreatedScreenshot(filename, path);
                    });

                    logLine.appendChild(screenshotsContainer);
                } else if (logData.type === 'audio') {
                    // Create text content
                    const textSpan = document.createElement('span');
                    textSpan.textContent = logData.content;
                    logLine.appendChild(textSpan);
                    logLine.appendChild(document.createElement('br'));

                    // Create audio element with retry logic
                    const audio = document.createElement('audio');
                    audio.controls = true;
                    audio.style.margin = '10px 0';
                    addAudioWithRetry(audio, logData.audio_path);
                    logLine.appendChild(audio);

                    // Add to Created Assets if it's an asset sound
                    if (logData.audio_path.includes('/assets/') && logData.audio_path.includes('/sounds/')) {
                        const filename = logData.audio_path.split('/').pop();
                        addCreatedSound(filename, logData.audio_path);
                    }
                } else if (logData.type === 'asset_image') {
                    // New type for asset images detected from log
                    logLine.textContent = logData.content;
                    addCreatedImage(logData.filename, logData.image_path);
                } else if (logData.type === 'asset_sound') {
                    // New type for asset sounds detected from log
                    logLine.textContent = logData.content;
                    addCreatedSound(logData.filename, logData.audio_path);
                } else if (logData.type === 'tester_complete') {
                    // Tester role completed - scan for screenshots
                    logLine.textContent = logData.content;
                    scanAndLoadScreenshots();
                }

                logOutput.appendChild(logLine);

                // Only auto-scroll if user was already at the bottom
                if (isAtBottom) {
                    logOutput.scrollTop = logOutput.scrollHeight;
                }
            }

            function addImageWithRetry(imgElement, path, maxRetries = 5, initialDelay = 1000) {
                let retryCount = 0;

                imgElement.onerror = function() {
                    retryCount++;
                    if (retryCount <= maxRetries) {
                        const delay = initialDelay * Math.pow(2, retryCount - 1); // exponential backoff: 1s, 2s, 4s, 8s, 16s
                        console.log(`Retrying image load (${retryCount}/${maxRetries}) after ${delay}ms: ${path}`);
                        setTimeout(() => {
                            // Force reload by adding cache-busting parameter
                            imgElement.src = path + '?retry=' + retryCount + '&t=' + Date.now();
                        }, delay);
                    } else {
                        console.error(`Failed to load image after ${maxRetries} retries: ${path}`);
                        // Show visual feedback for failed image
                        imgElement.style.opacity = '0.5';
                        imgElement.style.filter = 'grayscale(100%)';
                        imgElement.alt = 'Failed to load image (click to retry in modal)';
                    }
                };

                imgElement.src = path;
            }

            function addAudioWithRetry(audioElement, path, maxRetries = 5, initialDelay = 1000) {
                let retryCount = 0;

                audioElement.onerror = function() {
                    retryCount++;
                    if (retryCount <= maxRetries) {
                        const delay = initialDelay * Math.pow(2, retryCount - 1); // exponential backoff: 1s, 2s, 4s, 8s, 16s
                        console.log(`Retrying audio load (${retryCount}/${maxRetries}) after ${delay}ms: ${path}`);
                        setTimeout(() => {
                            // Force reload by adding cache-busting parameter
                            audioElement.src = path + '?retry=' + retryCount + '&t=' + Date.now();
                            audioElement.load(); // Reload the audio element
                        }, delay);
                    } else {
                        console.error(`Failed to load audio after ${maxRetries} retries: ${path}`);
                        // Show visual feedback for failed audio
                        audioElement.style.opacity = '0.5';
                        audioElement.title = 'Failed to load audio file';
                    }
                };

                audioElement.src = path;
            }

            async function addCreatedImage(filename, path) {
                // Skip if already added (same filename)
                if (createdImages.has(filename)) {
                    return;
                }
                createdImages.set(filename, path);

                const imagesGrid = document.getElementById('images-grid');
                const assetItem = document.createElement('div');
                assetItem.className = 'created-asset-item';

                // Create img element separately to add retry logic
                const img = document.createElement('img');
                img.alt = escapeHtml(filename);
                addImageWithRetry(img, path);

                const filenameDiv = document.createElement('div');
                filenameDiv.className = 'asset-filename';
                filenameDiv.textContent = filename;

                assetItem.appendChild(img);
                assetItem.appendChild(filenameDiv);
                imagesGrid.appendChild(assetItem);

                // Fetch and apply background color from asset metadata
                if (currentWorkspace) {
                    try {
                        const response = await fetch(`/api/asset-metadata/${encodeURIComponent(currentWorkspace)}/${encodeURIComponent(filename)}`);
                        if (response.ok) {
                            const metadata = await response.json();
                            if (metadata.background_color) {
                                // Apply background color to the image container
                                img.style.backgroundColor = metadata.background_color;
                                // Store metadata for modal view
                                assetItem.dataset.bgColor = metadata.background_color;
                            }
                        }
                    } catch (error) {
                        console.log(`Could not fetch metadata for ${filename}:`, error);
                    }
                }

                // Set click handler after metadata is loaded
                assetItem.onclick = function() {
                    const bgColor = assetItem.dataset.bgColor || '#222';
                    openModal(path, filename, bgColor);
                };
            }

            function addCreatedSound(filename, path) {
                // Skip if already added (same filename)
                if (createdSounds.has(filename)) {
                    return;
                }
                createdSounds.set(filename, path);

                const soundsGrid = document.getElementById('sounds-grid');
                const assetItem = document.createElement('div');
                assetItem.className = 'created-asset-item';
                assetItem.onclick = function(e) { e.stopPropagation(); };

                // Create filename div
                const filenameDiv = document.createElement('div');
                filenameDiv.className = 'asset-filename';
                filenameDiv.textContent = filename;

                // Create audio element with retry logic
                const audio = document.createElement('audio');
                audio.controls = true;
                addAudioWithRetry(audio, path);

                assetItem.appendChild(filenameDiv);
                assetItem.appendChild(audio);
                soundsGrid.appendChild(assetItem);
            }

            function addCreatedScreenshot(filename, path) {
                // Don't skip duplicates - we want to show all test screenshots from all runs
                // Use path as key to avoid exact duplicates
                if (createdScreenshots.has(path)) {
                    return;
                }
                createdScreenshots.set(path, path);

                const screenshotsGrid = document.getElementById('screenshots-grid');
                const assetItem = document.createElement('div');
                assetItem.className = 'created-asset-item';
                assetItem.onclick = function() { openModal(path, filename); };

                // Create img element separately to add retry logic
                const img = document.createElement('img');
                img.alt = escapeHtml(filename);
                addImageWithRetry(img, path);

                const filenameDiv = document.createElement('div');
                filenameDiv.className = 'asset-filename';
                filenameDiv.textContent = filename;

                assetItem.appendChild(img);
                assetItem.appendChild(filenameDiv);
                screenshotsGrid.appendChild(assetItem);
            }

            async function scanAndLoadScreenshots() {
                // Get current workspace from URL or state
                const workspace = currentWorkspace;
                if (!workspace) {
                    console.log('No workspace selected, skipping screenshot scan');
                    return;
                }

                try {
                    console.log(`Scanning for screenshots in workspace: ${workspace}`);
                    const response = await fetch(`/api/screenshots?workspace=${encodeURIComponent(workspace)}`);
                    if (!response.ok) {
                        console.error('Failed to scan screenshots:', response.statusText);
                        return;
                    }

                    const data = await response.json();
                    console.log(`Found ${data.screenshots.length} screenshots`);

                    // Add each screenshot to the grid
                    data.screenshots.forEach(screenshot => {
                        addCreatedScreenshot(screenshot.filename, screenshot.path);
                    });
                } catch (error) {
                    console.error('Error scanning screenshots:', error);
                }
            }

            function openModal(imagePath, filename, bgColor = '#222') {
                const modal = document.getElementById('image-modal');
                const modalImage = document.getElementById('modal-image');
                const modalFilename = document.getElementById('modal-filename');

                modalImage.src = imagePath;
                modalFilename.textContent = filename;

                // Apply background color to modal image
                modalImage.style.backgroundColor = bgColor;

                modal.classList.add('active');
            }

            function closeModal() {
                const modal = document.getElementById('image-modal');
                modal.classList.remove('active');
            }

            // Close modal with Escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    closeModal();
                }
            });

            function appendCompletionMessage(data) {
                const logOutput = document.getElementById('log-output');
                const completionLine = document.createElement('div');
                completionLine.className = 'log-line';
                completionLine.style.background = '#003300';
                completionLine.style.padding = '10px';
                completionLine.style.margin = '10px 0';
                completionLine.style.border = '2px solid #00ff00';
                completionLine.innerHTML = `
                    <strong>✅ ${data.message}</strong><br>
                    <a href="${data.message.match(/\/game\/[^\s]+/)[0]}"
                       target="_blank"
                       style="color: #00ff00; text-decoration: underline;">
                        🎮 Open Game
                    </a>
                `;
                logOutput.appendChild(completionLine);
                logOutput.scrollTop = logOutput.scrollHeight;
            }

            async function refreshLog() {
                // Fallback function - not used with SSE
                const response = await fetch('/api/logs');
                const data = await response.json();

                const logOutput = document.getElementById('log-output');
                logOutput.innerHTML = data.logs.map(line =>
                    `<div class="log-line">${escapeHtml(line)}</div>`
                ).join('');

                logOutput.scrollTop = logOutput.scrollHeight;
            }

            async function refreshWorkspaces() {
                // Build API URL with version filter if needed
                let url = '/api/workspaces';
                if (currentVersionFilter !== 'all') {
                    url += `?version=${currentVersionFilter}`;
                }

                const response = await fetch(url);
                const workspaces = await response.json();

                const workspaceList = document.getElementById('workspace-list');

                if (workspaces.length === 0) {
                    workspaceList.innerHTML = '<li style="color: #666;">No workspaces found</li>';
                    return;
                }

                workspaceList.innerHTML = workspaces.map(ws => `
                    <li class="workspace-item">
                        <a href="/game/${ws.name}" target="_blank">
                            <strong>${ws.name}</strong><br>
                            <small>${ws.created}</small>
                        </a>
                        <div>
                            <button class="workspace-log-btn" onclick="window.open('/files?workspace=${encodeURIComponent(ws.name)}&version=${encodeURIComponent(ws.version)}', '_blank'); event.stopPropagation();" title="Browse project files">
                                📁 Browse Files
                            </button>
                            <button class="workspace-log-btn" onclick="showWorkspaceLogs('${ws.name.replace(/'/g, "\\\\'")}', '${ws.version}'); event.stopPropagation();" title="View logs">
                                📋 Show Log
                            </button>
                            <button class="workspace-delete-btn" onclick="deleteWorkspace('${ws.name.replace(/'/g, "\\\\'")}'); event.stopPropagation();" title="Delete workspace">
                                🗑️
                            </button>
                        </div>
                    </li>
                `).join('');
            }

            function filterWorkspaces(version) {
                currentVersionFilter = version;

                // Update button styles to show active filter
                document.querySelectorAll('.btn-filter').forEach(btn => {
                    btn.style.background = '';
                });

                if (version === 'all') {
                    document.getElementById('filter-all').style.background = '#00aa00';
                } else if (version === 'v0.7') {
                    document.getElementById('filter-v07').style.background = '#00aa00';
                } else if (version === 'v0.6') {
                    document.getElementById('filter-v06').style.background = '#00aa00';
                } else if (version === 'v0.5') {
                    document.getElementById('filter-v05').style.background = '#00aa00';
                } else if (version === 'v0.4') {
                    document.getElementById('filter-v04').style.background = '#00aa00';
                }

                // Refresh the workspace list with the new filter
                refreshWorkspaces();
            }

            async function deleteWorkspace(workspaceName) {
                if (!confirm(`Delete this project?\n\nWorkspace: ${workspaceName}\n\nThis action cannot be undone.`)) {
                    return;
                }

                try {
                    const response = await fetch(`/api/workspaces/${workspaceName}`, {
                        method: 'DELETE'
                    });

                    const result = await response.json();

                    if (response.ok) {
                        // Refresh the workspace list
                        await refreshWorkspaces();
                    } else {
                        alert('Error deleting workspace: ' + (result.detail || result.error || 'Unknown error'));
                    }
                } catch (error) {
                    alert('Error deleting workspace: ' + error.message);
                }
            }

            // Log viewer functions
            let currentLogsWorkspace = null;
            let currentLogsVersion = null;

            async function showWorkspaceLogs(workspaceName, version) {
                currentLogsWorkspace = workspaceName;
                currentLogsVersion = version;

                // Show logs tab button and switch to it
                document.getElementById('logs-tab-btn').style.display = 'block';
                switchTab('logs');

                // Update title
                document.getElementById('logs-workspace-title').textContent = `Logs - ${workspaceName}`;
                document.getElementById('logs-workspace-info').textContent = `Version: ${version}`;

                // Show file list, hide viewer
                document.getElementById('logs-file-list').style.display = 'block';
                document.getElementById('log-viewer').style.display = 'none';

                // Load log files
                await loadLogFiles(workspaceName, version);
            }

            async function loadLogFiles(workspaceName, version) {
                try {
                    const response = await fetch(`/api/workspaces/${workspaceName}/logs?version=${version}`);
                    const files = await response.json();

                    const logFilesList = document.getElementById('log-files-list');

                    if (files.length === 0) {
                        logFilesList.innerHTML = '<li style="color: #666;">No log files found</li>';
                        return;
                    }

                    logFilesList.innerHTML = files.map(file => `
                        <li class="log-file-item" onclick="viewLogFile('${file.name.replace(/'/g, "\\'")}')">
                            <div class="file-name">${file.name}</div>
                            <div class="file-info">Size: ${formatFileSize(file.size)} | Modified: ${file.modified}</div>
                        </li>
                    `).join('');
                } catch (error) {
                    document.getElementById('log-files-list').innerHTML =
                        '<li style="color: #ff0000;">Error loading log files: ' + error.message + '</li>';
                }
            }

            async function viewLogFile(filename) {
                try {
                    const response = await fetch(`/api/workspaces/${currentLogsWorkspace}/logs/${filename}?version=${currentLogsVersion}`);
                    const data = await response.json();

                    // Hide file list, show viewer
                    document.getElementById('logs-file-list').style.display = 'none';
                    document.getElementById('log-viewer').style.display = 'block';
                    document.getElementById('log-file-title').textContent = filename;

                    const logContent = document.getElementById('log-content');

                    if (filename.endsWith('.jsonl')) {
                        // Render JSONL log viewer
                        renderJsonlLog(data.content, logContent);
                    } else {
                        // Render text log
                        renderTextLog(data.content, logContent);
                    }
                } catch (error) {
                    alert('Error loading log file: ' + error.message);
                }
            }

            function renderJsonlLog(content, container) {
                const lines = content.trim().split('\\n');
                const entries = lines.map(line => {
                    try {
                        return JSON.parse(line);
                    } catch (e) {
                        return null;
                    }
                }).filter(entry => entry !== null);

                if (entries.length === 0) {
                    container.innerHTML = '<div style="color: #666;">Empty log file</div>';
                    return;
                }

                container.innerHTML = entries.map(entry => {
                    const level = entry.level || 'INFO';
                    const timestamp = entry.timestamp || '';
                    const message = entry.message || '';
                    const category = entry.category || '';
                    const event = entry.event || '';

                    let entryClass = 'log-entry';
                    if (level === 'ERROR') entryClass += ' error';
                    else if (level === 'WARNING') entryClass += ' warning';

                    let metadataHtml = '';
                    if (entry.metadata) {
                        const metadataStr = JSON.stringify(entry.metadata, null, 2);
                        metadataHtml = `<div class="log-metadata"><pre style="margin: 0;">${escapeHtml(metadataStr)}</pre></div>`;
                    }

                    return `
                        <div class="${entryClass}">
                            <div>
                                <span class="log-timestamp">${timestamp}</span>
                                <span class="log-level ${level}">${level}</span>
                                ${category ? `<span style="color: #888; margin-left: 10px;">[${category}${event ? ':' + event : ''}]</span>` : ''}
                            </div>
                            <div class="log-message">${escapeHtml(message)}</div>
                            ${metadataHtml}
                        </div>
                    `;
                }).join('');
            }

            function renderTextLog(content, container) {
                container.innerHTML = `<div class="text-log-content">${escapeHtml(content)}</div>`;
            }

            function closeLogViewer() {
                document.getElementById('logs-file-list').style.display = 'block';
                document.getElementById('log-viewer').style.display = 'none';
            }

            function formatFileSize(bytes) {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Calculate cost based on model and token counts
            function calculateCost(model, inputTokens, outputTokens) {
                // Model pricing per 1M tokens (USD)
                const pricing = {
                    'gemini-3-pro': { input: 2.00, output: 12.00 },
                    'gemini-3-flash': { input: 0.50, output: 3.00 },
                    'gemini-2.5-pro': { input: 1.25, output: 10.00 },
                    'gemini-2.5-flash': { input: 0.30, output: 2.50 },
                    'gemini-2.5-flash-lite': { input: 0.10, output: 0.40 }
                };

                // Extract base model name (handle suffixes like -preview)
                let baseModel = model;
                for (const modelName in pricing) {
                    if (model.startsWith(modelName)) {
                        baseModel = modelName;
                        break;
                    }
                }

                // Get pricing for the model
                const modelPricing = pricing[baseModel];
                if (!modelPricing) {
                    console.warn(`Unknown model pricing for: ${model}`);
                    return 0;
                }

                // Calculate cost (tokens / 1,000,000 * price per 1M)
                const inputCost = (inputTokens / 1000000) * modelPricing.input;
                const outputCost = (outputTokens / 1000000) * modelPricing.output;

                return inputCost + outputCost;
            }

            // Update tokens display
            async function updateTokensDisplay() {
                try {
                    const response = await fetch('/api/tokens');
                    const tokensData = await response.json();

                    console.log('Tokens data received:', tokensData);  // Debug log

                    const currentStatusDisplay = document.getElementById('current-status-display');
                    const tokensHistoryDisplay = document.getElementById('tokens-history-display');

                    // Update Current Status
                    if (tokensData.current_task && tokensData.current_task.input_tokens > 0) {
                        console.log('Showing current status:', tokensData.current_task);  // Debug log
                        currentStatusDisplay.style.display = 'block';
                        document.getElementById('current-role').textContent = tokensData.current_task.role || '-';
                        document.getElementById('current-task-name').textContent = tokensData.current_task.task || '-';
                        document.getElementById('current-model').textContent = tokensData.current_task.model || '-';
                        document.getElementById('current-input-tokens').textContent = tokensData.current_task.input_tokens.toLocaleString();
                        document.getElementById('current-output-tokens').textContent = tokensData.current_task.output_tokens.toLocaleString();
                    } else {
                        currentStatusDisplay.style.display = 'none';
                    }

                    // Update Tokens History
                    if (tokensData.tasks_history && tokensData.tasks_history.length > 0) {
                        tokensHistoryDisplay.style.display = 'block';

                        const tbody = document.getElementById('tokens-history-body');
                        tbody.innerHTML = '';

                        // Group tasks by role+task to aggregate tokens
                        const taskGroups = {};
                        tokensData.tasks_history.forEach(task => {
                            const key = `${task.role}:${task.task}`;
                            if (!taskGroups[key]) {
                                taskGroups[key] = {
                                    role: task.role,
                                    task: task.task,
                                    model: task.model,
                                    input_tokens: 0,
                                    output_tokens: 0
                                };
                            }
                            taskGroups[key].input_tokens += task.input_tokens;
                            taskGroups[key].output_tokens += task.output_tokens;
                        });

                        // Populate table and calculate total cost
                        let totalCost = 0;
                        Object.values(taskGroups).forEach(task => {
                            const cost = calculateCost(task.model, task.input_tokens, task.output_tokens);
                            totalCost += cost;

                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${escapeHtml(task.role)}</td>
                                <td>${escapeHtml(task.task)}</td>
                                <td>${escapeHtml(task.model)}</td>
                                <td class="num">${task.input_tokens.toLocaleString()}</td>
                                <td class="num">${task.output_tokens.toLocaleString()}</td>
                                <td class="num">$${cost.toFixed(4)}</td>
                            `;
                            tbody.appendChild(row);
                        });

                        // Update totals
                        document.getElementById('total-input-tokens').textContent = tokensData.total_input_tokens.toLocaleString();
                        document.getElementById('total-output-tokens').textContent = tokensData.total_output_tokens.toLocaleString();
                        document.getElementById('total-cost').textContent = `$${totalCost.toFixed(4)}`;
                    } else {
                        tokensHistoryDisplay.style.display = 'none';
                    }
                } catch (error) {
                    console.error('Error updating tokens display:', error);
                }
            }

            // Initial load
            updateStatus();
            updateTokensDisplay();  // Initial tokens display
            setInterval(updateStatus, 5000);
            setInterval(updateTokensDisplay, 3000);  // Update tokens every 3 seconds
        </script>
    </body>
    </html>
    """)


def parse_jsonl_tokens_incremental(session_id: Optional[str] = None, offset: int = 0,
                                   existing_token_data: Optional[Dict] = None,
                                   version: str = "v0.4",
                                   workspace: Optional[str] = None) -> Dict:
    """
    Parse JSONL log file incrementally to extract new token usage.

    Args:
        session_id: Session ID to identify the JSONL file
        offset: Byte offset to start reading from (for incremental reading)
        existing_token_data: Previously accumulated token data to update
        version: Agent version (v0.4 or v0.5)
        workspace: Workspace/project name for locating logs

    Returns:
        Dict containing updated token data and new offset
    """
    import re

    # Initialize with existing data or defaults
    if existing_token_data:
        tokens_data = existing_token_data.copy()
        # Rebuild task_tokens dict from tasks_history for updates
        # Use timestamp in key to ensure uniqueness (for per-asset generation)
        task_tokens = {
            f"{t['role']}:{t['task']}:{t['call_id']}:{t.get('timestamp', '')}": t
            for t in tokens_data.get("tasks_history", [])
        }
    else:
        tokens_data = {
            "current_task": None,
            "tasks_history": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }
        task_tokens = {}

    tokens_data["new_offset"] = offset  # Default: no change

    if not session_id:
        print("[parse_jsonl_tokens] No session_id provided")
        return tokens_data

    if not workspace:
        print("[parse_jsonl_tokens] No workspace provided")
        return tokens_data

    # JSONL files are stored in workspace/{project_name}/logs/{session_id}.jsonl
    version_workspace_dir = get_workspace_dir(version)
    project_logs_dir = version_workspace_dir / workspace / "logs"
    jsonl_file = project_logs_dir / f"{session_id}.jsonl"

    if not jsonl_file.exists():
        print(f"[parse_jsonl_tokens] JSONL file not found: {jsonl_file}")
        return tokens_data

    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            # Seek to offset to read only new lines
            if offset > 0:
                f.seek(offset)

            # Read new lines only
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    if entry.get("category") == "model_call" and entry.get("event") == "response":
                        # Extract role and task from entry
                        role = entry.get("role", "unknown")
                        task = entry.get("task", "unknown")

                        metadata = entry.get("metadata", {})
                        response_full = metadata.get("response_full", [])

                        # Token info is in response_full[0].usage_metadata, NOT metadata.usage_metadata
                        usage_metadata = {}
                        model_name = "unknown"

                        if response_full and len(response_full) > 0:
                            resp = response_full[0]
                            usage_metadata = resp.get("usage_metadata", {})
                            resp_metadata = resp.get("response_metadata", {})
                            model_name = resp_metadata.get("model_name", "unknown")

                        if usage_metadata:
                            input_tokens = usage_metadata.get("input_tokens", 0)
                            output_tokens = usage_metadata.get("output_tokens", 0)

                            # Create unique key for this role+task+call_id+timestamp combination
                            # Note: timestamp is included to handle per-asset generation where
                            # multiple agents with same role/task/call_id are created
                            call_id = entry.get("call_id")
                            timestamp = entry.get("timestamp", "")
                            task_key = f"{role}:{task}:{call_id}:{timestamp}"

                            # Add task token data (each model call is recorded separately)
                            if task_key not in task_tokens:
                                task_tokens[task_key] = {
                                    "role": role,
                                    "task": task,
                                    "model": model_name,
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                    "call_id": call_id,
                                    "timestamp": timestamp
                                }
                                tokens_data["total_input_tokens"] += input_tokens
                                tokens_data["total_output_tokens"] += output_tokens
                            else:
                                # This should never happen with timestamp in key, but handle it safely
                                task_tokens[task_key]["input_tokens"] += input_tokens
                                task_tokens[task_key]["output_tokens"] += output_tokens
                                tokens_data["total_input_tokens"] += input_tokens
                                tokens_data["total_output_tokens"] += output_tokens

                except json.JSONDecodeError:
                    continue

            # Save current position for next incremental read
            tokens_data["new_offset"] = f.tell()

    except Exception as e:
        print(f"[parse_jsonl_tokens] Error parsing JSONL: {e}")

    # Convert to tasks history and sort by timestamp (chronological order)
    history_list = list(task_tokens.values())
    history_list.sort(key=lambda x: x.get('timestamp', ''))
    tokens_data["tasks_history"] = history_list

    # Set current task (last one chronologically)
    if history_list:
        tokens_data["current_task"] = history_list[-1]

    return tokens_data


@app.get("/api/status")
async def get_status():
    """Get current execution status"""
    state = load_state()

    # Check if process is still running
    if state["status"] == "running" and not check_process_running(state["pid"]):
        print(f"[get_status] Process {state['pid']} not running. Updating status to complete.")
        state["status"] = "complete"
        state["completed_workspace"] = state["workspace"]
        state["pid"] = None
        save_state(state)

    return state


@app.post("/api/start")
async def start_agent(request: Request):
    """Start a new agent execution"""
    state = load_state()

    # Check if already running
    if state["status"] == "running" and check_process_running(state["pid"]):
        raise HTTPException(status_code=400, detail="Agent is already running")

    # Parse request
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    project = data.get("project", "").strip()
    version = OSS_VERSION  # OSS version - always use single version
    model = data.get("model", "").strip()
    role_models = data.get("role_models", {})

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Use project name if provided, otherwise generate timestamp-based name
    if project:
        workspace = project
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace = f"game_{timestamp}"

    # Get version-specific directories
    version_dir = get_version_dir(version)
    version_workspace_dir = get_workspace_dir(version)
    version_logs_dir = version_workspace_dir / "webui_logs"

    # Ensure directories exist for this version
    version_workspace_dir.mkdir(parents=True, exist_ok=True)
    version_logs_dir.mkdir(parents=True, exist_ok=True)

    # Prepare log file in logs directory
    log_file = version_logs_dir / f"{workspace}.log"

    # Start agent in background with version-specific script
    cmd = [
        "python",
        str(version_dir / "gamestudio_1984.py"),
        prompt,
        "-p",
        workspace
    ]

    # Add default model parameter if specified
    if model:
        cmd.extend(["-m", model])

    # Add per-role model parameters if specified
    if role_models:
        if "designer" in role_models:
            cmd.extend(["--designer-model", role_models["designer"]])
        if "programmer" in role_models:
            cmd.extend(["--programmer-model", role_models["programmer"]])
        if "graphic_artist" in role_models:
            cmd.extend(["--graphic-artist-model", role_models["graphic_artist"]])
        if "sound_artist" in role_models:
            cmd.extend(["--sound-artist-model", role_models["sound_artist"]])
        if "tester" in role_models:
            cmd.extend(["--tester-model", role_models["tester"]])
        if "manager" in role_models:
            cmd.extend(["--manager-model", role_models["manager"]])

    with open(log_file, 'w') as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(version_dir)
        )

    # Update state
    state = {
        "status": "running",
        "pid": process.pid,
        "workspace": workspace,
        "version": version,  # Store version for later use
        "prompt": prompt,
        "start_time": datetime.now().isoformat(),
        "log_file": str(log_file),
        "session_id": None,  # Will be extracted from log later
        "jsonl_offset": 0,   # Start from beginning
        "token_data": {      # Reset token data for new session
            "current_task": None,
            "tasks_history": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }
    }
    save_state(state)

    return {"success": True, "workspace": workspace, "version": version, "pid": process.pid}


@app.post("/api/stop")
async def stop_agent():
    """Stop the running agent"""
    state = load_state()

    if state["status"] != "running" or not state["pid"]:
        raise HTTPException(status_code=400, detail="No agent is running")

    # Kill process
    try:
        os.kill(state["pid"], signal.SIGTERM)
        time.sleep(1)

        # Force kill if still running
        if check_process_running(state["pid"]):
            os.kill(state["pid"], signal.SIGKILL)
    except OSError:
        pass

    # Update state
    state["status"] = "idle"
    state["pid"] = None
    save_state(state)

    return {"success": True}


@app.post("/api/reset")
async def reset_agent():
    """Reset the agent state to idle for starting a new agent"""
    state = load_state()

    # Reset state to idle
    state["status"] = "idle"
    state["pid"] = None
    state["workspace"] = None
    state["prompt"] = None
    state["start_time"] = None
    state["log_file"] = None
    # Keep completed_workspace for reference if needed
    save_state(state)

    return {"success": True}


@app.get("/api/logs")
async def get_logs():
    """Get execution logs"""
    state = load_state()

    if not state.get("log_file"):
        return {"logs": [], "workspace": None}

    log_file = Path(state["log_file"])
    logs = []

    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()

    return {"logs": [line.rstrip() for line in logs], "workspace": state.get("workspace")}


@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    """Stream execution logs via SSE"""
    state = load_state()

    async def event_generator():
        last_position = 0
        last_check_time = time.time()

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Reload state to check if process is still running
            current_state = load_state()
            log_file_path = current_state.get("log_file")

            if not log_file_path:
                await asyncio.sleep(1)
                continue

            log_file = Path(log_file_path)
            if not log_file.exists():
                await asyncio.sleep(1)
                continue

            # Read new log lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()

            # Send new lines
            for line in new_lines:
                line = line.rstrip()
                if not line:
                    continue

                # Parse special content
                version = current_state.get("version", "v0.4")
                parsed_line = parse_log_line(line, current_state.get("workspace"), version)
                yield {
                    "event": "log",
                    "data": json.dumps(parsed_line)
                }

            # Check if process has finished
            if current_state["status"] == "running" and not check_process_running(current_state["pid"]):
                # Process finished
                print(f"[stream_logs] Process {current_state['pid']} finished. Updating status to complete.")
                current_state["status"] = "complete"
                current_state["completed_workspace"] = current_state["workspace"]
                current_state["pid"] = None
                save_state(current_state)

                # Send completion message with link
                workspace = current_state.get("workspace")
                if workspace:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "workspace": workspace,
                            "message": f"Agent execution completed. View game at: /game/{workspace}"
                        })
                    }
                break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


def parse_log_line(line: str, workspace: Optional[str], version: str = "v0.4") -> Dict:
    """Parse log line and detect special content (images, links, etc.)"""
    import re

    # Get version-specific workspace directory
    workspace_dir = get_workspace_dir(version)

    result = {
        "type": "text",
        "content": line
    }

    # Parse model call completion with usage metadata
    # Pattern: [2025-12-22 20:38:14] [LoggingMiddleware] 🤖 Model Call #1 (role: manager, task: generate_workflow) - COMPLETED in 1.06s
    model_call_pattern = r'\[LoggingMiddleware\] 🤖 Model Call #\d+ \(role: ([^,]+), task: ([^)]+)\) - COMPLETED'
    match = re.search(model_call_pattern, line)
    if match:
        role = match.group(1).strip()
        task = match.group(2).strip()
        result["role"] = role
        result["task"] = task

        # If tester role completes, trigger screenshot scan
        if role == "tester":
            result["type"] = "tester_complete"
            result["content"] = line

    # Detect test_result.json references and extract screenshots
    # Pattern: /work/test/NNN/test_result.json or similar
    if workspace and "test_result.json" in line:
        # Try to find test_result.json path
        test_result_patterns = [
            rf'/workspace/{re.escape(workspace)}/work/(test/\d{{3}}/test_result\.json)',
            rf'workspace/{re.escape(workspace)}/work/(test/\d{{3}}/test_result\.json)',
            r'work/(test/\d{3}/test_result\.json)',
            r'/work/(test/\d{3}/test_result\.json)',
        ]

        for pattern in test_result_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                test_result_rel_path = match.group(1)
                # Try to read test_result.json and extract screenshots
                test_result_path = workspace_dir / workspace / "work" / test_result_rel_path
                try:
                    if test_result_path.exists():
                        with open(test_result_path, 'r', encoding='utf-8') as f:
                            test_result = json.load(f)
                        # Extract screenshots from test_result.json
                        screenshots = test_result.get("script_results", {}).get("screenshots", [])
                        if not screenshots:
                            screenshots = test_result.get("screenshots", [])
                        if screenshots:
                            # Convert absolute paths to relative web paths
                            screenshot_paths = []
                            test_dir = test_result_rel_path.replace("test_result.json", "").rstrip('/')
                            for ss in screenshots:
                                # Extract just the filename
                                filename = Path(ss).name
                                screenshot_paths.append(f"/work/{workspace}/{test_dir}/{filename}")
                            result = {
                                "type": "test_screenshots",
                                "content": line,
                                "screenshots": screenshot_paths
                            }
                            print(f"[parse_log_line] Detected test_result.json with {len(screenshot_paths)} screenshots: {screenshot_paths}")
                            return result
                except Exception as e:
                    print(f"[parse_log_line] Error parsing test_result.json: {e}")
                    pass  # Fall through to normal text handling
                break

    # Detect screenshot paths from firefoxtester (work directory)
    # Patterns:
    #   - /path/to/workspace/xxx/work/test/NNN/01_title_screen.png
    #   - Screenshot saved: /path/to/work/test/002/01_title_screen.png
    if workspace and ("screenshot" in line.lower() or ".png" in line.lower()):
        # Pattern 1: work/test/NNN/ directory screenshots (from firefoxtester)
        work_png_patterns = [
            # Absolute path: /path/to/workspace/xxx/work/test/NNN/xxx.png
            rf'/workspace/{re.escape(workspace)}/work/(test/\d{{3}}/[^\s]+\.png)',
            # Relative path: workspace/xxx/work/test/NNN/xxx.png
            rf'workspace/{re.escape(workspace)}/work/(test/\d{{3}}/[^\s]+\.png)',
            # work/test/NNN/xxx.png pattern
            r'work/(test/\d{3}/[^\s]+\.png)',
            # Screenshot saved pattern with test subdirectory
            r'Screenshot saved:.*?/work/(test/\d{3}/[^\s]+\.png)',
            # Legacy: direct work directory (work/xxx.png)
            rf'/workspace/{re.escape(workspace)}/work/([^\s/]+\.png)',
            rf'workspace/{re.escape(workspace)}/work/([^\s/]+\.png)',
            r'work/(\d+_[^\s]+\.png)',
            rf'Screenshot saved:.*?/work/([^\s]+\.png)',
        ]

        for pattern in work_png_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                screenshot_path = match.group(1)
                result = {
                    "type": "image",
                    "content": line,
                    "image_path": f"/work/{workspace}/{screenshot_path}"
                }
                break

        # Pattern 2: public/screenshots directory (legacy)
        if result["type"] == "text":
            png_pattern = r'(workspace/[^/]+/public/screenshots/[^\s]+\.png)'
            match = re.search(png_pattern, line)
            if match:
                screenshot_path = match.group(1)
                rel_path = screenshot_path.replace(f"workspace/{workspace}/public/", "")
                result = {
                    "type": "image",
                    "content": line,
                    "image_path": f"/game/{workspace}/{rel_path}"
                }

    # Detect asset creation (images in assets folder)
    if workspace and "/assets/images/" in line and ".png" in line:
        # Pattern excludes glob wildcards (*, ?, [, ]) to avoid matching patterns like "*.png"
        asset_pattern = r'/assets/images/([a-zA-Z0-9_.-]+\.png)'
        match = re.search(asset_pattern, line)
        if match:
            asset_name = match.group(1)
            result = {
                "type": "asset_image",
                "content": line,
                "filename": asset_name,
                "image_path": f"/assets/{workspace}/images/{asset_name}"
            }

    # Detect sound creation
    if workspace and "/assets/sounds/" in line and ".wav" in line:
        # Pattern excludes glob wildcards (*, ?, [, ]) to avoid matching patterns like "*.wav"
        sound_pattern = r'/assets/sounds/([a-zA-Z0-9_.-]+\.wav)'
        match = re.search(sound_pattern, line)
        if match:
            sound_name = match.group(1)
            result = {
                "type": "asset_sound",
                "content": line,
                "filename": sound_name,
                "audio_path": f"/assets/{workspace}/sounds/{sound_name}"
            }

    return result


@app.get("/api/tokens")
async def get_tokens():
    """Get token usage information from logs (with incremental reading)"""
    state = load_state()

    # Check if process is still running and update status
    if state["status"] == "running" and not check_process_running(state["pid"]):
        state["status"] = "complete"
        state["completed_workspace"] = state["workspace"]
        state["pid"] = None
        save_state(state)

    # Return empty data if not running
    if state["status"] not in ["running", "complete"]:
        return {
            "current_task": None,
            "tasks_history": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }

    # Get or extract session_id
    session_id = state.get("session_id")
    if not session_id:
        # Try to extract from log file
        log_file = state.get("log_file")
        if log_file:
            log_path = Path(log_file)
            session_id = extract_session_id_from_log(log_path)
            if session_id:
                state["session_id"] = session_id
                save_state(state)
                print(f"[get_tokens] Extracted session_id: {session_id}")

    if not session_id:
        print("[get_tokens] No session_id available")
        return {
            "current_task": None,
            "tasks_history": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }

    # Get existing token data and offset
    existing_token_data = state.get("token_data", {})
    offset = state.get("jsonl_offset", 0)
    version = state.get("version", "v0.4")
    workspace = state.get("workspace") or state.get("completed_workspace")

    # Parse JSONL incrementally
    tokens_data = parse_jsonl_tokens_incremental(
        session_id=session_id,
        offset=offset,
        existing_token_data=existing_token_data,
        version=version,
        workspace=workspace
    )

    # Update state with new data and offset
    new_offset = tokens_data.pop("new_offset", offset)
    if new_offset != offset:
        state["jsonl_offset"] = new_offset
        state["token_data"] = tokens_data
        save_state(state)

        # Save token usage data as JSON file when data is updated
        if workspace and session_id:
            try:
                version_workspace_dir = get_workspace_dir(version)
                project_logs_dir = version_workspace_dir / workspace / "logs"
                tokens_json_file = project_logs_dir / f"{session_id}_tokens.json"

                # Ensure logs directory exists
                project_logs_dir.mkdir(parents=True, exist_ok=True)

                # Save token data to JSON file (overwrite completely)
                with open(tokens_json_file, 'w', encoding='utf-8') as f:
                    json.dump(tokens_data, f, indent=2, ensure_ascii=False)

                print(f"[get_tokens] Saved token usage to {tokens_json_file}")
            except Exception as e:
                print(f"[get_tokens] Error saving token usage JSON: {e}")

    return tokens_data


@app.get("/api/assets")
async def get_assets(workspace: str):
    """Get created assets for a workspace"""
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    workspace_path = workspace_dir / workspace / "public" / "assets"

    if not workspace_path.exists():
        return {"images": [], "sounds": []}

    images = []
    sounds = []

    # Find images
    images_path = workspace_path / "images"
    if images_path.exists():
        for img in images_path.glob("*.png"):
            images.append({
                "name": img.name,
                "path": f"images/{img.name}"
            })

    # Find sounds
    sounds_path = workspace_path / "sounds"
    if sounds_path.exists():
        for snd in sounds_path.glob("*.wav"):
            sounds.append({
                "name": snd.name,
                "path": f"sounds/{snd.name}"
            })

    return {"images": images, "sounds": sounds}


@app.get("/api/screenshots")
async def get_screenshots(workspace: str):
    """Scan and return all screenshots from test directories"""
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    work_test_path = workspace_dir / workspace / "work" / "test"

    screenshots = []

    if not work_test_path.exists():
        return {"screenshots": []}

    # Scan all test subdirectories (001, 002, etc.)
    for test_dir in sorted(work_test_path.iterdir()):
        if test_dir.is_dir():
            # Find all PNG files in this test directory
            for png_file in sorted(test_dir.glob("*.png")):
                screenshots.append({
                    "filename": png_file.name,
                    "path": f"/work/{workspace}/test/{test_dir.name}/{png_file.name}",
                    "test_dir": test_dir.name
                })

    return {"screenshots": screenshots}


@app.get("/api/asset-metadata/{workspace}/{filename}")
async def get_asset_metadata(workspace: str, filename: str):
    """Get metadata for an asset including background color from sprite JSON"""
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)

    # Remove .png extension if present
    base_name = filename.replace('.png', '')

    # Try to find sprite metadata JSON
    sprite_json_path = workspace_dir / workspace / "work" / "sprite" / f"{base_name}.json"

    if sprite_json_path.exists():
        try:
            with open(sprite_json_path, 'r', encoding='utf-8') as f:
                sprite_data = json.load(f)

            # Extract background color (first color in colors array)
            colors = sprite_data.get("colors", [])
            bg_color = colors[0] if colors else None

            # Convert "transparent" to actual transparent CSS value
            if bg_color == "transparent":
                bg_color = "transparent"

            return {
                "filename": filename,
                "background_color": bg_color,
                "colors": colors,
                "size": sprite_data.get("size", "unknown")
            }
        except Exception as e:
            print(f"Error reading sprite metadata: {e}")

    # Return default if no metadata found
    return {
        "filename": filename,
        "background_color": "#222222",  # Default dark gray
        "colors": [],
        "size": "unknown"
    }


@app.get("/api/workspaces")
async def list_workspaces(version: str = None):
    """List all available workspaces from v0.4, v0.5, v0.6, and v0.7"""
    workspaces = []
    seen_names = set()

    # System directories to exclude from workspace list
    excluded_dirs = {"agent_logs", "webui_logs"}

    # OSS version - single workspace directory
    versions_to_check = [OSS_VERSION]

    # Check version directories
    for ver in versions_to_check:
        workspace_dir = get_workspace_dir(ver)
        if not workspace_dir.exists():
            continue

        for ws in workspace_dir.iterdir():
            # Skip if not a directory, already seen, or in excluded list
            if not ws.is_dir():
                continue
            if ws.name in excluded_dirs:
                continue
            if ws.name in seen_names:
                continue

            seen_names.add(ws.name)
            stat = ws.stat()
            workspaces.append({
                "name": ws.name,
                "version": ver,
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            })

    # Sort by creation time descending
    workspaces.sort(key=lambda x: x["created"], reverse=True)
    return workspaces


@app.delete("/api/workspaces/{workspace}")
async def delete_workspace(workspace: str):
    """Delete a workspace directory"""
    import shutil

    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    workspace_path = workspace_dir / workspace

    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")

    if not workspace_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid workspace")

    try:
        shutil.rmtree(workspace_path)
        return {"success": True, "message": f"Workspace '{workspace}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {str(e)}")


@app.get("/api/workspaces/{workspace}/logs")
async def list_workspace_logs(workspace: str, version: str = None):
    """List all log files in a workspace's logs directory"""
    if not version:
        version = find_workspace_version(workspace)

    workspace_dir = get_workspace_dir(version)
    logs_dir = workspace_dir / workspace / "logs"

    if not logs_dir.exists():
        return []

    files = []
    for log_file in logs_dir.iterdir():
        if log_file.is_file():
            stat = log_file.stat()
            files.append({
                "name": log_file.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

    # Sort by modification time descending
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files


@app.get("/api/workspaces/{workspace}/logs/{filename}")
async def read_workspace_log(workspace: str, filename: str, version: str = None):
    """Read a specific log file from a workspace"""
    if not version:
        version = find_workspace_version(workspace)

    workspace_dir = get_workspace_dir(version)
    log_path = workspace_dir / workspace / "logs" / filename

    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    if not log_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid log file")

    # Security check: ensure the file is within the logs directory
    try:
        log_path.resolve().relative_to(workspace_dir / workspace / "logs")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        content = log_path.read_text(encoding='utf-8')
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")


@app.get("/assets/{workspace}/{asset_type}/{filename}")
async def serve_asset(workspace: str, asset_type: str, filename: str):
    """Serve asset files (images, sounds)"""
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    asset_path = workspace_dir / workspace / "public" / "assets" / asset_type / filename

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    return FileResponse(asset_path)


@app.get("/work/{workspace}/{path:path}")
async def serve_work_file(workspace: str, path: str):
    """Serve files from work directory (screenshots, test results, etc.)

    Supports subdirectories like /work/{workspace}/test/001/01_title_screen.png
    """
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    work_path = workspace_dir / workspace / "work" / path

    if not work_path.exists():
        raise HTTPException(status_code=404, detail="Work file not found")

    return FileResponse(work_path)


@app.get("/game/{workspace}/{path:path}")
async def serve_game_file(workspace: str, path: str):
    """Serve game files"""
    if not path:
        path = "index.html"

    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    file_path = workspace_dir / workspace / "public" / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/game/{workspace}")
async def serve_game_index(workspace: str):
    """Redirect to trailing slash for correct relative path resolution"""
    return RedirectResponse(url=f"/game/{workspace}/", status_code=301)


@app.get("/game/{workspace}/")
async def serve_game_index_with_slash(workspace: str):
    """Serve game index page"""
    version = find_workspace_version(workspace)
    workspace_dir = get_workspace_dir(version)
    index_path = workspace_dir / workspace / "public" / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Game not found")

    return FileResponse(index_path)


# ============================================================================
# File Viewer - Browse project_root files
# ============================================================================

@app.get("/api/files")
async def list_files(path: str = "", workspace: str = None, version: str = None):
    """List files and directories in project_root or workspace subdirectory"""
    import mimetypes

    # Security: ensure path is relative and doesn't go outside base directory
    if path and (path.startswith("/") or ".." in path):
        raise HTTPException(status_code=400, detail="Invalid path")

    # Determine base directory: workspace or project_root
    if workspace and version:
        workspace_dir = get_workspace_dir(version)
        base_dir = workspace_dir / workspace
        if not base_dir.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
    else:
        base_dir = BASE_DIR

    target_path = base_dir / path if path else base_dir

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    # Ensure target_path is within base_dir
    try:
        target_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    items = []
    for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        item_type = "directory" if item.is_dir() else "file"

        # Get file info
        stat = item.stat()
        file_info = {
            "name": item.name,
            "type": item_type,
            "path": str(item.relative_to(base_dir)),
            "size": stat.st_size if item_type == "file" else None,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add MIME type for files
        if item_type == "file":
            mime_type, _ = mimetypes.guess_type(item.name)
            file_info["mime_type"] = mime_type or "application/octet-stream"

            # Determine if file has thumbnail support
            if mime_type and mime_type.startswith("image/"):
                file_info["has_thumbnail"] = True
            else:
                file_info["has_thumbnail"] = False

        items.append(file_info)

    return {
        "path": path,
        "items": items
    }


@app.get("/api/file/content/{path:path}")
async def get_file_content(path: str, workspace: str = None, version: str = None):
    """Get file content for text files, image files, or other supported types"""
    import mimetypes

    # Security: ensure path is relative and doesn't go outside base directory
    if path.startswith("/") or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Determine base directory: workspace or project_root
    if workspace and version:
        workspace_dir = get_workspace_dir(version)
        base_dir = workspace_dir / workspace
        if not base_dir.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
    else:
        base_dir = BASE_DIR

    file_path = base_dir / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Ensure file_path is within base_dir
    try:
        file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    mime_type, _ = mimetypes.guess_type(file_path.name)

    # For images, audio, video - return the file directly
    if mime_type and (mime_type.startswith("image/") or
                      mime_type.startswith("audio/") or
                      mime_type.startswith("video/")):
        return FileResponse(file_path, media_type=mime_type)

    # For text files - return content as JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "path": path,
            "content": content,
            "mime_type": mime_type or "text/plain",
            "size": file_path.stat().st_size
        }
    except UnicodeDecodeError:
        # Binary file - return error
        raise HTTPException(status_code=400, detail="Cannot display binary file content")


@app.get("/api/file/thumbnail/{path:path}")
async def get_file_thumbnail(path: str, size: int = 200, workspace: str = None, version: str = None):
    """Generate thumbnail for image files"""
    from PIL import Image
    import io

    # Security: ensure path is relative and doesn't go outside base directory
    if path.startswith("/") or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Determine base directory: workspace or project_root
    if workspace and version:
        workspace_dir = get_workspace_dir(version)
        base_dir = workspace_dir / workspace
        if not base_dir.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
    else:
        base_dir = BASE_DIR

    file_path = base_dir / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Ensure file_path is within base_dir
    try:
        file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate size
    if size < 50 or size > 500:
        size = 200

    try:
        # Open and resize image
        with Image.open(file_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create thumbnail
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            # Save to bytes
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)

            from fastapi.responses import StreamingResponse
            return StreamingResponse(img_io, media_type="image/jpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnail: {str(e)}")


@app.get("/files")
async def file_viewer():
    """File viewer UI for browsing project_root"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Viewer - GameStudio 1984</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .header {
                background: #2c3e50;
                color: white;
                padding: 15px 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .header h1 {
                font-size: 20px;
                margin: 0;
            }
            .breadcrumb {
                background: #34495e;
                padding: 10px 20px;
                color: #ecf0f1;
                font-size: 14px;
            }
            .breadcrumb a {
                color: #3498db;
                text-decoration: none;
                cursor: pointer;
            }
            .breadcrumb a:hover {
                text-decoration: underline;
            }
            .breadcrumb span {
                margin: 0 5px;
            }
            .container {
                display: flex;
                flex: 1;
                overflow: hidden;
            }
            .file-list {
                width: 400px;
                background: white;
                border-right: 1px solid #ddd;
                overflow-y: auto;
            }
            .file-item {
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: background 0.2s;
            }
            .file-item:hover {
                background: #f8f9fa;
            }
            .file-item.active {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
            }
            .file-item.directory {
                font-weight: 600;
            }
            .file-thumbnail {
                width: 48px;
                height: 48px;
                border-radius: 4px;
                object-fit: cover;
                background: #ecf0f1;
            }
            .file-icon {
                width: 48px;
                height: 48px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #ecf0f1;
                border-radius: 4px;
                font-size: 24px;
            }
            .file-info {
                flex: 1;
                min-width: 0;
            }
            .file-name {
                font-size: 14px;
                color: #2c3e50;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .file-meta {
                font-size: 11px;
                color: #999;
                margin-top: 2px;
            }
            .content-viewer {
                flex: 1;
                background: white;
                overflow-y: auto;
                padding: 20px;
            }
            .no-selection {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: #999;
                font-size: 18px;
            }
            .text-content {
                background: #f8f9fa;
                padding: 16px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.6;
            }
            .image-content {
                text-align: center;
                position: relative;
                overflow: auto;
                max-height: calc(100vh - 200px);
            }
            .image-content img {
                max-width: 100%;
                height: auto;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: transform 0.2s;
                cursor: zoom-in;
            }
            .image-content img.zoomed {
                max-width: none;
                cursor: zoom-out;
            }
            .zoom-controls {
                position: sticky;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                display: inline-flex;
                gap: 10px;
                background: rgba(0, 0, 0, 0.7);
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 10px;
                z-index: 10;
            }
            .zoom-btn {
                background: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                transition: background 0.2s;
            }
            .zoom-btn:hover {
                background: #2980b9;
            }
            .zoom-btn:active {
                transform: scale(0.95);
            }
            .zoom-level {
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                display: flex;
                align-items: center;
            }
            .audio-content {
                padding: 20px;
            }
            .audio-content audio {
                width: 100%;
                margin-top: 10px;
            }
            .content-header {
                background: #ecf0f1;
                padding: 16px;
                margin: -20px -20px 20px -20px;
                border-bottom: 2px solid #bdc3c7;
            }
            .content-header h2 {
                font-size: 18px;
                color: #2c3e50;
                margin-bottom: 8px;
            }
            .content-meta {
                font-size: 13px;
                color: #666;
            }
            .log-viewer-link {
                display: inline-block;
                margin-top: 10px;
                padding: 10px 20px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
            }
            .log-viewer-link:hover {
                background: #2980b9;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1 id="header-title">📁 File Viewer</h1>
        </div>
        <div class="breadcrumb" id="breadcrumb">
            <a onclick="navigateTo('')">project_root</a>
        </div>
        <div class="container">
            <div class="file-list" id="fileList">
                <p style="padding: 16px; color: #999;">Loading...</p>
            </div>
            <div class="content-viewer" id="contentViewer">
                <div class="no-selection">Select a file or folder to view</div>
            </div>
        </div>
        <script>
            // Get URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const workspaceName = urlParams.get('workspace');
            const workspaceVersion = urlParams.get('version');

            let currentPath = '';
            let currentItems = [];

            function getFileIcon(item) {
                if (item.type === 'directory') return '📁';

                const ext = item.name.split('.').pop().toLowerCase();
                const iconMap = {
                    'py': '🐍',
                    'js': '📜',
                    'json': '📋',
                    'jsonl': '📊',
                    'md': '📝',
                    'txt': '📄',
                    'png': '🖼️',
                    'jpg': '🖼️',
                    'jpeg': '🖼️',
                    'gif': '🖼️',
                    'wav': '🎵',
                    'mp3': '🎵',
                    'html': '🌐',
                    'css': '🎨',
                };
                return iconMap[ext] || '📄';
            }

            function formatFileSize(bytes) {
                if (!bytes) return '';
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            }

            function updateBreadcrumb(path) {
                const breadcrumb = document.getElementById('breadcrumb');
                const parts = path ? path.split('/') : [];
                const rootName = workspaceName ? workspaceName : 'project_root';
                let html = `<a onclick="navigateTo('')">${rootName}</a>`;

                let accumulated = '';
                for (let i = 0; i < parts.length; i++) {
                    accumulated += (i > 0 ? '/' : '') + parts[i];
                    const currentAccumulated = accumulated;
                    html += ` <span>/</span> <a onclick="navigateTo('${currentAccumulated}')">${parts[i]}</a>`;
                }

                breadcrumb.innerHTML = html;
            }

            async function navigateTo(path) {
                currentPath = path;
                updateBreadcrumb(path);

                try {
                    let url = `/api/files?path=${encodeURIComponent(path)}`;
                    if (workspaceName && workspaceVersion) {
                        url += `&workspace=${encodeURIComponent(workspaceName)}&version=${encodeURIComponent(workspaceVersion)}`;
                    }
                    const response = await fetch(url);
                    const data = await response.json();
                    currentItems = data.items;
                    renderFileList(data.items);
                } catch (error) {
                    document.getElementById('fileList').innerHTML =
                        '<p style="padding: 16px; color: red;">Error loading files</p>';
                }
            }

            function renderFileList(items) {
                const fileList = document.getElementById('fileList');

                if (items.length === 0) {
                    fileList.innerHTML = '<p style="padding: 16px; color: #999;">Empty directory</p>';
                    return;
                }

                fileList.innerHTML = items.map((item, index) => {
                    const icon = getFileIcon(item);
                    const size = item.size ? formatFileSize(item.size) : '';

                    let thumbnailHtml = `<div class="file-icon">${icon}</div>`;
                    if (item.has_thumbnail) {
                        let thumbUrl = `/api/file/thumbnail/${encodeURIComponent(item.path)}`;
                        if (workspaceName && workspaceVersion) {
                            thumbUrl += `?workspace=${encodeURIComponent(workspaceName)}&version=${encodeURIComponent(workspaceVersion)}`;
                        }
                        thumbnailHtml = `<img class="file-thumbnail" src="${thumbUrl}" alt="${item.name}">`;
                    }

                    return `
                        <div class="file-item ${item.type}" onclick="selectItem(${index})">
                            ${thumbnailHtml}
                            <div class="file-info">
                                <div class="file-name">${item.name}</div>
                                <div class="file-meta">${size} ${item.modified}</div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            async function selectItem(index) {
                const item = currentItems[index];

                // Update active state
                document.querySelectorAll('.file-item').forEach((el, i) => {
                    if (i === index) {
                        el.classList.add('active');
                    } else {
                        el.classList.remove('active');
                    }
                });

                if (item.type === 'directory') {
                    navigateTo(item.path);
                    return;
                }

                // Display file content
                await displayFileContent(item);
            }

            async function displayFileContent(item) {
                const viewer = document.getElementById('contentViewer');

                // Check if it's a JSONL log file
                if (item.name.endsWith('.jsonl') && item.path.includes('logs/')) {
                    viewer.innerHTML = `
                        <div class="content-header">
                            <h2>${item.name}</h2>
                            <div class="content-meta">
                                Log file | ${formatFileSize(item.size)}
                            </div>
                        </div>
                        <div style="padding: 20px;">
                            <p>This is an agent log file in JSONL format.</p>
                            <a href="/api/workspaces/${getWorkspaceName(item.path)}/logs/${item.name}"
                               class="log-viewer-link" target="_blank">
                                Open in Log Viewer
                            </a>
                        </div>
                    `;
                    return;
                }

                // For images
                if (item.mime_type && item.mime_type.startsWith('image/')) {
                    let imgUrl = `/api/file/content/${encodeURIComponent(item.path)}`;
                    if (workspaceName && workspaceVersion) {
                        imgUrl += `?workspace=${encodeURIComponent(workspaceName)}&version=${encodeURIComponent(workspaceVersion)}`;
                    }
                    viewer.innerHTML = `
                        <div class="content-header">
                            <h2>${item.name}</h2>
                            <div class="content-meta">
                                ${item.mime_type} | ${formatFileSize(item.size)}
                            </div>
                        </div>
                        <div class="image-content" id="imageContent">
                            <div class="zoom-controls">
                                <button class="zoom-btn" onclick="zoomOut()">-</button>
                                <span class="zoom-level" id="zoomLevel">100%</span>
                                <button class="zoom-btn" onclick="zoomIn()">+</button>
                                <button class="zoom-btn" onclick="resetZoom()">Reset</button>
                            </div>
                            <img id="zoomableImage" src="${imgUrl}" alt="${item.name}">
                        </div>
                    `;
                    return;
                }

                // For audio
                if (item.mime_type && item.mime_type.startsWith('audio/')) {
                    let audioUrl = `/api/file/content/${encodeURIComponent(item.path)}`;
                    if (workspaceName && workspaceVersion) {
                        audioUrl += `?workspace=${encodeURIComponent(workspaceName)}&version=${encodeURIComponent(workspaceVersion)}`;
                    }
                    viewer.innerHTML = `
                        <div class="content-header">
                            <h2>${item.name}</h2>
                            <div class="content-meta">
                                ${item.mime_type} | ${formatFileSize(item.size)}
                            </div>
                        </div>
                        <div class="audio-content">
                            <audio controls>
                                <source src="${audioUrl}" type="${item.mime_type}">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    `;
                    return;
                }

                // For text files
                try {
                    let contentUrl = `/api/file/content/${encodeURIComponent(item.path)}`;
                    if (workspaceName && workspaceVersion) {
                        contentUrl += `?workspace=${encodeURIComponent(workspaceName)}&version=${encodeURIComponent(workspaceVersion)}`;
                    }
                    const response = await fetch(contentUrl);
                    const data = await response.json();

                    viewer.innerHTML = `
                        <div class="content-header">
                            <h2>${item.name}</h2>
                            <div class="content-meta">
                                ${data.mime_type} | ${formatFileSize(data.size)}
                            </div>
                        </div>
                        <div class="text-content">${escapeHtml(data.content)}</div>
                    `;
                } catch (error) {
                    viewer.innerHTML = `
                        <div class="content-header">
                            <h2>${item.name}</h2>
                        </div>
                        <div style="padding: 20px; color: red;">
                            Cannot display this file type
                        </div>
                    `;
                }
            }

            function getWorkspaceName(path) {
                // Extract workspace name from path like "v0.4/workspace/my_game/logs/..."
                const parts = path.split('/');
                const workspaceIndex = parts.indexOf('workspace');
                if (workspaceIndex >= 0 && workspaceIndex + 1 < parts.length) {
                    return parts[workspaceIndex + 1];
                }
                return '';
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // Zoom functionality
            let currentZoom = 100;

            function updateZoom(newZoom) {
                currentZoom = newZoom;
                const img = document.getElementById('zoomableImage');
                const zoomLevel = document.getElementById('zoomLevel');

                if (img && zoomLevel) {
                    img.style.transform = `scale(${currentZoom / 100})`;
                    zoomLevel.textContent = `${currentZoom}%`;

                    // Add/remove zoomed class for cursor change
                    if (currentZoom > 100) {
                        img.classList.add('zoomed');
                    } else {
                        img.classList.remove('zoomed');
                    }
                }
            }

            function zoomIn() {
                const newZoom = Math.min(currentZoom + 25, 500);
                updateZoom(newZoom);
            }

            function zoomOut() {
                const newZoom = Math.max(currentZoom - 25, 25);
                updateZoom(newZoom);
            }

            function resetZoom() {
                updateZoom(100);
            }

            // Initialize
            // Update header title if viewing workspace
            if (workspaceName) {
                document.getElementById('header-title').textContent = `📁 File Viewer - ${workspaceName}`;
            }
            navigateTo('');
        </script>
    </body>
    </html>
    """)


@app.get("/api/workspace/files/{file_path:path}")
async def get_workspace_file(file_path: str):
    """Serve workspace asset files"""
    full_path = BASE_DIR / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security check: ensure the path is within the BASE_DIR
    try:
        full_path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(full_path)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8089)
