
import sys
import signal
import traceback

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.ui.robot_window import RobotWindow
from app.core.robot_controller import RobotController


def main():

    app = QApplication(sys.argv)
    app.setApplicationName("LabBuddy AI")
    app.setFont(QFont("Segoe UI", 10))

    # Allow Ctrl+C to request a clean application shutdown.
    app.setQuitOnLastWindowClosed(True)

    robot = RobotWindow()
    controller = RobotController(robot)

    app.robot = robot
    app.controller = controller

    robot.show()

    def handle_sigint(*args):
        print("\nStopping LabBuddy...", flush=True)
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    # Check for Ctrl+C periodically.
    from PySide6.QtCore import QTimer

    interrupt_timer = QTimer()
    interrupt_timer.timeout.connect(lambda: None)
    interrupt_timer.start(200)

    sys.exit(app.exec())


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("LabBuddy stopped.")

    except Exception:
        traceback.print_exc()
