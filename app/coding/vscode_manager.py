"""
VS Code Manager for RoboBuddy.
Safely opens experiment workspaces in VS Code and integrated terminal using argument lists.
"""

import os
import shutil
import subprocess
from pathlib import Path


class VSCodeManager:
    @staticmethod
    def is_vscode_installed() -> bool:
        """Check if 'code' command is available on PATH."""
        return shutil.which("code") is not None

    @staticmethod
    def open_workspace(workspace_path: Path, open_file: str = "main.py") -> bool:
        """
        Open the workspace directory in VS Code safely using subprocess argument lists.
        """
        path_str = str(Path(workspace_path).resolve())
        target_file = Path(workspace_path) / open_file

        if VSCodeManager.is_vscode_installed():
            try:
                # Open the workspace directory
                subprocess.Popen(["code", path_str], shell=False)

                # Open the target starter file if it exists
                if target_file.exists():
                    subprocess.Popen(["code", str(target_file.resolve())], shell=False)

                print(f"[VSCODE] Opened workspace in VS Code: {path_str}", flush=True)
                return True
            except Exception as e:
                print(f"[VSCODE] Error launching VS Code: {e}", flush=True)

        # Fallback for Windows if 'code' CLI is not on PATH:
        # Try default system open or PowerShell in the directory
        try:
            if os.name == "nt":
                # Open directory in File Explorer
                os.startfile(path_str)
                # Open PowerShell in that directory
                subprocess.Popen(
                    ["powershell.exe", "-NoExit", "-Command", f"Set-Location '{path_str}'"],
                    shell=False,
                )
                print(f"[VSCODE] Opened directory and PowerShell in {path_str}", flush=True)
                return True
        except Exception as e:
            print(f"[VSCODE] Fallback open failed: {e}", flush=True)

        return False
