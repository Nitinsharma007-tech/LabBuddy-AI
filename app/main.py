import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.ui.dashboard import LabBuddyDashboard


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LabBuddy AI")
    app.setFont(QFont("Cambria", 10))

    window = LabBuddyDashboard()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()