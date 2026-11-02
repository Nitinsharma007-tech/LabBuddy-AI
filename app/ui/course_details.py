from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTabWidget, QWidget, QFrame
)
import html


THEME = """
QDialog { background:#f1f9fc; color:#17243e; font-family:'Segoe UI'; }
QLabel#title { color:#17243e; font-size:25px; font-weight:800; }
QLabel#muted { color:#64748b; font-size:12px; }
QFrame#summary { background:#ffffff; border:1px solid #e1ecef; border-radius:14px; }
QTabWidget::pane { border:1px solid #dce7e5; border-radius:12px; background:#ffffff; }
QTabBar::tab { background:#edf3ff; color:#64748b; padding:11px 17px; margin-right:4px; border-radius:7px; }
QTabBar::tab:selected { background:#008b7d; color:white; }
QTextBrowser { background:#ffffff; color:#263d49; border:0; padding:15px; font-size:13px; }
QPushButton { background:#edf3ff; color:#23404b; border:1px solid #dce7ef; border-radius:12px; padding:10px 18px; font-weight:650; }
QPushButton:hover { background:#dff8f1; }
QPushButton#primary { background:#008b7d; color:white; border:0; }
"""

class CourseDetailsDialog(QDialog):
    def __init__(self, course, parent=None):
        super().__init__(parent)
        self.course = course
        self.setWindowTitle("Course Details | LabBuddy AI")
        self.resize(900, 680)
        self.setMinimumSize(720, 540)
        self.setStyleSheet(THEME)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(15)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(course.get("name", "Untitled Course"))
        title.setObjectName("title")
        subtitle = QLabel(course.get("filename", "No syllabus file"))
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        header.addWidget(close)
        root.addLayout(header)

        summary = QFrame()
        summary.setObjectName("summary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(18, 14, 18, 14)
        experiments = course.get("experiments", [])
        summary_layout.addWidget(self.metric(str(len(experiments)), "EXPERIMENTS FOUND"))
        summary_layout.addWidget(self.metric(PathSafeExtension(course.get("filename", "")), "FILE TYPE"))
        summary_layout.addWidget(self.metric("Local", "STORAGE"))
        root.addWidget(summary)

        tabs = QTabWidget()
        basic = QTextBrowser()
        basic.setHtml(
            "<h2 style='color:#008b7d'>Course information</h2>"
            f"<p><b>Course name:</b> {html.escape(course.get('name',''))}</p>"
            f"<p><b>Syllabus file:</b> {html.escape(course.get('filename',''))}</p>"
            f"<p><b>File location:</b> {html.escape(course.get('file_path',''))}</p>"
            f"<p><b>Workspace:</b> {html.escape(course.get('workspace','Not available'))}</p>"
        )
        tabs.addTab(basic, "Overview")

        syllabus = QTextBrowser()
        syllabus.setPlainText(course.get("syllabus_text", "Syllabus text is not available."))
        tabs.addTab(syllabus, "Extracted Syllabus")

        experiment_view = QTextBrowser()
        if experiments:
            blocks = []
            for item in experiments:
                number = html.escape(str(item.get("number", "")))
                exp_title = html.escape(str(item.get("title", "Untitled experiment")))
                description = html.escape(str(item.get("description", "No description available.")))
                concepts = html.escape(str(item.get("concepts", "Not specified")))
                blocks.append(
                    f"<div style='padding:12px 0;border-bottom:1px solid #e1ecef'>"
                    f"<h3 style='color:#008b7d'>Experiment {number}: {exp_title}</h3>"
                    f"<p>{description}</p><p><b>Key concepts:</b> {concepts}</p></div>"
                )
            experiment_view.setHtml("".join(blocks))
        else:
            experiment_view.setPlainText("No experiments were identified in this syllabus.")
        tabs.addTab(experiment_view, "Experiments")
        root.addWidget(tabs, 1)

    @staticmethod
    def metric(value, label):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 2, 4, 2)
        number = QLabel(value)
        number.setStyleSheet("color:#008b7d;font-size:20px;font-weight:800;")
        caption = QLabel(label)
        caption.setStyleSheet("color:#64748b;font-size:10px;font-weight:800;")
        layout.addWidget(number)
        layout.addWidget(caption)
        return box


def PathSafeExtension(filename):
    from pathlib import Path
    suffix = Path(filename).suffix.upper().lstrip(".")
    return suffix if suffix else "—"
