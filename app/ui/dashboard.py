from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QInputDialog, QMessageBox,
    QScrollArea, QGridLayout, QSizePolicy
)
import json
import re
from app.ui.experiment_page import ExperimentPage
import shutil
import re
import json

from PySide6.QtWidgets import QInputDialog, QMessageBox
from app.ui.course_details import CourseDetailsDialog

from app.syllabus.parser import extract_text
from app.syllabus.experiment_extractor import extract_experiments


BASE_DIR = Path(__file__).resolve().parents[2]
SUPPORTED_FILES = (".pdf", ".docx", ".txt")


STYLESHEET = """
QMainWindow, QWidget#centralWidget {
    background-color: #0b1020;
    color: #e8ecf8;
    font-family: 'Segoe UI';
}
QFrame#sidebar {
    background-color: #10182b;
    border-right: 1px solid #202b43;
}
QLabel#brand {
    color: #ffffff;
    font-size: 23px;
    font-weight: 700;
}
QLabel#brandAccent {
    color: #8b9cff;
    font-size: 23px;
    font-weight: 700;
}
QLabel#muted {
    color: #8995b0;
    font-size: 12px;
}
QLabel#pageTitle {
    color: #f4f6ff;
    font-size: 27px;
    font-weight: 700;
}
QLabel#sectionTitle {
    color: #f4f6ff;
    font-size: 17px;
    font-weight: 650;
}
QFrame#hero {
    background-color: #172344;
    border: 1px solid #2b3b68;
    border-radius: 18px;
}
QLabel#heroTitle {
    color: #ffffff;
    font-size: 25px;
    font-weight: 700;
}
QLabel#heroText {
    color: #c1cbed;
    font-size: 13px;
}
QFrame#statCard, QFrame#courseCard {
    background-color: #111a2e;
    border: 1px solid #202d48;
    border-radius: 14px;
}
QLabel#statNumber {
    color: #ffffff;
    font-size: 25px;
    font-weight: 700;
}
QLabel#courseName {
    color: #f3f5ff;
    font-size: 16px;
    font-weight: 650;
}
QPushButton {
    background-color: #202d49;
    color: #e9edff;
    border: 1px solid #344363;
    border-radius: 9px;
    padding: 10px 15px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2a3b60;
}
QPushButton#primaryButton {
    background-color: #687cf5;
    color: white;
    border: none;
    padding: 12px 18px;
}
QPushButton#primaryButton:hover {
    background-color: #7d8eff;
}
QPushButton#navButton {
    text-align: left;
    background-color: transparent;
    border: none;
    color: #aab5ce;
    padding: 12px;
    font-size: 13px;
}
QPushButton#navButton:hover, QPushButton#navActive {
    background-color: #202d49;
    color: white;
    border-radius: 9px;
    text-align: left;
    padding: 12px;
    font-size: 13px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #0b1020;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #344363;
    border-radius: 4px;
}
"""


class CourseCard(QFrame):
    view_requested = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, course, parent=None):
        super().__init__(parent)

        self.course = course
        self.setObjectName("courseCard")
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        icon = QLabel("📘")
        icon.setStyleSheet("font-size:25px;")
        layout.addWidget(icon)

        name = QLabel(course["name"])
        name.setObjectName("courseName")
        name.setWordWrap(True)
        layout.addWidget(name)

        filename = QLabel(course["filename"])
        filename.setObjectName("muted")
        filename.setWordWrap(True)
        layout.addWidget(filename)

        count = QLabel(
            f"{len(course.get('experiments', []))} experiments identified"
        )
        count.setObjectName("muted")
        layout.addWidget(count)

        layout.addStretch()

        buttons = QHBoxLayout()

        view = QPushButton("View Details")
        view.setObjectName("primaryButton")
        view.clicked.connect(
            lambda: self.view_requested.emit(self.course)
        )

        edit = QPushButton("Edit")
        edit.clicked.connect(
            lambda: self.edit_requested.emit(self.course)
        )

        delete = QPushButton("Delete")
        delete.setStyleSheet(
            "background:#47232d; border:1px solid #75404b;"
        )
        delete.clicked.connect(
            lambda: self.delete_requested.emit(self.course)
        )

        buttons.addWidget(view)
        buttons.addWidget(edit)
        buttons.addWidget(delete)

        layout.addLayout(buttons)


class LabBuddyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBuddy AI")
        self.resize(1200, 780)
        self.setMinimumSize(950, 650)

        self.courses = []
        self.load_courses()

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self.create_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 25, 32, 24)
        content_layout.setSpacing(20)

        content_layout.addWidget(self.create_header())
        content_layout.addWidget(self.create_hero())
        content_layout.addLayout(self.create_stats())
        content_layout.addLayout(self.create_courses_header())

        self.course_area = QScrollArea()
        self.course_area.setWidgetResizable(True)

        self.course_container = QWidget()
        self.course_grid = QGridLayout(self.course_container)
        self.course_grid.setContentsMargins(0, 5, 5, 5)
        self.course_grid.setHorizontalSpacing(16)
        self.course_grid.setVerticalSpacing(16)

        self.course_area.setWidget(self.course_container)
        content_layout.addWidget(self.course_area, 1)

        root.addWidget(content, 1)

        self.setStyleSheet(STYLESHEET)
        self.refresh_courses()
    def load_courses(self):
        workspace_root = BASE_DIR / "course_workspaces"

        workspace_root.mkdir(parents=True, exist_ok=True)

        self.courses = []

        for metadata_file in workspace_root.glob("*/course.json"):
            try:
                with metadata_file.open("r", encoding="utf-8") as file:
                    course = json.load(file)

                course["workspace"] = str(metadata_file.parent)
                self.courses.append(course)

            except (OSError, json.JSONDecodeError) as error:
                print(f"Could not load {metadata_file}: {error}")

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 25, 18, 20)
        layout.setSpacing(12)

        brand_row = QHBoxLayout()
        brand = QLabel("Lab")
        brand.setObjectName("brand")
        accent = QLabel("Buddy")
        accent.setObjectName("brandAccent")
        brand_row.addWidget(brand)
        brand_row.addWidget(accent)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        tagline = QLabel("YOUR AI LAB PARTNER")
        tagline.setObjectName("muted")
        layout.addWidget(tagline)

        layout.addSpacing(30)

        nav_title = QLabel("WORKSPACE")
        nav_title.setObjectName("muted")
        layout.addWidget(nav_title)

        dashboard_button = QPushButton("⌂    Dashboard")
        dashboard_button.setObjectName("navActive")
        layout.addWidget(dashboard_button)

        courses_button = QPushButton("▤    My Courses")
        courses_button.setObjectName("navButton")
        courses_button.clicked.connect(
            lambda: self.course_area.ensureVisible(0, 0)
        )
        layout.addWidget(courses_button)

        upload_button = QPushButton("＋    Upload Syllabus")
        upload_button.setObjectName("navButton")
        upload_button.clicked.connect(self.add_course)
        layout.addWidget(upload_button)

        layout.addStretch()

        assistant_card = QFrame()
        assistant_card.setStyleSheet(
            "background:#182440; border:1px solid #2c3c60;"
            "border-radius:13px;"
        )
        assistant_layout = QVBoxLayout(assistant_card)

        assistant_icon = QLabel("🤖")
        assistant_icon.setStyleSheet("font-size:27px;")
        assistant_layout.addWidget(assistant_icon)

        assistant_title = QLabel("LabBuddy Assistant")
        assistant_title.setStyleSheet(
            "font-weight:700; color:white; font-size:13px;"
        )
        assistant_layout.addWidget(assistant_title)

        assistant_text = QLabel("Your personal experiment tutor.")
        assistant_text.setObjectName("muted")
        assistant_text.setWordWrap(True)
        assistant_layout.addWidget(assistant_text)

        layout.addWidget(assistant_card)

        version = QLabel("LABBUDDY AI  •  VERSION 1.0")
        version.setObjectName("muted")
        layout.addWidget(version)

        return sidebar

    def create_header(self):
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Your learning workspace starts here.")
        subtitle.setObjectName("muted")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addStretch()

        status = QLabel("●  SYSTEM READY")
        status.setStyleSheet(
            "color:#75d6a0; font-size:11px; font-weight:700;"
            "background:#142b2a; padding:9px 12px; border-radius:8px;"
        )
        layout.addWidget(status)

        return header

    def create_hero(self):
        hero = QFrame()
        hero.setObjectName("hero")

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(25, 23, 25, 23)

        text_layout = QVBoxLayout()
        title = QLabel("Ready to explore your next experiment?")
        title.setObjectName("heroTitle")
        title.setWordWrap(True)

        description = QLabel(
            "Upload your course syllabus, choose an experiment, "
            "and let LabBuddy guide your learning step by step."
        )
        description.setObjectName("heroText")
        description.setWordWrap(True)

        button = QPushButton("＋  Add your first course")
        button.setObjectName("primaryButton")
        button.setMaximumWidth(205)
        button.clicked.connect(self.add_course)

        text_layout.addWidget(title)
        text_layout.addSpacing(5)
        text_layout.addWidget(description)
        text_layout.addSpacing(12)
        text_layout.addWidget(button, alignment=Qt.AlignLeft)

        robot = QLabel("🤖")
        robot.setAlignment(Qt.AlignCenter)
        robot.setStyleSheet("font-size:75px; min-width:130px;")

        layout.addLayout(text_layout, 1)
        layout.addWidget(robot)

        return hero

    def create_stats(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        self.course_count = self.create_stat_card("0", "COURSES ADDED", "📚")
        self.experiment_count = self.create_stat_card(
            "0", "EXPERIMENTS", "🧪"
        )
        self.progress_count = self.create_stat_card(
            "0%", "LEARNING PROGRESS", "📈"
        )

        row.addWidget(self.course_count)
        row.addWidget(self.experiment_count)
        row.addWidget(self.progress_count)

        return row

    def create_stat_card(self, number, label, icon):
        card = QFrame()
        card.setObjectName("statCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 14, 17, 14)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size:20px;")

        number_label = QLabel(number)
        number_label.setObjectName("statNumber")

        caption = QLabel(label)
        caption.setObjectName("muted")

        layout.addWidget(icon_label)
        layout.addWidget(number_label)
        layout.addWidget(caption)

        card.number_label = number_label
        return card

    def create_courses_header(self):
        row = QHBoxLayout()

        title = QLabel("My Courses")
        title.setObjectName("sectionTitle")

        add_button = QPushButton("＋  Add Course")
        add_button.clicked.connect(self.add_course)

        row.addWidget(title)
        row.addStretch()
        row.addWidget(add_button)

        return row

    def refresh_courses(self):
        while self.course_grid.count():
            item = self.course_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.courses:
            empty = QLabel(
                "No courses added yet.\n\n"
                "Upload your syllabus to create your first course."
            )
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color:#8995b0; font-size:14px;"
                "background:#111a2e; border:1px dashed #344363;"
                "border-radius:14px; padding:35px;"
            )
            self.course_grid.addWidget(empty, 0, 0, 1, 2)
        else:
            for index, course in enumerate(self.courses):
                card = CourseCard(course)

                card.view_requested.connect(self.view_course)
                card.edit_requested.connect(self.edit_course)
                card.delete_requested.connect(self.delete_course)

                self.course_grid.addWidget(
                    card, index // 2, index % 2
                )

        self.course_count.number_label.setText(str(len(self.courses)))
        total_experiments = sum(
            len(course.get("experiments", []))
            for course in self.courses
        )

        self.experiment_count.number_label.setText(
            str(total_experiments)
        )
        self.progress_count.number_label.setText("0%")

    def add_course(self):
        course_name, accepted = QInputDialog.getText(
            self,
            "Add Course",
            "Enter course name:"
        )

        if not accepted or not course_name.strip():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Syllabus",
            str(Path.home()),
            "Syllabus Files (*.pdf *.docx *.txt)"
        )

        if not file_path:
            return

        path = Path(file_path)

        try:
            syllabus_text = extract_text(file_path)

            if not syllabus_text.strip():
                QMessageBox.warning(
                    self, "Empty Syllabus",
                    "No readable text was found."
                )
                return

            experiments = extract_experiments(syllabus_text)

            folder_name = re.sub(
                r"[^a-zA-Z0-9_-]",
                "_",
                course_name.strip()
            )

            workspace = BASE_DIR / "course_workspaces" / folder_name

            if workspace.exists():
                QMessageBox.warning(
                    self,
                    "Course already exists",
                    "A course with this workspace name already exists. "
                    "Please use a different course name."
                )
                return

            workspace.mkdir(parents=True)

            course_data = {
                "name": course_name.strip(),
                "filename": path.name,
                "file_path": str(path.resolve()),
                "syllabus_text": syllabus_text,
                "experiments": experiments,
                "workspace": str(workspace)
            }

            metadata_path = workspace / "course.json"

            metadata_path.write_text(
                json.dumps(
                    course_data,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            self.courses.append(course_data)
            self.refresh_courses()

            QMessageBox.information(
                self,
                "Course Added",
                f"Course added successfully!\n\n"
                f"Experiments identified: {len(experiments)}"
            )

        except Exception as error:
            QMessageBox.critical(
                self, "Upload Error", str(error)
            )

    
    def view_course(self, course):
        dialog = CourseDetailsDialog(course, self)
        dialog.exec()


    def edit_course(self, course):
        new_name, accepted = QInputDialog.getText(
            self,
            "Edit Course",
            "Enter new course name:",
            text=course["name"]
        )

        if not accepted or not new_name.strip():
            return

        new_name = new_name.strip()

        # Prevent duplicate course names.
        if any(
            item is not course
            and item["name"].casefold() == new_name.casefold()
            for item in self.courses
        ):
            QMessageBox.warning(
                self,
                "Duplicate Course",
                "A course with this name already exists."
            )
            return

        course["name"] = new_name

        workspace = Path(course["workspace"])
        metadata_path = workspace / "course.json"

        try:
            metadata_path.write_text(
                json.dumps(
                    course,
                    indent=4,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            self.refresh_courses()

            QMessageBox.information(
                self,
                "Updated",
                "Course name updated successfully."
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Update Error",
                str(error)
            )


    def delete_course(self, course):
        answer = QMessageBox.question(
            self,
            "Delete Course",
            f"Are you sure you want to delete "
            f"'{course['name']}'?\n\n"
            "Its saved course information will also be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:
            workspace = Path(course["workspace"])

            if workspace.exists():
                shutil.rmtree(workspace)

            self.courses.remove(course)
            self.refresh_courses()

            QMessageBox.information(
                self,
                "Course Deleted",
                "Course deleted successfully."
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Delete Error",
                str(error)
            )