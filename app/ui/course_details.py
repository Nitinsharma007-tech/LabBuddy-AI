from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QTabWidget, QWidget
)
import html

class CourseDetailsDialog(QDialog):

    def __init__(self, course, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Course Details | LabBuddy AI")
        self.resize(850, 650)

        self.setStyleSheet("""
            QDialog {
                background: #0b1020;
                color: white;
                font-family: 'Segoe UI';
            }
            QLabel#title {
                color: white;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#muted {
                color: #8995b0;
                font-size: 12px;
            }
            QTabWidget::pane {
                border: 1px solid #293956;
                border-radius: 9px;
                background: #111a2e;
            }
            QTabBar::tab {
                background: #17233c;
                color: #c6d0e8;
                padding: 11px 18px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #293c70;
                color: white;
            }
            QTextBrowser {
                background: #111a2e;
                color: #dce4fa;
                border: none;
                padding: 12px;
                font-size: 13px;
            }
            QPushButton {
                background: #202d49;
                color: white;
                border: 1px solid #344363;
                border-radius: 8px;
                padding: 10px 18px;
            }
        """)

        root = QVBoxLayout(self)

        title = QLabel(course.get("name", "Untitled Course"))
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel(course.get("filename", "No syllabus file"))
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)

        tabs = QTabWidget()

        # Basic information
        basic = QWidget()
        basic_layout = QVBoxLayout(basic)

        experiments = course.get("experiments", [])

        basic_text = QTextBrowser()
        basic_text.setHtml(f"""
            <h2>Course Information</h2>
            <p><b>Course Name:</b> {course.get("name", "")}</p>
            <p><b>Syllabus File:</b> {course.get("filename", "")}</p>
            <p><b>Experiments Identified:</b> {len(experiments)}</p>
            <p><b>File Location:</b> {course.get("file_path", "")}</p>
            <hr>
            <h3>Experiments</h3>
            {''.join(
                f"<p>{e['number']}. {e['title']}</p>"
                for e in experiments
            )}
        """)

        basic_layout.addWidget(basic_text)
        tabs.addTab(basic, "Basic Information")

        # Extracted syllabus
        syllabus = QTextBrowser()
        syllabus.setPlainText(
            course.get(
                "syllabus_text",
                "Syllabus text is not available."
            )
        )
        tabs.addTab(syllabus, "View Syllabus")

        # Experiment list
        experiment_view = QTextBrowser()
        experiment_view.setHtml(
            "<h2>Identified Experiments</h2>" +
            "".join(
                f"<h3>Experiment {e['number']}: {e['title']}</h3>"
                f"<p>{e.get('description', '')}</p>"
                f"<p><b>Key Concepts:</b> "
                f"{e.get('concepts', '')}</p>"
                for e in experiments
            )
        )
        tabs.addTab(experiment_view, "Experiments")

        root.addWidget(tabs)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close)