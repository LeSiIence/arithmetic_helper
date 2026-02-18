from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import SessionResult
from app.i18n.localizer import Localizer


class HistoryPage(QWidget):
    back_to_menu_requested = pyqtSignal()
    search_requested = pyqtSignal(str)

    def __init__(self, localizer: Localizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._sessions: list[SessionResult] = []
        self._current_filter = ""
        self._build_ui()
        self.retranslate_ui()
        self._localizer.locale_changed.connect(self.retranslate_ui)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        root.addWidget(self.title_label)

        filter_row = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setMinimumHeight(38)
        self.search_button = QPushButton("")
        self.back_button = QPushButton("")
        self.search_button.setMinimumHeight(38)
        self.back_button.setMinimumHeight(38)
        filter_row.addWidget(self.filter_edit)
        filter_row.addWidget(self.search_button)
        filter_row.addWidget(self.back_button)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 6)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 14pt; color: #374151;")
        root.addWidget(self.summary_label)

        self.search_button.clicked.connect(self._emit_search)
        self.filter_edit.returnPressed.connect(self._emit_search)
        self.back_button.clicked.connect(self.back_to_menu_requested.emit)
        self.setStyleSheet("QWidget { font-size: 14pt; } QPushButton { padding: 6px 12px; }")

    def retranslate_ui(self) -> None:
        tr = self._localizer.tr
        self.title_label.setText(tr("history_title"))
        self.filter_edit.setPlaceholderText(tr("history_filter_placeholder"))
        self.search_button.setText(tr("btn_search"))
        self.back_button.setText(tr("btn_back_menu"))
        self.table.setHorizontalHeaderLabels(
            [
                tr("table_date"),
                tr("table_name"),
                tr("table_score"),
                tr("table_accuracy"),
                tr("table_time"),
                tr("table_details"),
            ]
        )
        self.set_history(self._sessions, self._current_filter)

    def set_history(self, sessions: list[SessionResult], name_filter: str) -> None:
        tr = self._localizer.tr
        self._sessions = sessions
        self._current_filter = name_filter
        self.table.setRowCount(len(sessions))
        for row, item in enumerate(sessions):
            score_text = f"{item.score} / {item.total}"
            values = [
                item.timestamp,
                item.username,
                score_text,
                f"{item.accuracy:.2f}%",
                self._format_seconds(item.elapsed_seconds),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

            detail_button = QPushButton(tr("btn_view"))
            detail_button.clicked.connect(lambda _, idx=row: self._show_details(idx))
            self.table.setCellWidget(row, 5, detail_button)

        if sessions:
            avg = sum(item.accuracy for item in sessions) / len(sessions)
            name_title = name_filter if name_filter else tr("history_summary_all")
            self.summary_label.setText(
                tr("history_summary_stats", name=name_title, count=len(sessions), accuracy=avg)
            )
        else:
            self.summary_label.setText(tr("history_summary_empty"))

    def _emit_search(self) -> None:
        self.search_requested.emit(self.filter_edit.text().strip())

    def _show_details(self, row: int) -> None:
        if row < 0 or row >= len(self._sessions):
            return
        session = self._sessions[row]
        tr = self._localizer.tr

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("detail_window_title", username=session.username))
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        info = QLabel(
            tr(
                "detail_info",
                timestamp=session.timestamp,
                score=session.score,
                total=session.total,
                accuracy=session.accuracy,
                time=self._format_seconds(session.elapsed_seconds),
            )
        )
        info.setStyleSheet("font-size: 13pt;")
        layout.addWidget(info)

        text = QTextEdit()
        text.setReadOnly(True)
        lines = []
        for i, detail in enumerate(session.details, start=1):
            status = tr("status_correct") if detail.is_correct else tr("status_wrong")
            lines.append(
                tr(
                    "detail_line",
                    index=i,
                    question=detail.question,
                    correct=detail.correct_answer,
                    answer=detail.user_answer,
                    status=status,
                )
            )
        text.setPlainText("\n".join(lines) if lines else tr("detail_none"))
        layout.addWidget(text)

        close_button = QPushButton(tr("btn_close"))
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec_()

    @staticmethod
    def _format_seconds(total_seconds: int) -> str:
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
