"""
Code Monitor for RoboBuddy.
Monitors the active experiment directory in a background QThread.
Implements debouncing (quiet period) to avoid keystroke spam.
Detects stable Python file edits, additions, and deletions.
"""

import os
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class CodeMonitor(QThread):
    code_changed = Signal(str, str, str, int)  # file_path, full_content, changed_line, line_number
    file_created = Signal(str)
    file_deleted = Signal(str)
    analysis_started = Signal(str)

    def __init__(self, workspace_path: Path, debounce_seconds: float = 2.5, parent=None):
        super().__init__(parent)
        self.workspace_path = Path(workspace_path)
        self.debounce_seconds = debounce_seconds
        self.running = True

        # Track file snapshots: {path: (mtime, [lines])}
        self.snapshots = {}
        self.pending_change_time = None
        self.pending_file = None
        self.last_analyzed_content = {}

        self._take_initial_snapshot()

    def _take_initial_snapshot(self):
        if not self.workspace_path.exists():
            return
        for file_path in self.workspace_path.glob("*.py"):
            try:
                mtime = file_path.stat().st_mtime
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                self.snapshots[str(file_path)] = (mtime, content.splitlines())
                self.last_analyzed_content[str(file_path)] = content
            except Exception:
                pass

    def stop(self):
        self.running = False

    def run(self):
        print(f"[MONITOR] Started monitoring workspace: {self.workspace_path}", flush=True)

        while self.running:
            try:
                if not self.workspace_path.exists():
                    time.sleep(0.5)
                    continue

                current_files = set(str(p) for p in self.workspace_path.glob("*.py"))
                known_files = set(self.snapshots.keys())

                # 1. Check for newly created files
                for new_file in current_files - known_files:
                    p = Path(new_file)
                    try:
                        mtime = p.stat().st_mtime
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        self.snapshots[new_file] = (mtime, content.splitlines())
                        self.last_analyzed_content[new_file] = content
                        self.file_created.emit(new_file)
                    except Exception:
                        pass

                # 2. Check for deleted files
                for deleted_file in known_files - current_files:
                    self.snapshots.pop(deleted_file, None)
                    self.last_analyzed_content.pop(deleted_file, None)
                    self.file_deleted.emit(deleted_file)

                # 3. Check for modified files
                for f_path in current_files:
                    p = Path(f_path)
                    try:
                        mtime = p.stat().st_mtime
                        last_mtime, last_lines = self.snapshots.get(f_path, (0, []))

                        if mtime > last_mtime:
                            # File changed on disk! Reset debounce timer
                            self.snapshots[f_path] = (mtime, last_lines)
                            self.pending_change_time = time.time()
                            self.pending_file = f_path
                    except Exception:
                        pass

                # 4. Handle Debounce: Has file settled for debounce_seconds?
                if self.pending_file and self.pending_change_time:
                    elapsed = time.time() - self.pending_change_time
                    if elapsed >= self.debounce_seconds:
                        target = self.pending_file
                        self.pending_file = None
                        self.pending_change_time = None
                        self._process_stable_file(target)

            except Exception as e:
                print(f"[MONITOR] Error in monitor loop: {e}", flush=True)

            time.sleep(0.4)

    def _process_stable_file(self, file_path_str: str):
        p = Path(file_path_str)
        if not p.exists():
            return
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            # Avoid re-analyzing if content is strictly identical to last analysis
            if content == self.last_analyzed_content.get(file_path_str):
                return

            self.last_analyzed_content[file_path_str] = content
            new_lines = content.splitlines()
            old_lines = self.snapshots.get(file_path_str, (0, []))[1]

            # Detect which line changed
            changed_line = ""
            changed_lineno = 1

            for i in range(max(len(new_lines), len(old_lines))):
                new_l = new_lines[i] if i < len(new_lines) else ""
                old_l = old_lines[i] if i < len(old_lines) else ""
                if new_l != old_l and new_l.strip():
                    changed_line = new_l
                    changed_lineno = i + 1
                    break

            if not changed_line and new_lines:
                changed_line = new_lines[-1]
                changed_lineno = len(new_lines)

            # Update snapshot
            mtime = p.stat().st_mtime
            self.snapshots[file_path_str] = (mtime, new_lines)

            self.analysis_started.emit(file_path_str)
            self.code_changed.emit(file_path_str, content, changed_line, changed_lineno)

        except Exception as e:
            print(f"[MONITOR] Failed to read {file_path_str}: {e}", flush=True)
