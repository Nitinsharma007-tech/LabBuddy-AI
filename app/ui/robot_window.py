import math

from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class RobotMascot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0
        self.blink = 0
        self.state = "idle"
        self.setFixedSize(150, 142)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(45)

    def animate(self):
        self.phase += 0.09
        self.blink = (self.blink + 1) % 90
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, math.sin(self.phase) * 2.5)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 90, 100, 28))
        painter.drawEllipse(31, 128, 88, 9)

        painter.setPen(QPen(QColor("#00a991"), 4))
        painter.drawLine(53, 35, 46, 15)
        painter.drawLine(98, 35, 105, 15)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#43dfd0"))
        painter.drawEllipse(40, 8, 12, 12)
        painter.drawEllipse(99, 8, 12, 12)

        gradient = QLinearGradient(40, 65, 112, 128)
        gradient.setColorAt(0, QColor("#ffffff"))
        gradient.setColorAt(1, QColor("#b9e8e9"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#a9d8dc"), 2))
        painter.drawRoundedRect(38, 65, 76, 63, 22, 22)

        painter.setBrush(QColor("#102c49"))
        painter.setPen(QPen(QColor("#6b9cac"), 2))
        painter.drawRoundedRect(27, 30, 98, 65, 25, 25)

        eye_color = QColor("#ffb454") if self.state == "error" else QColor("#50f4ed")
        if self.blink in (0, 1, 2):
            painter.setPen(QPen(eye_color, 4))
            painter.drawLine(53, 61, 64, 61)
            painter.drawLine(87, 61, 98, 61)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(eye_color)
            painter.drawRoundedRect(54, 49, 9, 19, 4, 4)
            painter.drawRoundedRect(88, 49, 9, 19, 4, 4)

        painter.setPen(QPen(eye_color, 3))
        painter.drawArc(68, 66, 18, 11, 205 * 16, 130 * 16)
        painter.end()


class ExperimentSelectionDialog(QDialog):
    """Large, scrollable experiment picker. It stays non-modal so voice works too."""

    experiment_chosen = Signal(int)

    def __init__(self, course_name, experiments, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{course_name} — Experiment Library")
        self.setMinimumSize(760, 620)
        self.resize(850, 700)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setStyleSheet("""
            QDialog {
                background: #f3f8fb;
            }
            QLabel#heading {
                color: #102c49;
                font: 700 22pt 'Segoe UI';
            }
            QLabel#subtitle {
                color: #587184;
                font: 10.5pt 'Segoe UI';
            }
            QFrame#experimentCard {
                background: white;
                border: 1px solid #dce9ef;
                border-radius: 15px;
            }
            QLabel#experimentNumber {
                color: #008f83;
                font: 700 10pt 'Segoe UI';
            }
            QLabel#experimentTitle {
                color: #102c49;
                font: 600 12pt 'Segoe UI';
            }
            QLabel#experimentDescription {
                color: #587184;
                font: 9.5pt 'Segoe UI';
            }
            QPushButton#chooseButton {
                color: white;
                background: #008f83;
                border: none;
                border-radius: 9px;
                padding: 9px 15px;
                font: 600 9.5pt 'Segoe UI';
            }
            QPushButton#chooseButton:hover {
                background: #00776e;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #e5eff2;
                width: 9px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #43cfc1;
                border-radius: 4px;
                min-height: 30px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(25, 22, 25, 22)
        root.setSpacing(12)

        heading = QLabel("Choose Your Experiment")
        heading.setObjectName("heading")
        root.addWidget(heading)

        subtitle = QLabel(
            f"Course: {course_name}   •   {len(experiments)} experiments available\n"
            "Select a card, or tell LabBuddy the experiment number or name."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(4, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        valid_experiments = [
            item for item in experiments if isinstance(item, dict)
        ]

        for index, experiment in enumerate(valid_experiments):
            number = experiment.get("number", index + 1)
            title = experiment.get("title", "Untitled experiment")
            description = experiment.get("description", "")
            concepts = experiment.get("concepts", "")

            card = QFrame()
            card.setObjectName("experimentCard")
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(8)

            number_label = QLabel(f"EXPERIMENT {number:02}" if isinstance(number, int) else f"EXPERIMENT {number}")
            number_label.setObjectName("experimentNumber")

            title_label = QLabel(str(title))
            title_label.setObjectName("experimentTitle")
            title_label.setWordWrap(True)

            description_label = QLabel(str(description or concepts or "No description available."))
            description_label.setObjectName("experimentDescription")
            description_label.setWordWrap(True)
            description_label.setMaximumHeight(68)

            choose = QPushButton("Select experiment  →")
            choose.setObjectName("chooseButton")
            choose.clicked.connect(
                lambda checked=False, n=int(number): self.choose_experiment(n)
            )

            card_layout.addWidget(number_label)
            card_layout.addWidget(title_label)
            card_layout.addWidget(description_label)
            card_layout.addWidget(choose)

            grid.addWidget(card, index // 2, index % 2)

        self.scroll.setWidget(content)
        root.addWidget(self.scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                color: #31566a;
                background: #e4eef2;
                border: none;
                border-radius: 9px;
                padding: 9px 20px;
                font: 600 9.5pt 'Segoe UI';
            }
            QPushButton:hover { background: #d4e5ea; }
        """)
        close_button.clicked.connect(self.hide)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def choose_experiment(self, number):
        self.experiment_chosen.emit(number)
        self.hide()


class RobotWindow(QWidget):
    listen_requested = Signal()
    idle_requested = Signal()
    exit_requested = Signal()
    experiment_selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.drag_offset = QPoint()
        self.press_pos = QPoint()
        self.dragging = False
        self.experiment_dialog = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.bubble_frame = QFrame()
        self.bubble_frame.setObjectName("speechBubble")
        self.bubble_frame.setStyleSheet("""
            QFrame#speechBubble {
                background-color: #ffffff;
                border: 2px solid #43dfd0;
                border-radius: 22px;
            }
        """)
        bubble_layout = QVBoxLayout(self.bubble_frame)
        bubble_layout.setContentsMargins(12, 10, 12, 10)

        self.bubble_title = QLabel("LABBUDDY")
        self.bubble_title.setStyleSheet("""
            QLabel {
                color: #008f83;
                background: transparent;
                border: none;
                font: bold 9pt 'Segoe UI';
            }
        """)
        bubble_layout.addWidget(self.bubble_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #edf7f7; width: 7px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #43cfc1; border-radius: 3px; min-height: 25px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.bubble_text = QLabel("")
        self.bubble_text.setWordWrap(True)
        self.bubble_text.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.bubble_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.bubble_text.setStyleSheet("""
            QLabel {
                color: #18364d;
                background: transparent;
                border: none;
                font: 10pt 'Segoe UI';
                padding: 3px;
            }
        """)
        self.scroll_area.setWidget(self.bubble_text)
        bubble_layout.addWidget(self.scroll_area)

        self.bubble_frame.setFixedHeight(205)
        self.bubble_frame.hide()
        layout.addWidget(self.bubble_frame)

        self.mascot = RobotMascot()
        layout.addWidget(self.mascot, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status = QLabel("Ready! Click me.")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("""
            QLabel {
                background: #102c49;
                color: #e9fffc;
                border-radius: 10px;
                padding: 7px;
                font: 600 10px 'Segoe UI';
            }
        """)
        layout.addWidget(self.status)
        self.adjustSize()

    def show_experiment_dialog(self, course_name, experiments):
        if self.experiment_dialog is not None:
            self.experiment_dialog.close()

        self.experiment_dialog = ExperimentSelectionDialog(
            course_name, experiments, self
        )
        self.experiment_dialog.experiment_chosen.connect(
            self.experiment_selected.emit
        )
        self.experiment_dialog.show()
        self.experiment_dialog.raise_()
        self.experiment_dialog.activateWindow()

    def close_experiment_dialog(self):
        if self.experiment_dialog is not None:
            self.experiment_dialog.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_positioned", False):
            screen = self.screen() or QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                self.move(
                    area.right() - self.width() - 20,
                    area.bottom() - self.height() - 20
                )
            self._positioned = True

    def set_state(self, state):
        self.state = state
        self.mascot.state = state
        labels = {
            "idle": "Ready! Click me.",
            "listening": "🎤 Listening to you...",
            "thinking": "🧠 Thinking...",
            "speaking": "🤖 Here's my answer!",
            "error": "Something went wrong."
        }
        self.status.setText(labels.get(state, "Ready! Click me."))
        self.mascot.update()

    def show_bubble(self, text, title="LABBUDDY"):
        old_bottom_right = self.frameGeometry().bottomRight()
        self.bubble_title.setText(title)
        self.bubble_text.setText(text)
        self.bubble_frame.show()
        self.adjustSize()
        self.move(
            old_bottom_right.x() - self.width() + 1,
            old_bottom_right.y() - self.height() + 1
        )
        QTimer.singleShot(
            50,
            lambda: self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )
        )

    def show_transcript(self, text):
        self.show_bubble(text, "🎤 YOU ARE SAYING")

    def show_answer(self, text):
        self.show_bubble(text, "🤖 LABBUDDY'S ANSWER")

    def hide_bubble(self):
        old_bottom_right = self.frameGeometry().bottomRight()
        self.bubble_frame.hide()
        self.adjustSize()
        self.move(
            old_bottom_right.x() - self.width() + 1,
            old_bottom_right.y() - self.height() + 1
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.globalPosition().toPoint()
            self.drag_offset = self.press_pos - self.frameGeometry().topLeft()
            self.dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            if (current - self.press_pos).manhattanLength() > 5:
                self.dragging = True
                self.move(current - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self.dragging
        ):
            self.listen_requested.emit()
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        listen_action = menu.addAction("🎤  Listen")
        idle_action = menu.addAction("😴  Idle")
        menu.addSeparator()
        exit_action = menu.addAction("❌  Exit")
        selected = menu.exec(event.globalPos())

        if selected == listen_action:
            self.listen_requested.emit()
        elif selected == idle_action:
            self.idle_requested.emit()
        elif selected == exit_action:
            self.exit_requested.emit()
