from pathlib import Path
import json
import re
import shutil
import math

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QBrush, QLinearGradient
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QInputDialog, QMessageBox, QScrollArea,
    QGridLayout, QLineEdit, QSizePolicy, QComboBox
)

from app.ui.experiment_page import ExperimentPage
from app.ui.course_details import CourseDetailsDialog
from app.syllabus.parser import extract_text
from app.syllabus.experiment_extractor import extract_experiments


BASE_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = BASE_DIR / "course_workspaces"
ASSET_DIR = BASE_DIR / "assets"
SUPPORTED_FILES = "*.pdf *.docx *.txt"

COLORS = {
    "background": "#f8f9ff",
    "surface": "#ffffff",
    "surface_low": "#eff4ff",
    "surface_high": "#e5eeff",
    "primary": "#00685d",
    "primary_container": "#008376",
    "secondary": "#95f3e8",
    "text": "#081d31",
    "muted": "#52636b",
    "outline": "#bcc9c6",
    "danger": "#ba1a1a",
}

STYLESHEET = """
QMainWindow, QWidget#centralWidget { background:#f1f9fc; color:#17243e; font-family:'Segoe UI'; }
QFrame#sidebar { background:#ffffff; border:1px solid #e2edf0; border-radius:20px; }
QLabel#brand { color:#17243e; font-size:22px; font-weight:800; }
QLabel#brandAccent { color:#008b7d; font-size:22px; font-weight:800; }
QLabel#muted { color:#64748b; font-size:12px; }
QLabel#pageTitle { color:#17243e; font-size:27px; font-weight:800; }
QLabel#sectionTitle { color:#17243e; font-size:20px; font-weight:800; }
QFrame#hero { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #eafffa,stop:0.55 #d8f8f2,stop:1 #bff2e9); border:1px solid #d0eee8; border-radius:24px; }
QLabel#heroTitle { color:#17243e; font-size:34px; font-weight:850; }
QLabel#heroText { color:#40546b; font-size:14px; }
QFrame#statCard, QFrame#courseCard { background:#ffffff; border:1px solid #e1ecef; border-radius:19px; }
QFrame#courseCard:hover { border:1px solid #55cdbb; }
QLabel#statNumber { color:#007d70; font-size:27px; font-weight:800; }
QLabel#courseName { color:#17243e; font-size:18px; font-weight:800; }
QLabel#eyebrow { color:#007d70; font-size:10px; font-weight:800; letter-spacing:1px; }
QPushButton { background:#edf3ff; color:#17243e; border:1px solid #dce7ef; border-radius:12px; padding:11px 15px; font-size:12px; font-weight:700; }
QPushButton:hover { background:#dff8f1; border-color:#9ce3d5; }
QPushButton#primaryButton { background:#00a991; color:white; border:0; padding:12px 18px; }
QPushButton#primaryButton:hover { background:#008b7d; }
QPushButton#navButton, QPushButton#navActive { text-align:left; padding:13px; border:0; border-radius:11px; font-size:13px; }
QPushButton#navButton { background:transparent; color:#34445c; }
QPushButton#navButton:hover, QPushButton#navActive { background:#dff8f1; color:#007d70; }
QLineEdit, QComboBox { background:#ffffff; color:#17243e; border:1px solid #d5e5e5; border-radius:12px; padding:11px 13px; }
QLineEdit:focus, QComboBox:focus { border:1px solid #00a991; }
QScrollArea { border:0; background:transparent; }
QScrollBar:vertical { background:transparent; width:8px; }
QScrollBar::handle:vertical { background:#b8dcd5; border-radius:4px; }
"""


class AnimatedRobot(QWidget):
    """Qt-painted mascot with a floating body, waving arm and blinking eyes."""

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.phase = 0.0
        self.tick = 0
        self.compact = compact
        self.setMinimumSize(72, 72) if compact else self.setMinimumSize(210, 175)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(40)

    def _animate(self):
        self.phase += 0.075
        self.tick = (self.tick + 1) % 100
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        scale = min(w / 220.0, h / 190.0)
        painter.translate((w - 220 * scale) / 2, (h - 190 * scale) / 2)
        painter.scale(scale, scale)
        bob = math.sin(self.phase) * 4
        painter.translate(0, bob)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 110, 100, 25))
        painter.drawEllipse(48, 166, 126, 13)

        # Antennae and glowing tips
        painter.setPen(QPen(QColor("#00a991"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(76, 43, 67, 17 + int(math.sin(self.phase) * 3))
        painter.drawLine(145, 43, 154, 17 - int(math.sin(self.phase) * 3))
        painter.setBrush(QColor("#43dfd0"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(59, 8 + int(math.sin(self.phase) * 3), 16, 16)
        painter.drawEllipse(146, 8 - int(math.sin(self.phase) * 3), 16, 16)

        # Waving arm
        painter.save()
        painter.translate(151, 94)
        painter.rotate(-25 + math.sin(self.phase * 1.5) * 17)
        painter.setPen(QPen(QColor("#d8f5f1"), 16, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 0, 27, -27)
        painter.setBrush(QColor("#f7fdff"))
        painter.setPen(QPen(QColor("#a9d5dc"), 2))
        painter.drawEllipse(17, -45, 25, 25)
        painter.restore()

        # Body and legs
        grad = QLinearGradient(65, 90, 155, 166)
        grad.setColorAt(0, QColor("#ffffff"))
        grad.setColorAt(1, QColor("#b9e8e9"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#a9d8dc"), 2))
        painter.drawRoundedRect(65, 91, 91, 76, 28, 28)
        painter.setPen(QPen(QColor("#d6f0f0"), 13, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(91, 157, 87, 176)
        painter.drawLine(132, 157, 137, 176)
        painter.setPen(QPen(QColor("#00bda8"), 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(82, 179, 94, 179)
        painter.drawLine(132, 179, 144, 179)

        # Chest flask emblem
        painter.setBrush(QColor("#d8fff7"))
        painter.setPen(QPen(QColor("#54cfc0"), 2))
        painter.drawEllipse(101, 112, 20, 20)
        painter.setPen(QPen(QColor("#008b7d"), 2))
        painter.drawLine(111, 116, 107, 125)
        painter.drawLine(107, 125, 115, 125)

        # Head shell and dark glass face
        head = QLinearGradient(57, 34, 160, 110)
        head.setColorAt(0, QColor("#ffffff"))
        head.setColorAt(1, QColor("#c8e6ed"))
        painter.setBrush(QBrush(head))
        painter.setPen(QPen(QColor("#a6d1dc"), 2))
        painter.drawRoundedRect(48, 35, 126, 83, 34, 34)
        painter.setBrush(QColor("#102c49"))
        painter.setPen(QPen(QColor("#6b9cac"), 2))
        painter.drawRoundedRect(59, 49, 104, 57, 24, 24)

        # Blink every few seconds
        painter.setPen(QPen(QColor("#50f4ed"), 4, Qt.SolidLine, Qt.RoundCap))
        if self.tick in (0, 1, 2, 3):
            painter.drawLine(82, 77, 96, 77)
            painter.drawLine(126, 77, 140, 77)
        else:
            painter.setBrush(QColor("#50f4ed"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(82, 65, 11, 21, 5, 5)
            painter.drawRoundedRect(128, 65, 11, 21, 5, 5)
        painter.setPen(QPen(QColor("#50f4ed"), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(101, 79, 23, 15, 205 * 16, 130 * 16)

        # Ear pieces
        painter.setBrush(QColor("#00bda8"))
        painter.setPen(QPen(QColor("#6ce8dc"), 2))
        painter.drawRoundedRect(39, 62, 13, 34, 6, 6)
        painter.drawRoundedRect(171, 62, 13, 34, 6, 6)
        painter.end()


class CourseCard(QFrame):
    view_requested = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    learn_requested = Signal(dict)

    def __init__(self, course, parent=None):
        super().__init__(parent)
        self.course = course
        self.setObjectName("courseCard")
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        tile = QLabel("🧪")
        tile.setFixedSize(78, 78)
        tile.setAlignment(Qt.AlignCenter)
        tile.setStyleSheet("background:#e2f8f4;border-radius:16px;font-size:34px;")
        layout.addWidget(tile, alignment=Qt.AlignVCenter)

        details = QVBoxLayout()
        details.setSpacing(7)
        name = QLabel(course.get("name", "Untitled course"))
        name.setObjectName("courseName")
        details.addWidget(name)
        filename = QLabel("▤  " + course.get("filename", "No syllabus file"))
        filename.setObjectName("muted")
        filename.setWordWrap(True)
        details.addWidget(filename)
        count = len(course.get("experiments", []))
        info = QLabel(f"⚗  {count} experiments extracted")
        info.setStyleSheet("color:#008b7d;font-size:12px;font-weight:750;")
        details.addWidget(info)
        details.addStretch()
        layout.addLayout(details, 3)

        right = QVBoxLayout()
        top = QHBoxLayout()
        top.addStretch()
        tag = QLabel(Path(course.get("filename", "")).suffix.upper().lstrip(".") or "COURSE")
        tag.setStyleSheet("background:#dff8f1;color:#007d70;border-radius:9px;padding:7px 11px;font-size:10px;font-weight:800;")
        top.addWidget(tag)
        right.addLayout(top)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        view = QPushButton("◉  View Details")
        view.clicked.connect(lambda: self.view_requested.emit(self.course))
        learn = QPushButton("⚗  Explore Experiments")
        learn.setObjectName("primaryButton")
        learn.clicked.connect(lambda: self.learn_requested.emit(self.course))
        edit = QPushButton("✎  Edit")
        edit.clicked.connect(lambda: self.edit_requested.emit(self.course))
        delete = QPushButton("▤  Delete")
        delete.setStyleSheet("color:#d51f2a;background:#fff1f2;border:1px solid #ffd6da;")
        delete.clicked.connect(lambda: self.delete_requested.emit(self.course))
        for button in (view, learn, edit, delete):
            actions.addWidget(button, 1)
        right.addStretch()
        right.addLayout(actions)
        layout.addLayout(right, 5)


class LabBuddyDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabBuddy AI | Learning Workspace")
        self.resize(1320, 850)
        self.setMinimumSize(1000, 680)
        self.courses = []
        self.load_courses()

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(18)

        root.addWidget(self.create_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(17)
        content_layout.addWidget(self.create_header())
        content_layout.addWidget(self.create_hero())
        content_layout.addLayout(self.create_stats())
        content_layout.addLayout(self.create_courses_header())

        self.course_area = QScrollArea()
        self.course_area.setWidgetResizable(True)
        self.course_container = QWidget()
        self.course_grid = QGridLayout(self.course_container)
        self.course_grid.setContentsMargins(0, 4, 4, 4)
        self.course_grid.setHorizontalSpacing(0)
        self.course_grid.setVerticalSpacing(12)
        self.course_area.setWidget(self.course_container)
        content_layout.addWidget(self.course_area, 1)
        root.addWidget(content, 1)

        self.setStyleSheet(STYLESHEET)
        self.refresh_courses()

    def load_courses(self):
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        self.courses = []
        for metadata_file in WORKSPACE_DIR.glob("*/course.json"):
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
        sidebar.setFixedWidth(205)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(17, 22, 17, 18)
        layout.setSpacing(10)

        brand_row = QHBoxLayout()
        mark = AnimatedRobot(compact=True)
        mark.setFixedSize(42, 42)
        brand_row.addWidget(mark)
        brand = QLabel("LabBuddy")
        brand.setObjectName("brand")
        accent = QLabel("AI")
        accent.setObjectName("brandAccent")
        brand_row.addWidget(brand)
        brand_row.addWidget(accent)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        tagline = QLabel("YOUR AI LAB PARTNER")
        tagline.setObjectName("muted")
        layout.addWidget(tagline)
        layout.addSpacing(24)

        section = QLabel("WORKSPACE")
        section.setObjectName("eyebrow")
        layout.addWidget(section)

        dashboard = QPushButton("⌂   Dashboard")
        dashboard.setObjectName("navActive")
        dashboard.setEnabled(False)
        layout.addWidget(dashboard)
        courses = QPushButton("▤   My Courses")
        courses.setObjectName("navButton")
        courses.clicked.connect(lambda: self.course_area.ensureVisible(0, 0))
        layout.addWidget(courses)
        upload = QPushButton("＋   Upload Syllabus")
        upload.setObjectName("navButton")
        upload.clicked.connect(self.add_course)
        layout.addWidget(upload)

        layout.addStretch()
        assistant = QFrame()
        assistant.setStyleSheet("background:#effaf7;border:1px solid #ccebe4;border-radius:14px;")
        assistant_layout = QVBoxLayout(assistant)
        assistant_layout.setContentsMargins(13, 13, 13, 13)
        bot = AnimatedRobot(compact=True)
        bot.setFixedSize(70, 66)
        assistant_layout.addWidget(bot, alignment=Qt.AlignLeft)
        label = QLabel("LabBuddy Assistant")
        label.setStyleSheet("font-weight:800;color:#081d31;font-size:13px;")
        assistant_layout.addWidget(label)
        desc = QLabel("Your personal experiment tutor, ready when you are.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#52636b;font-size:11px;")
        assistant_layout.addWidget(desc)
        layout.addWidget(assistant)
        version = QLabel("LABBUDDY AI  •  DESKTOP")
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
        subtitle = QLabel("Organize your laboratory courses and continue learning.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch()
        status = QLabel("●  LOCAL WORKSPACE")
        status.setStyleSheet("color:#00685d;background:#dff5f0;border-radius:9px;padding:9px 12px;font-size:11px;font-weight:800;")
        layout.addWidget(status)
        return header

    def create_hero(self):
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(285)
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(30, 22, 24, 20)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(9)
        pill = QLabel("⚗  AUTONOMOUS LAB ASSISTANT  •  READY")
        pill.setObjectName("eyebrow")
        pill.setStyleSheet("background:#ffffff;border:1px solid #ccefe7;border-radius:16px;padding:9px 13px;")
        pill.setMaximumWidth(315)
        title = QLabel("Your Lab Journey,\nMade Smarter.")
        title.setObjectName("heroTitle")
        description = QLabel(
            "Organize your laboratory courses, explore your syllabus, and "
            "let LabBuddy make your academic workspace smarter."
        )
        description.setObjectName("heroText")
        description.setWordWrap(True)
        description.setMaximumWidth(590)

        buttons = QHBoxLayout()
        upload = QPushButton("⬆  Upload Syllabus  ›")
        upload.setObjectName("primaryButton")
        upload.clicked.connect(self.add_course)
        explore = QPushButton("▱  Explore My Courses")
        explore.clicked.connect(lambda: self.course_area.ensureVisible(0, 0))
        buttons.addWidget(upload)
        buttons.addWidget(explore)
        buttons.addStretch()

        text_layout.addWidget(pill)
        text_layout.addSpacing(4)
        text_layout.addWidget(title)
        text_layout.addWidget(description)
        text_layout.addSpacing(7)
        text_layout.addLayout(buttons)
        text_layout.addStretch()
        layout.addLayout(text_layout, 3)

        mascot_area = QWidget()
        mascot_layout = QVBoxLayout(mascot_area)
        mascot_layout.setContentsMargins(0, 0, 0, 0)
        speech = QLabel("Hey there! 👋\nReady to organize\nyour lab courses?")
        speech.setAlignment(Qt.AlignCenter)
        speech.setStyleSheet("background:#ffffff;color:#17243e;border:1px solid #e2eeee;border-radius:20px;padding:10px 14px;font-size:12px;font-weight:700;")
        speech.setMaximumWidth(175)
        mascot_layout.addWidget(speech, alignment=Qt.AlignHCenter)
        mascot = AnimatedRobot()
        mascot.setMinimumSize(220, 175)
        mascot_layout.addWidget(mascot, 1)
        layout.addWidget(mascot_area, 2)
        return hero

    def create_stats(self):
        row = QHBoxLayout()
        row.setSpacing(13)
        self.course_count = self.create_stat_card("0", "TOTAL COURSES", "📁")
        self.experiment_count = self.create_stat_card("0", "TOTAL EXPERIMENTS", "🧪")
        self.format_count = self.create_stat_card("PDF · DOCX · TXT", "SUPPORTED FORMATS", "📄", compact=True)
        self.file_count = self.create_stat_card("0", "SYLLABUS FILES", "✓")
        for card in (self.course_count, self.experiment_count, self.format_count, self.file_count):
            row.addWidget(card, 1)
        return row

    def create_stat_card(self, number, label, icon, compact=False):
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 14, 15, 14)
        top = QHBoxLayout()
        caption = QLabel(label)
        caption.setObjectName("muted")
        glyph = QLabel(icon)
        glyph.setStyleSheet("font-size:20px;background:#dff5f0;border-radius:9px;padding:6px;")
        top.addWidget(caption)
        top.addStretch()
        top.addWidget(glyph)
        number_label = QLabel(number)
        number_label.setStyleSheet("color:#00685d;font-size:21px;font-weight:800;" if compact else "")
        if not compact:
            number_label.setObjectName("statNumber")
        layout.addLayout(top)
        layout.addWidget(number_label)
        card.number_label = number_label
        return card

    def create_courses_header(self):
        row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("My Learning Workspace")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("All your laboratory courses, in one place.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        row.addLayout(title_box)
        row.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search courses...")
        self.search_input.setFixedWidth(245)
        self.search_input.textChanged.connect(self.filter_courses)
        row.addWidget(self.search_input)
        add_button = QPushButton("＋  Add Course")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self.add_course)
        row.addWidget(add_button)
        return row

    def refresh_courses(self):
        while self.course_grid.count():
            item = self.course_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.course_cards = []
        if not self.courses:
            empty = QFrame()
            empty.setStyleSheet("background:#ffffff;border:1px dashed #a8c9c2;border-radius:15px;")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(30, 35, 30, 35)
            icon = QLabel("📚")
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("font-size:35px;")
            heading = QLabel("Your workspace is ready")
            heading.setAlignment(Qt.AlignCenter)
            heading.setStyleSheet("font-size:17px;font-weight:800;color:#081d31;")
            message = QLabel("Upload your first syllabus to create a course and identify its experiments.")
            message.setAlignment(Qt.AlignCenter)
            message.setStyleSheet("color:#52636b;font-size:12px;")
            empty_layout.addWidget(icon)
            empty_layout.addWidget(heading)
            empty_layout.addWidget(message)
            self.course_grid.addWidget(empty, 0, 0, 1, 1)
        else:
            for index, course in enumerate(self.courses):
                card = CourseCard(course)
                card.view_requested.connect(self.view_course)
                card.edit_requested.connect(self.edit_course)
                card.delete_requested.connect(self.delete_course)
                card.learn_requested.connect(self.open_experiments)
                self.course_grid.addWidget(card, index, 0)
                self.course_cards.append(card)

        total_experiments = sum(len(c.get("experiments", [])) for c in self.courses)
        self.course_count.number_label.setText(str(len(self.courses)))
        self.experiment_count.number_label.setText(str(total_experiments))
        self.file_count.number_label.setText(str(sum(bool(c.get("filename")) for c in self.courses)))
        self.filter_courses(self.search_input.text() if hasattr(self, "search_input") else "")

    def filter_courses(self, query):
        query = query.strip().casefold()
        for card in getattr(self, "course_cards", []):
            course = card.course
            haystack = f"{course.get('name','')} {course.get('filename','')}".casefold()
            card.setVisible(query in haystack)

    def add_course(self):
        course_name, accepted = QInputDialog.getText(self, "Add Course", "Enter course name:")
        if not accepted or not course_name.strip():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Syllabus", str(Path.home()),
            "Syllabus Files (*.pdf *.docx *.txt)"
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            syllabus_text = extract_text(file_path)
            if not syllabus_text.strip():
                QMessageBox.warning(self, "Empty Syllabus", "No readable text was found in this file.")
                return
            experiments = extract_experiments(syllabus_text)
            folder_name = re.sub(r"[^a-zA-Z0-9_-]", "_", course_name.strip())
            workspace = WORKSPACE_DIR / folder_name
            if workspace.exists():
                QMessageBox.warning(self, "Course already exists", "A course with this workspace name already exists. Choose another name.")
                return
            workspace.mkdir(parents=True)
            course_data = {
                "name": course_name.strip(),
                "filename": path.name,
                "file_path": str(path.resolve()),
                "syllabus_text": syllabus_text,
                "experiments": experiments,
                "workspace": str(workspace),
            }
            (workspace / "course.json").write_text(
                json.dumps(course_data, indent=4, ensure_ascii=False), encoding="utf-8"
            )
            self.courses.append(course_data)
            self.refresh_courses()
            QMessageBox.information(
                self, "Course Added",
                f"Course added successfully.\n\nExperiments identified: {len(experiments)}"
            )
        except Exception as error:
            QMessageBox.critical(self, "Upload Error", str(error))

    def view_course(self, course):
        CourseDetailsDialog(course, self).exec()

    def open_experiments(self, course):
        dialog = ExperimentPage(course, self)
        dialog.exec()

    def edit_course(self, course):
        new_name, accepted = QInputDialog.getText(
            self, "Edit Course", "Enter new course name:", text=course.get("name", "")
        )
        if not accepted or not new_name.strip():
            return
        new_name = new_name.strip()
        if any(item is not course and item.get("name", "").casefold() == new_name.casefold() for item in self.courses):
            QMessageBox.warning(self, "Duplicate Course", "A course with this name already exists.")
            return
        old_name = course.get("name", "")
        course["name"] = new_name
        workspace = Path(course["workspace"])
        new_folder_name = re.sub(r"[^a-zA-Z0-9_-]", "_", new_name)
        new_workspace = WORKSPACE_DIR / new_folder_name
        try:
            if new_workspace != workspace and new_workspace.exists():
                raise FileExistsError("A workspace with the new course name already exists.")
            if new_workspace != workspace:
                workspace.rename(new_workspace)
                course["workspace"] = str(new_workspace)
            (Path(course["workspace"]) / "course.json").write_text(
                json.dumps(course, indent=4, ensure_ascii=False), encoding="utf-8"
            )
            self.refresh_courses()
            QMessageBox.information(self, "Updated", f"Course renamed from '{old_name}' to '{new_name}'.")
        except Exception as error:
            course["name"] = old_name
            QMessageBox.critical(self, "Update Error", str(error))

    def delete_course(self, course):
        answer = QMessageBox.question(
            self, "Delete Course",
            f"Are you sure you want to delete '{course.get('name', 'this course')}'?\n\nIts saved course workspace will also be deleted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        try:
            workspace = Path(course["workspace"])
            if workspace.exists():
                shutil.rmtree(workspace)
            self.courses.remove(course)
            self.refresh_courses()
            QMessageBox.information(self, "Course Deleted", "Course deleted successfully.")
        except Exception as error:
            QMessageBox.critical(self, "Delete Error", str(error))
