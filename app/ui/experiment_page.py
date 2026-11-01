from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QListWidget,
    QListWidgetItem, QLineEdit, QTextBrowser
)
import html


class ExperimentPage(QDialog):
    experiment_selected = Signal(dict)

    def __init__(self, course, parent=None):
        super().__init__(parent)

        self.course = course
        self.experiments = course.get("experiments", [])
        self.selected_experiment = None

        self.setWindowTitle(f"{course['name']} | LabBuddy AI")
        self.resize(1050, 680)
        self.setMinimumSize(850, 580)

        self.setStyleSheet("""
            QDialog {
                background: #0b1020;
                color: #e8ecf8;
                font-family: 'Segoe UI';
            }
            QLabel#title {
                font-size: 25px;
                font-weight: 700;
                color: white;
            }
            QLabel#muted {
                color: #8995b0;
                font-size: 12px;
            }
            QFrame#panel {
                background: #111a2e;
                border: 1px solid #263653;
                border-radius: 13px;
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #dce4fa;
                font-size: 13px;
            }
            QListWidget::item {
                background: #17233c;
                border: 1px solid #283956;
                border-radius: 9px;
                padding: 13px;
                margin: 4px 2px;
            }
            QListWidget::item:selected {
                background: #293c70;
                border: 1px solid #7186ff;
            }
            QLineEdit {
                background: #17233c;
                border: 1px solid #344363;
                border-radius: 8px;
                padding: 11px;
                color: white;
            }
            QTextBrowser {
                background: transparent;
                border: none;
                color: #c2cde5;
                font-size: 13px;
            }
            QPushButton {
                background: #202d49;
                color: white;
                border: 1px solid #344363;
                border-radius: 8px;
                padding: 11px 17px;
                font-weight: 600;
            }
            QPushButton#primary {
                background: #687cf5;
                border: none;
            }
            QPushButton#primary:hover {
                background: #7d8eff;
            }
        """)

        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(25, 22, 25, 22)
        root.setSpacing(17)

        # Header
        header = QHBoxLayout()

        heading_box = QVBoxLayout()

        title = QLabel(self.course["name"])
        title.setObjectName("title")

        subtitle = QLabel(
            f"{len(self.experiments)} experiments identified from "
            f"{self.course['filename']}"
        )
        subtitle.setObjectName("muted")

        heading_box.addWidget(title)
        heading_box.addWidget(subtitle)

        header.addLayout(heading_box)
        header.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        header.addWidget(close_button)

        root.addLayout(header)

        # Main two-column layout
        body = QHBoxLayout()
        body.setSpacing(16)

        # Left panel
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)

        list_title = QLabel("SELECT AN EXPERIMENT")
        list_title.setStyleSheet(
            "font-size:12px; font-weight:700; color:#9eadd0;"
        )
        left_layout.addWidget(list_title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search experiments...")
        self.search.textChanged.connect(self.filter_experiments)
        left_layout.addWidget(self.search)

        self.experiment_list = QListWidget()
        self.experiment_list.currentRowChanged.connect(
            self.show_experiment
        )
        left_layout.addWidget(self.experiment_list)

        # Right panel
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(22, 22, 22, 22)

        self.number_label = QLabel("EXPERIMENT DETAILS")
        self.number_label.setStyleSheet(
            "font-size:11px; color:#91a4ff; font-weight:700;"
        )
        right_layout.addWidget(self.number_label)

        self.experiment_title = QLabel("Choose an experiment")
        self.experiment_title.setStyleSheet(
            "font-size:23px; font-weight:700; color:white;"
        )
        self.experiment_title.setWordWrap(True)
        right_layout.addWidget(self.experiment_title)

        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        right_layout.addWidget(self.details, 1)

        self.start_button = QPushButton("Start Learning  →")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_learning)
        right_layout.addWidget(self.start_button)

        body.addWidget(left_panel, 5)
        body.addWidget(right_panel, 7)

        root.addLayout(body, 1)

        self.populate_experiments()

    def populate_experiments(self):
        self.experiment_list.clear()

        for experiment in self.experiments:
            item = QListWidgetItem(
                f"  {experiment['number']:02d}   "
                f"{experiment['title']}"
            )
            item.setData(Qt.UserRole, experiment)
            self.experiment_list.addItem(item)

        if self.experiments:
            self.experiment_list.setCurrentRow(0)

    def filter_experiments(self, query):
        query = query.strip().lower()

        for index in range(self.experiment_list.count()):
            item = self.experiment_list.item(index)
            experiment = item.data(Qt.UserRole)

            searchable = (
                experiment["title"] + " " +
                experiment.get("description", "") + " " +
                experiment.get("concepts", "")
            ).lower()

            item.setHidden(query not in searchable)

    def show_experiment(self, row):
        if row < 0:
            return

        item = self.experiment_list.item(row)

        if item is None:
            return

        experiment = item.data(Qt.UserRole)
        self.selected_experiment = experiment

        self.number_label.setText(
            f"EXPERIMENT {experiment['number']:02d}"
        )

        self.experiment_title.setText(experiment["title"])

        description = html.escape(
            experiment.get("description", "No task description available.")
        )

        concepts = html.escape(
            experiment.get("concepts", "No key concepts available.")
        )

        self.details.setHtml(f"""
            <h3 style="color:#91a4ff;">Experiment Objective / Task</h3>
            <p>{description}</p>
            <br>
            <h3 style="color:#91a4ff;">Key Concepts</h3>
            <p>{concepts}</p>
            <br>
            <p style="color:#8995b0;">
                Select Start Learning to begin your guided lesson.
            </p>
        """)

        self.start_button.setEnabled(True)

    def start_learning(self):
        if self.selected_experiment:
            self.experiment_selected.emit(
                self.selected_experiment
            )
            self.accept()