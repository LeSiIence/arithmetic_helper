from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# 历史列表：按正确率着色（≥80% 绿 / ≥60% 黄 / <60% 红）
_HISTORY_ACCURACY_HIGH_BG = QColor("#c6f6d5")
_HISTORY_ACCURACY_HIGH_FG = QColor("#166534")
_HISTORY_ACCURACY_MID_BG = QColor("#fefce8")
_HISTORY_ACCURACY_MID_FG = QColor("#854d0e")
_HISTORY_ACCURACY_LOW_BG = QColor("#fed7d7")
_HISTORY_ACCURACY_LOW_FG = QColor("#991b1b")

# 历史详情弹窗：按题目对错着色
_DETAIL_CORRECT_BG = QColor("#c6f6d5")
_DETAIL_CORRECT_FG = QColor("#166534")
_DETAIL_WRONG_BG = QColor("#fed7d7")
_DETAIL_WRONG_FG = QColor("#991b1b")

from app.domain.models import SessionResult
from app.i18n.localizer import Localizer


class _ColoredItemDelegate(QStyledItemDelegate):
    """Manually paints per-item BackgroundRole / ForegroundRole colors,
    bypassing qt_material's application-level stylesheet overrides."""

    def paint(self, painter, option, index):
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            bg = index.data(Qt.BackgroundRole)
            if isinstance(bg, QBrush) and bg.style() != Qt.NoBrush:
                painter.fillRect(option.rect, bg)

        text = index.data(Qt.DisplayRole)
        if text is not None:
            if option.state & QStyle.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                fg = index.data(Qt.ForegroundRole)
                if isinstance(fg, QBrush):
                    painter.setPen(fg.color())
                else:
                    painter.setPen(option.palette.text().color())
            text_rect = option.rect.adjusted(6, 0, -6, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, str(text))

        painter.restore()


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
        self.title_label.setProperty("class", "page_title")
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
        self.table.setItemDelegate(_ColoredItemDelegate(self.table))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table)

        self.summary_label = QLabel("")
        self.summary_label.setProperty("class", "summary_stat")
        root.addWidget(self.summary_label)

        self.search_button.clicked.connect(self._emit_search)
        self.filter_edit.returnPressed.connect(self._emit_search)
        self.back_button.clicked.connect(self.back_to_menu_requested.emit)

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
            # 历史记录行着色：按正确率整行着色（≥80% 绿 / ≥60% 黄 / <60% 红）
            score_text = f"{item.score} / {item.total}"
            values = [
                item.timestamp,
                item.username,
                score_text,
                f"{item.accuracy:.2f}%",
                self._format_seconds(item.elapsed_seconds),
            ]
            bg, fg = self._accuracy_colors(item.accuracy)
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setBackground(QBrush(bg))
                cell.setForeground(QBrush(fg))
                self.table.setItem(row, col, cell)

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
        dialog.resize(720, 520)
        dialog.setStyleSheet(
            "QDialog { background: palette(window); } "
            "QFrame#detailHeader { "
            "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f0f9ff, stop:1 #e0f2fe); "
            "  border: 1px solid #bae6fd; border-radius: 10px; "
            "  padding: 12px; "
            "} "
            "QLabel[class=\"detailStat\"] { font-size: 13pt; font-weight: 600; color: #0c4a6e; } "
            "QLabel[class=\"detailStatValue\"] { font-size: 14pt; font-weight: 700; color: #0369a1; } "
            "QTableWidget { gridline-color: #e2e8f0; border-radius: 6px; } "
            "QTableWidget::item { padding: 6px; } "
        )

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)

        header = QFrame(dialog)
        header.setObjectName("detailHeader")
        header_layout = QGridLayout(header)
        header_layout.setSpacing(8)
        header_layout.addWidget(self._detail_stat_label(tr("table_date")), 0, 0)
        header_layout.addWidget(self._detail_value_label(session.timestamp), 0, 1)
        header_layout.addWidget(self._detail_stat_label(tr("table_score")), 1, 0)
        header_layout.addWidget(self._detail_value_label(f"{session.score} / {session.total}"), 1, 1)
        header_layout.addWidget(self._detail_stat_label(tr("table_accuracy")), 2, 0)
        header_layout.addWidget(self._detail_value_label(f"{session.accuracy:.2f}%"), 2, 1)
        header_layout.addWidget(self._detail_stat_label(tr("table_time")), 3, 0)
        header_layout.addWidget(self._detail_value_label(self._format_seconds(session.elapsed_seconds)), 3, 1)
        layout.addWidget(header)

        table = QTableWidget(0, 4)
        table.setItemDelegate(_ColoredItemDelegate(table))
        table.setHorizontalHeaderLabels([
            tr("table_question"),
            tr("table_your_answer"),
            tr("table_correct_answer"),
            tr("table_result"),
        ])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(False)

        if session.details:
            table.setRowCount(len(session.details))
            for r, item in enumerate(session.details):
                # 历史详情逐题着色：对=绿，错=红
                status = tr("status_correct") if item.is_correct else tr("status_wrong")
                bg = QBrush(_DETAIL_CORRECT_BG if item.is_correct else _DETAIL_WRONG_BG)
                fg = QBrush(_DETAIL_CORRECT_FG if item.is_correct else _DETAIL_WRONG_FG)
                for c, value in enumerate([item.question, str(item.user_answer), str(item.correct_answer), status]):
                    cell = QTableWidgetItem(value)
                    cell.setBackground(bg)
                    cell.setForeground(fg)
                    table.setItem(r, c, cell)
        else:
            table.setRowCount(1)
            cell = QTableWidgetItem(tr("detail_none"))
            table.setItem(0, 0, cell)
            table.setSpan(0, 0, 1, 4)

        layout.addWidget(table)

        close_btn = QPushButton(tr("btn_close"))
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec_()

    def _detail_stat_label(self, text: str) -> QLabel:
        label = QLabel(text + ":")
        label.setProperty("class", "detailStat")
        return label

    def _detail_value_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("class", "detailStatValue")
        return label

    @staticmethod
    def _accuracy_colors(accuracy: float) -> tuple[QColor, QColor]:
        """历史记录行着色：≥80% 绿，≥60% 黄，<60% 红。"""
        if accuracy >= 80:
            return _HISTORY_ACCURACY_HIGH_BG, _HISTORY_ACCURACY_HIGH_FG
        if accuracy >= 60:
            return _HISTORY_ACCURACY_MID_BG, _HISTORY_ACCURACY_MID_FG
        return _HISTORY_ACCURACY_LOW_BG, _HISTORY_ACCURACY_LOW_FG

    @staticmethod
    def _format_seconds(total_seconds: int) -> str:
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
