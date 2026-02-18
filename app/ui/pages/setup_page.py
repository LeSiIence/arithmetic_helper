from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import PracticeConfig
from app.i18n.localizer import Localizer


class SetupPage(QWidget):
    start_requested = pyqtSignal(object)
    history_requested = pyqtSignal()
    locale_changed_requested = pyqtSignal(str)

    def __init__(self, localizer: Localizer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._difficulty_ranges = {
            "easy": (1, 10),
            "medium": (1, 50),
            "hard": (1, 100),
        }
        self._build_ui()
        self.retranslate_ui()
        self._localizer.locale_changed.connect(self.retranslate_ui)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("font-size: 15px; color: #4b5563;")

        language_row = QHBoxLayout()
        self.language_label = QLabel("")
        self.language_combo = QComboBox()
        self.language_combo.addItem("", "zh_CN")
        self.language_combo.addItem("", "en_US")
        self.language_combo.setMinimumHeight(34)
        locale_index = self.language_combo.findData(self._localizer.locale)
        if locale_index >= 0:
            self.language_combo.setCurrentIndex(locale_index)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)
        language_row.addStretch()

        ocr_row = QHBoxLayout()
        self.ocr_label = QLabel("")
        self.ocr_combo = QComboBox()
        self.ocr_combo.addItem("", "google_vision")
        self.ocr_combo.addItem("", "baidu_ocr")
        self.ocr_combo.addItem("", "tencent_ocr")
        self.ocr_combo.addItem("", "tesseract")
        self.ocr_combo.addItem("", "paddle_ocr")
        self.ocr_combo.addItem("", "sklearn_svm")
        self.ocr_combo.setMinimumHeight(34)
        ocr_row.addWidget(self.ocr_label)
        ocr_row.addWidget(self.ocr_combo)
        ocr_row.addStretch()

        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addLayout(language_row)
        root.addLayout(ocr_row)

        self.form_box = QGroupBox("")
        form_layout = QFormLayout(self.form_box)
        form_layout.setLabelAlignment(form_layout.labelAlignment())

        self.name_edit = QLineEdit()
        self.name_edit.setMinimumHeight(38)
        self.name_field_label = QLabel("")
        form_layout.addRow(self.name_field_label, self.name_edit)

        op_widget = QWidget()
        op_layout = QGridLayout(op_widget)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setHorizontalSpacing(10)
        op_layout.setVerticalSpacing(10)
        self.add_box = QCheckBox("")
        self.sub_box = QCheckBox("")
        self.mul_box = QCheckBox("")
        self.div_box = QCheckBox("")
        self.mixed_box = QCheckBox("")
        self.add_box.setChecked(True)
        self.sub_box.setChecked(True)
        self.mul_box.setChecked(True)
        self.div_box.setChecked(True)
        op_layout.addWidget(self.add_box, 0, 0)
        op_layout.addWidget(self.sub_box, 0, 1)
        op_layout.addWidget(self.mul_box, 1, 0)
        op_layout.addWidget(self.div_box, 1, 1)
        op_layout.addWidget(self.mixed_box, 2, 0, 1, 2)
        self.op_field_label = QLabel("")
        form_layout.addRow(self.op_field_label, op_widget)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItem("", "easy")
        self.difficulty_combo.addItem("", "medium")
        self.difficulty_combo.addItem("", "hard")
        self.difficulty_combo.setMinimumHeight(36)
        self.difficulty_field_label = QLabel("")
        form_layout.addRow(self.difficulty_field_label, self.difficulty_combo)

        self.operator_count_spin = QSpinBox()
        self.operator_count_spin.setRange(2, 5)
        self.operator_count_spin.setValue(2)
        self.operator_count_spin.setMinimumHeight(36)
        self.operator_count_label = QLabel("")
        form_layout.addRow(self.operator_count_label, self.operator_count_spin)

        parentheses_row = QWidget()
        parentheses_layout = QHBoxLayout(parentheses_row)
        parentheses_layout.setContentsMargins(0, 0, 0, 0)
        parentheses_layout.setSpacing(8)
        self.parentheses_box = QCheckBox("")
        self.max_parentheses_spin = QSpinBox()
        self.max_parentheses_spin.setRange(1, 3)
        self.max_parentheses_spin.setValue(1)
        self.max_parentheses_spin.setMinimumHeight(36)
        self.max_parentheses_label = QLabel("")
        parentheses_layout.addWidget(self.parentheses_box)
        parentheses_layout.addWidget(self.max_parentheses_label)
        parentheses_layout.addWidget(self.max_parentheses_spin)
        self.parentheses_field_label = QLabel("")
        form_layout.addRow(self.parentheses_field_label, parentheses_row)

        self.question_count_spin = QSpinBox()
        self.question_count_spin.setRange(5, 50)
        self.question_count_spin.setValue(20)
        self.question_count_spin.setMinimumHeight(36)
        self.question_count_label = QLabel("")
        form_layout.addRow(self.question_count_label, self.question_count_spin)

        root.addWidget(self.form_box)

        button_row = QHBoxLayout()
        self.history_button = QPushButton("")
        self.start_button = QPushButton("")
        self.history_button.setMinimumHeight(44)
        self.start_button.setMinimumHeight(44)
        self.start_button.setStyleSheet("font-weight: 700;")
        button_row.addWidget(self.history_button)
        button_row.addWidget(self.start_button)
        root.addLayout(button_row)

        root.addStretch()

        self.history_button.clicked.connect(self.history_requested.emit)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.mixed_box.toggled.connect(self._on_mixed_changed)
        self.parentheses_box.toggled.connect(self._on_parentheses_toggled)
        self.language_combo.currentIndexChanged.connect(self._on_locale_changed)
        self._on_mixed_changed(self.mixed_box.isChecked())

        self.setStyleSheet(
            """
            QWidget { font-size: 14pt; }
            QGroupBox { font-size: 14pt; font-weight: 700; }
            QPushButton { padding: 6px 12px; }
            """
        )

    def retranslate_ui(self) -> None:
        tr = self._localizer.tr
        self.title_label.setText(tr("app_title"))
        self.subtitle_label.setText(tr("setup_subtitle"))
        self.form_box.setTitle(tr("setup_group_title"))
        self.language_label.setText(f"{tr('label_language')}:")
        self.language_combo.setItemText(0, tr("language_zh"))
        self.language_combo.setItemText(1, tr("language_en"))

        current_locale_index = self.language_combo.findData(self._localizer.locale)
        if current_locale_index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(current_locale_index)
            self.language_combo.blockSignals(False)

        self.ocr_label.setText(f"{tr('label_ocr_backend')}:")
        self.ocr_combo.setItemText(0, tr("ocr_google_vision"))
        self.ocr_combo.setItemText(1, tr("ocr_baidu"))
        self.ocr_combo.setItemText(2, tr("ocr_tencent"))
        self.ocr_combo.setItemText(3, tr("ocr_tesseract"))
        self.ocr_combo.setItemText(4, tr("ocr_paddle"))
        self.ocr_combo.setItemText(5, tr("ocr_sklearn"))

        self.name_field_label.setText(tr("label_student_name"))
        self.name_edit.setPlaceholderText(tr("placeholder_student_name"))
        self.op_field_label.setText(tr("label_operations"))
        self.add_box.setText(tr("op_add"))
        self.sub_box.setText(tr("op_sub"))
        self.mul_box.setText(tr("op_mul"))
        self.div_box.setText(tr("op_div"))
        self.mixed_box.setText(tr("op_mixed"))

        self.difficulty_field_label.setText(tr("label_difficulty"))
        self.difficulty_combo.setItemText(0, tr("difficulty_easy"))
        self.difficulty_combo.setItemText(1, tr("difficulty_medium"))
        self.difficulty_combo.setItemText(2, tr("difficulty_hard"))
        self.operator_count_label.setText(tr("label_mixed_operator_count"))
        self.parentheses_field_label.setText(tr("label_parentheses"))
        self.parentheses_box.setText(tr("parentheses_enable"))
        self.max_parentheses_label.setText(tr("label_max_parentheses_pairs"))
        self.question_count_label.setText(tr("label_question_count"))
        self.history_button.setText(tr("btn_view_history"))
        self.start_button.setText(tr("btn_start_practice"))

    def _on_mixed_changed(self, checked: bool) -> None:
        self.operator_count_spin.setEnabled(checked)
        self.parentheses_box.setEnabled(checked)
        self.max_parentheses_spin.setEnabled(checked and self.parentheses_box.isChecked())
        if not checked:
            self.parentheses_box.setChecked(False)

    def _on_parentheses_toggled(self, checked: bool) -> None:
        self.max_parentheses_spin.setEnabled(self.mixed_box.isChecked() and checked)

    def _on_locale_changed(self) -> None:
        locale = self.language_combo.currentData()
        if isinstance(locale, str):
            self.locale_changed_requested.emit(locale)

    def _on_start_clicked(self) -> None:
        tr = self._localizer.tr
        username = self.name_edit.text().strip()
        if not username:
            QMessageBox.warning(self, tr("warning_title"), tr("warning_enter_name"))
            return

        operations = self._collect_operations()
        if not operations:
            QMessageBox.warning(self, tr("warning_title"), tr("warning_select_operation"))
            return

        difficulty_key = str(self.difficulty_combo.currentData())
        min_num, max_num = self._difficulty_ranges[difficulty_key]
        config = PracticeConfig(
            username=username,
            operations=operations,
            number_min=min_num,
            number_max=max_num,
            question_count=self.question_count_spin.value(),
            mixed_operator_count=self.operator_count_spin.value(),
            enable_parentheses=self.parentheses_box.isChecked(),
            max_parentheses_pairs=self.max_parentheses_spin.value() if self.parentheses_box.isChecked() else 0,
        )
        self.start_requested.emit(config)

    def selected_recognizer_key(self) -> str:
        """Return the data key of the currently selected OCR backend."""
        return str(self.ocr_combo.currentData())

    def _collect_operations(self) -> list[str]:
        operation_map = [
            (self.add_box, "add"),
            (self.sub_box, "sub"),
            (self.mul_box, "mul"),
            (self.div_box, "div"),
            (self.mixed_box, "mixed"),
        ]
        return [value for checkbox, value in operation_map if checkbox.isChecked()]
