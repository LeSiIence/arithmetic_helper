from __future__ import annotations

from PyQt5.QtCore import QPropertyAnimation, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n.localizer import Localizer
from app.services.recognizer_backend import RecognizerBackend
from app.ui.widgets.handwriting_canvas import HandwritingCanvas


_AUTO_RECOGNIZE_DELAY_MS = 800
_AUTO_NEXT_DELAY_MS = 800


class PracticePage(QWidget):
    submit_requested = pyqtSignal(str)
    next_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(
        self,
        localizer: Localizer,
        recognizer: RecognizerBackend | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._recognizer = recognizer
        self._elapsed_seconds = 0
        self._current_index = 0
        self._total_questions = 0
        self._correct_count = 0
        self._answered_count = 0
        self._current_expression = ""
        self._feedback_state: tuple[bool, int] | None = None
        self._recognized_value: int | None = None
        self._auto_flow_active = False
        self._build_ui()
        self.retranslate_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._auto_recognize_timer = QTimer(self)
        self._auto_recognize_timer.setSingleShot(True)
        self._auto_recognize_timer.timeout.connect(self._on_auto_recognize_timeout)

        self._auto_next_timer = QTimer(self)
        self._auto_next_timer.setSingleShot(True)
        self._auto_next_timer.timeout.connect(self._on_auto_next_timeout)

        self._localizer.locale_changed.connect(self.retranslate_ui)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        top_row = QHBoxLayout()
        self.progress_label = QLabel("")
        self.time_label = QLabel("00:00")
        self.progress_label.setProperty("class", "progress")
        self.time_label.setProperty("class", "timer")
        top_row.addWidget(self.progress_label)
        top_row.addStretch()
        top_row.addWidget(self.time_label)
        root.addLayout(top_row)

        self.question_label = QLabel("")
        self.question_label.setProperty("class", "question")
        root.addWidget(self.question_label)

        self.tip_label = QLabel("")
        self.tip_label.setProperty("class", "subtitle")
        root.addWidget(self.tip_label)
        self.canvas = HandwritingCanvas()
        root.addWidget(self.canvas, stretch=3)

        recognized_row = QHBoxLayout()
        self.recognized_label = QLabel("")
        self.recognize_button = QPushButton("")
        self.recognize_button.setMinimumHeight(38)
        recognized_row.addWidget(self.recognized_label)
        recognized_row.addStretch()
        recognized_row.addWidget(self.recognize_button)
        root.addLayout(recognized_row)

        answer_row = QHBoxLayout()
        self.answer_label = QLabel("")
        self.answer_edit = QLineEdit()
        self.answer_edit.setValidator(QIntValidator(0, 999999, self))
        self.answer_edit.setMinimumHeight(40)
        answer_row.addWidget(self.answer_label)
        answer_row.addWidget(self.answer_edit)
        root.addLayout(answer_row)

        self._flash_banner = QLabel("")
        self._flash_banner.setFixedHeight(48)
        self._flash_banner.setAlignment(self.question_label.alignment())
        self._flash_opacity = QGraphicsOpacityEffect(self._flash_banner)
        self._flash_opacity.setOpacity(0.0)
        self._flash_banner.setGraphicsEffect(self._flash_opacity)
        root.addWidget(self._flash_banner)

        self.feedback_label = QLabel("")
        self.feedback_label.setProperty("class", "feedback_correct")
        root.addWidget(self.feedback_label)

        self.score_label = QLabel("")
        self.score_label.setProperty("class", "score")
        root.addWidget(self.score_label)

        button_row = QHBoxLayout()
        self.quit_button = QPushButton("")
        self.clear_button = QPushButton("")
        self.submit_button = QPushButton("")
        self.next_button = QPushButton("")
        self.quit_button.setMinimumHeight(42)
        self.clear_button.setMinimumHeight(42)
        self.submit_button.setMinimumHeight(42)
        self.next_button.setMinimumHeight(42)
        self.next_button.setEnabled(False)
        button_row.addWidget(self.quit_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.submit_button)
        button_row.addWidget(self.next_button)
        root.addLayout(button_row)
        root.addStretch()

        self.quit_button.clicked.connect(self._quit)
        self.clear_button.clicked.connect(self.canvas.clear_canvas)
        self.recognize_button.clicked.connect(self._on_recognize_clicked)
        self.submit_button.clicked.connect(self._submit)
        self.next_button.clicked.connect(self.next_requested.emit)
        self.answer_edit.returnPressed.connect(self._submit)
        self.canvas.drawing_changed.connect(self._on_canvas_drawing_changed)
        self.canvas.stroke_finished.connect(self._on_stroke_finished)


    def retranslate_ui(self) -> None:
        tr = self._localizer.tr
        self.tip_label.setText(tr("practice_canvas_tip"))
        self.recognize_button.setText(tr("btn_recognize"))
        self.answer_label.setText(tr("practice_answer_label"))
        self.answer_edit.setPlaceholderText(tr("practice_answer_placeholder"))
        self.quit_button.setText(tr("btn_quit_session"))
        self.clear_button.setText(tr("btn_clear_canvas"))
        self.submit_button.setText(tr("btn_submit"))
        self.next_button.setText(tr("btn_next"))
        self._refresh_dynamic_text()

    def set_recognizer(self, recognizer: RecognizerBackend | None) -> None:
        """Hot-swap the recognition backend (called from MainWindow)."""
        self._recognizer = recognizer

    def start_timer(self, elapsed_seconds: int = 0) -> None:
        self._elapsed_seconds = elapsed_seconds
        self._update_time_label()
        self._timer.start(1000)

    def stop_timer(self) -> None:
        self._timer.stop()
        self._auto_recognize_timer.stop()
        self._auto_next_timer.stop()

    def show_question(
        self,
        expression: str,
        current: int,
        total: int,
        elapsed_seconds: int,
        correct_count: int,
        answered_count: int,
    ) -> None:
        self._auto_recognize_timer.stop()
        self._auto_next_timer.stop()
        self._auto_flow_active = False
        self._elapsed_seconds = elapsed_seconds
        self._update_time_label()
        self._current_index = current
        self._total_questions = total
        self._current_expression = expression
        self._correct_count = correct_count
        self._answered_count = answered_count
        self._feedback_state = None
        self.answer_edit.clear()
        self.answer_edit.setFocus()
        self.submit_button.setEnabled(True)
        self.next_button.setEnabled(False)
        self.canvas.clear_canvas()
        self._recognized_value = None
        self._refresh_dynamic_text()

    def show_feedback(self, is_correct: bool, correct_answer: int, correct_count: int, answered_count: int) -> None:
        self._feedback_state = (is_correct, correct_answer)
        self._correct_count = correct_count
        self._answered_count = answered_count
        self._refresh_dynamic_text()
        cls = "feedback_correct" if is_correct else "feedback_wrong"
        self.feedback_label.setProperty("class", cls)
        self.feedback_label.style().unpolish(self.feedback_label)
        self.feedback_label.style().polish(self.feedback_label)
        self._play_flash(is_correct)
        self.submit_button.setEnabled(False)
        self.next_button.setEnabled(True)
        if self._auto_flow_active:
            self._auto_next_timer.start(_AUTO_NEXT_DELAY_MS)

    def _play_flash(self, is_correct: bool) -> None:
        color = "#c6f6d5" if is_correct else "#fed7d7"
        icon = "\u2714" if is_correct else "\u2718"
        self._flash_banner.setText(f"  {icon}")
        self._flash_banner.setStyleSheet(
            f"background-color: {color}; border-radius: 8px;"
            f" font-size: 22pt; font-weight: 700;"
            f" color: {'#16a34a' if is_correct else '#dc2626'};"
        )
        anim = QPropertyAnimation(self._flash_opacity, b"opacity", self)
        anim.setDuration(700)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _submit(self) -> None:
        self._auto_recognize_timer.stop()
        self._auto_flow_active = False
        answer = self.answer_edit.text().strip()
        if not answer:
            answer = self._try_recognize_to_answer()
            if not answer:
                QMessageBox.warning(
                    self,
                    self._localizer.tr("warning_title"),
                    self._localizer.tr("warning_enter_answer"),
                )
                return
        self.submit_requested.emit(answer)

    def _quit(self) -> None:
        reply = QMessageBox.question(
            self,
            self._localizer.tr("confirm_quit_title"),
            self._localizer.tr("confirm_quit_message"),
        )
        if reply == QMessageBox.Yes:
            self.stop_timer()
            self.quit_requested.emit()

    def _tick(self) -> None:
        self._elapsed_seconds += 1
        self._update_time_label()

    def _update_time_label(self) -> None:
        minutes, seconds = divmod(self._elapsed_seconds, 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _refresh_dynamic_text(self) -> None:
        tr = self._localizer.tr
        self.progress_label.setText(
            tr("practice_progress", current=self._current_index, total=self._total_questions)
        )
        self.score_label.setText(
            tr("practice_score", correct=self._correct_count, answered=self._answered_count)
        )
        if self._current_expression:
            self.question_label.setText(f"{self._current_expression} = ?")
        else:
            self.question_label.setText(tr("practice_question_placeholder"))
        if self._feedback_state is None:
            self.feedback_label.setText("")
        elif self._feedback_state[0]:
            self.feedback_label.setText(tr("feedback_correct"))
        else:
            self.feedback_label.setText(tr("feedback_wrong", answer=self._feedback_state[1]))

        if self._recognized_value is None:
            self.recognized_label.setText(tr("practice_recognized_empty"))
        else:
            self.recognized_label.setText(
                tr("practice_recognized_value", value=self._recognized_value)
            )

    def _on_recognize_clicked(self) -> None:
        answer = self._try_recognize_to_answer()
        if answer:
            self.answer_edit.setText(answer)
            self.answer_edit.setFocus()
            self.answer_edit.selectAll()
            return
        QMessageBox.information(
            self,
            self._localizer.tr("warning_title"),
            self._localizer.tr("warning_recognition_failed"),
        )

    def _on_canvas_drawing_changed(self) -> None:
        self._auto_recognize_timer.stop()
        self._recognized_value = None
        self.recognized_label.setProperty("class", "recognized")
        self.recognized_label.style().unpolish(self.recognized_label)
        self.recognized_label.style().polish(self.recognized_label)
        self._refresh_dynamic_text()

    def _on_stroke_finished(self) -> None:
        """Restart the auto-recognize countdown after every pen-up."""
        if not self.submit_button.isEnabled():
            return
        self._auto_recognize_timer.start(_AUTO_RECOGNIZE_DELAY_MS)

    def _on_auto_recognize_timeout(self) -> None:
        if not self.submit_button.isEnabled():
            return
        answer = self._try_recognize_to_answer()
        if answer:
            self.answer_edit.setText(answer)
            self._auto_flow_active = True
            self.submit_requested.emit(answer)
            return
        self.canvas.clear_canvas()
        self.recognized_label.setText(self._localizer.tr("auto_recognition_retry"))
        self.recognized_label.setProperty("class", "recognized_warn")
        self.recognized_label.style().unpolish(self.recognized_label)
        self.recognized_label.style().polish(self.recognized_label)

    def _on_auto_next_timeout(self) -> None:
        self._auto_flow_active = False
        self.next_requested.emit()

    def _try_recognize_to_answer(self) -> str:
        if self._recognizer is None:
            return ""
        value = self._recognizer.recognize(self.canvas.to_image())
        self._recognized_value = value
        self._refresh_dynamic_text()
        if value is None:
            return ""
        return str(value)
