"""
Workflow Engine for GameStudio 1984 v0.4

Executes workflow with asset-first validation.
"""

import os
import json
import shutil
from typing import Dict, List, Any
from datetime import datetime


class WorkflowEngine:
    """Execute workflow with asset-first validation."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.workflow = None
        self.task_results = {}

    def load_workflow(self, workflow_path: str) -> bool:
        """Load workflow from JSON file."""
        try:
            full_path = os.path.join(self.project_root, workflow_path.lstrip("/"))
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.workflow = data.get("workflow")

            # Restore task_results for completed tasks (supports resume)
            self._restore_task_results()

            return True
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return False

    def validate_workflow_order(self) -> List[str]:
        """
        Ensure assets created before programmer tasks.

        Returns:
            List of error messages (empty if valid)
        """
        if not self.workflow:
            return ["No workflow loaded"]

        errors = []

        asset_tasks = {"generate_sprites", "generate_sounds"}
        # Code tasks that require assets to exist first
        code_tasks_needing_assets = {"implement_game"}
        # Code tasks that can run without asset creation (continuous development)
        code_tasks_no_assets = {"fix_bugs", "fix_error", "improve_game"}

        asset_phase_indices = []
        code_phase_indices = []

        for i, phase in enumerate(self.workflow.get("phases", [])):
            for task in phase.get("tasks", []):
                task_name = task.get("task")
                if task_name in asset_tasks:
                    asset_phase_indices.append(i)
                elif task_name in code_tasks_needing_assets:
                    code_phase_indices.append(i)
                # Note: code_tasks_no_assets are allowed to run without asset creation

        # Check asset-first rule (only for tasks that need assets)
        if code_phase_indices and asset_phase_indices:
            if min(code_phase_indices) < max(asset_phase_indices):
                errors.append(
                    "ERROR: Code tasks must come AFTER all asset tasks. "
                    "Asset-first rule violated!"
                )

        return errors

    def get_next_task(self) -> Dict[str, Any]:
        """
        Get next pending task that has all dependencies satisfied.

        Returns:
            Task dict or None if no task available
        """
        if not self.workflow:
            return None

        for phase in self.workflow.get("phases", []):
            for task in phase.get("tasks", []):
                task_id = task.get("id")
                status = task.get("status", "pending")

                # Skip completed or in-progress tasks
                if status != "pending":
                    continue

                # Check dependencies
                dependencies = task.get("dependencies", [])
                all_deps_met = all(
                    self.task_results.get(dep_id, {}).get("status") == "completed"
                    for dep_id in dependencies
                )

                if all_deps_met:
                    return task

        return None

    def update_task_status(self, task_id: str, status: str, result: Any = None):
        """Update task status and result."""
        self.task_results[task_id] = {
            "status": status,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

        # Update workflow JSON
        if self.workflow:
            for phase in self.workflow.get("phases", []):
                for task in phase.get("tasks", []):
                    if task.get("id") == task_id:
                        task["status"] = status
                        break

    def is_workflow_complete(self) -> bool:
        """Check if all tasks are completed."""
        if not self.workflow:
            return False

        for phase in self.workflow.get("phases", []):
            for task in phase.get("tasks", []):
                if task.get("status", "pending") != "completed":
                    return False

        return True

    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of workflow progress."""
        if not self.workflow:
            return {"error": "No workflow loaded"}

        total_tasks = 0
        completed_tasks = 0
        pending_tasks = 0
        in_progress_tasks = 0

        for phase in self.workflow.get("phases", []):
            for task in phase.get("tasks", []):
                total_tasks += 1
                status = task.get("status", "pending")
                if status == "completed":
                    completed_tasks += 1
                elif status == "in_progress":
                    in_progress_tasks += 1
                else:
                    pending_tasks += 1

        return {
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "pending": pending_tasks,
            "complete": completed_tasks == total_tasks
        }

    def _restore_task_results(self):
        """
        Restore task_results from workflow JSON for completed/in-progress tasks.

        This is essential for workflow resume functionality.
        When a workflow is resumed, we need to populate task_results
        with the status of already completed tasks so that dependency
        checks work correctly.
        """
        if not self.workflow:
            return

        for phase in self.workflow.get("phases", []):
            for task in phase.get("tasks", []):
                task_id = task.get("id")
                status = task.get("status", "pending")

                # Restore completed or in-progress tasks
                if status in ["completed", "in_progress"]:
                    self.task_results[task_id] = {
                        "status": status,
                        "result": task.get("result"),  # May be None
                        "timestamp": task.get("timestamp", datetime.now().isoformat())
                    }

    def save_workflow(self, workflow_path: str) -> bool:
        """Save workflow to JSON file."""
        try:
            full_path = os.path.join(self.project_root, workflow_path.lstrip("/"))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump({"workflow": self.workflow}, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving workflow: {e}")
            return False

    def add_fix_phase(self, after_task_id: str, max_iterations: int = 3) -> bool:
        """
        Add a fix phase to the workflow after a failed test.

        Args:
            after_task_id: Task ID to insert fix phase after
            max_iterations: Maximum number of fix iterations to add

        Returns:
            True if fix phase added successfully, False otherwise
        """
        if not self.workflow:
            return False

        # Find the test task and its phase
        test_phase_idx = None
        test_task_idx = None

        for phase_idx, phase in enumerate(self.workflow.get("phases", [])):
            for task_idx, task in enumerate(phase.get("tasks", [])):
                if task.get("id") == after_task_id:
                    test_phase_idx = phase_idx
                    test_task_idx = task_idx
                    break
            if test_phase_idx is not None:
                break

        if test_phase_idx is None:
            return False

        # Generate unique task IDs
        existing_ids = set()
        for phase in self.workflow.get("phases", []):
            for task in phase.get("tasks", []):
                existing_ids.add(task.get("id"))

        # Find next available task ID number
        task_num = 1
        while f"task_{task_num}" in existing_ids:
            task_num += 1

        fix_task_id = f"task_{task_num}"
        retest_task_id = f"task_{task_num + 1}"

        # Create fix phase
        fix_phase = {
            "id": f"phase_fix_{task_num}",
            "name": "Bug Fix Phase",
            "description": "Fix issues found during testing",
            "tasks": [
                {
                    "id": fix_task_id,
                    "agent": "Programmer",
                    "task": "fix_bugs",
                    "description": "Fix bugs identified in test report",
                    "output": "/public/game.js",
                    "dependencies": [after_task_id],
                    "status": "pending"
                },
                {
                    "id": retest_task_id,
                    "agent": "Tester",
                    "task": "test_game",
                    "description": "Re-test game after bug fixes",
                    "output": "/work/test_report.json",
                    "dependencies": [fix_task_id],
                    "status": "pending"
                }
            ]
        }

        # Insert fix phase after test phase
        self.workflow["phases"].insert(test_phase_idx + 1, fix_phase)

        return True

    def get_last_completed_test_task(self) -> Dict[str, Any]:
        """
        Get the most recently completed test task.

        Returns:
            Task dict or None if no test task found
        """
        if not self.workflow:
            return None

        # Iterate in reverse to find most recent test task
        for phase in reversed(self.workflow.get("phases", [])):
            for task in reversed(phase.get("tasks", [])):
                if task.get("task") == "test_game" and task.get("status") == "completed":
                    return task

        return None

    def setup_workspace(self, template_dir: str = "templates/game_template_advanced") -> Dict[str, Any]:
        """
        Setup workspace with template files.

        Copies template files (index.html, style.css, gamelib.js) to /public/
        only if they don't already exist (supports continuous development).

        Args:
            template_dir: Path to template directory (relative to project root)

        Returns:
            Dict with setup results: {copied: [], skipped: [], errors: []}
        """
        result = {
            "copied": [],
            "skipped": [],
            "errors": []
        }

        # Files to copy (these should not be modified by agents)
        template_files = [
            "index.html",
            "style.css",
            "gamelib.js"
        ]

        # Ensure /public/ directory exists
        public_dir = os.path.join(self.project_root, "public")
        os.makedirs(public_dir, exist_ok=True)

        # Ensure /public/assets/ directories exist
        os.makedirs(os.path.join(public_dir, "assets", "images"), exist_ok=True)
        os.makedirs(os.path.join(public_dir, "assets", "sounds"), exist_ok=True)

        # Copy template files if they don't exist
        template_path = os.path.join(self.project_root, template_dir)

        for filename in template_files:
            src = os.path.join(template_path, filename)
            dst = os.path.join(public_dir, filename)

            try:
                if os.path.exists(dst):
                    result["skipped"].append(filename)
                elif os.path.exists(src):
                    shutil.copy2(src, dst)
                    result["copied"].append(filename)
                else:
                    result["errors"].append(f"{filename}: template not found")
            except Exception as e:
                result["errors"].append(f"{filename}: {str(e)}")

        return result
