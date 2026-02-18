from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import SessionResult
from app.i18n.localizer import Localizer


class SummaryPage(QWidget):
    back_to_menu_requested = pyqtSignal()
    view_history_requested = pyqtSignal()

    def __init__(self, localizer: Localizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._last_result: SessionResult | None = None
        self._build_ui()
        self.retranslate_ui()
        self._localizer.locale_changed.connect(self.retranslate_ui)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.result_label = QLabel("")
        self.accuracy_label = QLabel("")
        self.time_label = QLabel("")
        self.result_label.setStyleSheet("font-size: 16pt; font-weight: 700;")
        self.accuracy_label.setStyleSheet("font-size: 14pt;")
        self.time_label.setStyleSheet("font-size: 14pt;")
        root.addWidget(self.title_label)
        root.addWidget(self.result_label)
        root.addWidget(self.accuracy_label)
        root.addWidget(self.time_label)

        self.review_table = QTableWidget(0, 4)
        self.review_table.horizontalHeader().setStretchLastSection(True)
        self.review_table.verticalHeader().setVisible(False)
        self.review_table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.review_table)

        button_row = QHBoxLayout()
        self.back_button = QPushButton("")
        self.history_button = QPushButton("")
        self.back_button.setMinimumHeight(42)
        self.history_button.setMinimumHeight(42)
        button_row.addWidget(self.back_button)
        button_row.addWidget(self.history_button)
        root.addLayout(button_row)

        self.back_button.clicked.connect(self.back_to_menu_requested.emit)
        self.history_button.clicked.connect(self.view_history_requested.emit)
        self.setStyleSheet("QWidget { font-size: 14pt; } QPushButton { padding: 6px 12px; }")

    def retranslate_ui(self) -> None:
        tr = self._localizer.tr
        self.title_label.setText(tr("summary_title"))
        self.review_table.setHorizontalHeaderLabels(
            [
                tr("table_question"),
                tr("table_your_answer"),
                tr("table_correct_answer"),
                tr("table_result"),
            ]
        )
        self.back_button.setText(tr("btn_back_menu"))
        self.history_button.setText(tr("btn_view_history"))
        if self._last_result is not None:
            self.set_result(self._last_result)
        else:
            self.result_label.setText(tr("summary_score", score=0, total=0))
            self.accuracy_label.setText(tr("summary_accuracy", accuracy=0.0))
            self.time_label.setText(tr("summary_time", time="00:00"))

    def set_result(self, result: SessionResult) -> None:
        tr = self._localizer.tr
        self._last_result = result
        self.result_label.setText(tr("summary_score", score=result.score, total=result.total))
        self.accuracy_label.setText(tr("summary_accuracy", accuracy=result.accuracy))
        minutes, seconds = divmod(result.elapsed_seconds, 60)
        self.time_label.setText(tr("summary_time", time=f"{minutes:02d}:{seconds:02d}"))

        self.review_table.setRowCount(len(result.details))
        for row, item in enumerate(result.details):
            status = tr("status_correct") if item.is_correct else tr("status_wrong")
            values = [item.question, str(item.user_answer), str(item.correct_answer), status]
            for col, value in enumerate(values):
                self.review_table.setItem(row, col, QTableWidgetItem(value))
