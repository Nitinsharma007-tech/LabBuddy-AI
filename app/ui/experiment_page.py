from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QLineEdit, QTextBrowser
)
import html


THEME = """
QDialog { background:#f1f9fc; color:#17243e; font-family:'Segoe UI'; }
QLabel#title { font-size:25px; font-weight:800; color:#17243e; }
QLabel#muted { color:#64748b; font-size:12px; }
QFrame#panel { background:#ffffff; border:1px solid #e1ecef; border-radius:15px; }
QListWidget { background:transparent; border:0; outline:0; color:#263d49; font-size:13px; }
QListWidget::item { background:#f3f7ff; border:1px solid #e1eae8; border-radius:12px; padding:13px; margin:4px 2px; }
QListWidget::item:selected { background:#dff8f1; border:1px solid #65cbbb; color:#005048; }
QLineEdit { background:#f1f9fc; border:1px solid #d5e5e5; border-radius:12px; padding:11px; color:#17243e; }
QLineEdit:focus { border:1px solid #008b7d; }
QTextBrowser { background:transparent; border:0; color:#263d49; font-size:13px; }
QPushButton { background:#edf3ff; color:#23404b; border:1px solid #dce7ef; border-radius:12px; padding:11px 17px; font-weight:650; }
QPushButton:hover { background:#dff8f1; }
QPushButton#primary { background:#008b7d; color:white; border:0; }
QPushButton#primary:hover { background:#00a991; }
"""

class ExperimentPage(QDialog):
    experiment_selected = Signal(dict)

    def __init__(self, course, parent=None):
        super().__init__(parent)
        self.course = course
        self.experiments = course.get("experiments", [])
        self.selected_experiment = None
        self.setWindowTitle(f"{course.get('name', 'Course')} | LabBuddy AI")
        self.resize(1080, 700)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(THEME)
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        header = QHBoxLayout()
        heading_box = QVBoxLayout()
        title = QLabel(self.course.get("name", "Course experiments"))
        title.setObjectName("title")
        subtitle = QLabel(
            f"{len(self.experiments)} experiments extracted from "
            f"{self.course.get('filename', 'the syllabus')}"
        )
        subtitle.setObjectName("muted")
        heading_box.addWidget(title)
        heading_box.addWidget(subtitle)
        header.addLayout(heading_box)
        header.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        header.addWidget(close)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(15)

        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(15, 15, 15, 15)
        eyebrow = QLabel("CHOOSE AN EXPERIMENT")
        eyebrow.setStyleSheet("color:#008b7d;font-size:10px;font-weight:800;letter-spacing:1px;")
        left_layout.addWidget(eyebrow)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search experiments...")
        self.search.textChanged.connect(self.filter_experiments)
        left_layout.addWidget(self.search)
        self.experiment_list = QListWidget()
        self.experiment_list.currentRowChanged.connect(self.show_experiment)
        left_layout.addWidget(self.experiment_list, 1)

        right = QFrame()
        right.setObjectName("panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 20, 20, 20)
        self.number_label = QLabel("EXPERIMENT DETAILS")
        self.number_label.setStyleSheet("color:#008b7d;font-size:10px;font-weight:800;letter-spacing:1px;")
        right_layout.addWidget(self.number_label)
        self.experiment_title = QLabel("Choose an experiment")
        self.experiment_title.setStyleSheet("font-size:23px;font-weight:800;color:#17243e;")
        self.experiment_title.setWordWrap(True)
        right_layout.addWidget(self.experiment_title)
        self.details = QTextBrowser()
        right_layout.addWidget(self.details, 1)
        self.start_button = QPushButton("Start Learning  →")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_learning)
        right_layout.addWidget(self.start_button)

        body.addWidget(left, 5)
        body.addWidget(right, 7)
        root.addLayout(body, 1)
        self.populate_experiments()

    def populate_experiments(self):
        self.experiment_list.clear()
        for experiment in self.experiments:
            number = str(experiment.get("number", ""))
            title = str(experiment.get("title", "Untitled experiment"))
            item = QListWidgetItem(f"{number.zfill(2)}   {title}")
            item.setData(Qt.UserRole, experiment)
            self.experiment_list.addItem(item)
        if self.experiments:
            self.experiment_list.setCurrentRow(0)
        else:
            self.details.setPlainText("No experiments were identified. Check the extracted syllabus text.")

    def filter_experiments(self, query):
        query = query.strip().casefold()
        for index in range(self.experiment_list.count()):
            item = self.experiment_list.item(index)
            experiment = item.data(Qt.UserRole)
            searchable = " ".join([
                str(experiment.get("title", "")),
                str(experiment.get("description", "")),
                str(experiment.get("concepts", "")),
            ]).casefold()
            item.setHidden(query not in searchable)

    def show_experiment(self, row):
        if row < 0:
            return
        item = self.experiment_list.item(row)
        if item is None:
            return
        experiment = item.data(Qt.UserRole)
        self.selected_experiment = experiment
        number = html.escape(str(experiment.get("number", "")))
        title = html.escape(str(experiment.get("title", "Untitled experiment")))
        description = html.escape(str(experiment.get("description", "No task description available.")))
        concepts = html.escape(str(experiment.get("concepts", "No key concepts available.")))
        self.number_label.setText(f"EXPERIMENT {number}")
        self.experiment_title.setText(experiment.get("title", "Untitled experiment"))
        self.details.setHtml(
            f"<h3 style='color:#008b7d'>Objective / Task</h3><p>{description}</p>"
            f"<h3 style='color:#008b7d'>Key Concepts</h3><p>{concepts}</p>"
            "<p style='color:#64748b'>Select Start Learning to begin your guided lesson.</p>"
        )
        self.start_button.setEnabled(True)

    def start_learning(self):
        if self.selected_experiment:
            self.experiment_selected.emit(self.selected_experiment)
            self.accept()
