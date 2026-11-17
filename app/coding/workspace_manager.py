"""
Workspace Manager for RoboBuddy.
Creates and manages dedicated experiment directories, starter files, and metadata.
Ensures existing student work is never overwritten.
"""

import json
import re
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
EXPERIMENTS_DIR = BASE_DIR / "experiments"


class WorkspaceManager:
    def __init__(self, base_dir: Path = EXPERIMENTS_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Convert a title or course name into a safe folder name."""
        clean = re.sub(r"[^\w\s-]", "", str(name).strip())
        return re.sub(r"[-\s]+", "_", clean)

    def get_experiment_folder_name(self, experiment: dict) -> str:
        number = experiment.get("number", 1)
        title = experiment.get("title", f"Experiment_{number}")
        num_str = f"Experiment_{int(number):02d}" if isinstance(number, (int, str)) and str(number).isdigit() else f"Experiment_{number}"
        sanitized_title = self.sanitize_name(title)
        return f"{num_str}_{sanitized_title}"

    def create_experiment_workspace(self, course: dict, experiment: dict) -> Path:
        """
        Creates a dedicated workspace directory for an experiment.
        Never overwrites an existing main.py file.
        """
        course_name = self.sanitize_name(course.get("name", "General"))
        folder_name = self.get_experiment_folder_name(experiment)

        workspace_path = self.base_dir / course_name / folder_name
        workspace_path.mkdir(parents=True, exist_ok=True)

        main_py = workspace_path / "main.py"
        info_json = workspace_path / "experiment_info.json"

        # Write experiment metadata
        metadata = {
            "course": course.get("name", "General"),
            "experiment_number": experiment.get("number", 1),
            "title": experiment.get("title", "Untitled Experiment"),
            "objective": experiment.get("description", ""),
            "key_concepts": experiment.get("concepts", ""),
            "workspace_path": str(workspace_path),
            "created_at": datetime.now().isoformat(),
        }
        info_json.write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")

        # Create starter main.py ONLY if it does not already exist
        if not main_py.exists():
            starter_content = (
                f'"""\n'
                f'Experiment {experiment.get("number", 1)}: {experiment.get("title", "")}\n'
                f'Course: {course.get("name", "")}\n\n'
                f'Objective: {experiment.get("description", "")}\n'
                f'Key Concepts: {experiment.get("concepts", "")}\n'
                f'"""\n\n'
                f"# RoboBuddy is monitoring your workspace.\n"
                f"# Write your code below and save the file (Ctrl + S).\n\n"
            )
            main_py.write_text(starter_content, encoding="utf-8")
            print(f"[WORKSPACE] Created starter file: {main_py}", flush=True)
        else:
            print(f"[WORKSPACE] Existing experiment file preserved: {main_py}", flush=True)

        return workspace_path
