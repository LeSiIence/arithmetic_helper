from __future__ import annotations

"""Main application window composition and page routing."""

import logging
import os
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

from app.controllers.practice_controller import PracticeController
from app.i18n.localizer import Localizer
from app.repositories.history_repository import HistoryRepository
from app.services.problem_generator import ProblemGenerator
from app.services.recognizer_backend import RecognizerBackend
from app.services.session_service import SessionService
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.practice_page import PracticePage
from app.ui.pages.setup_page import SetupPage
from app.ui.pages.summary_page import SummaryPage

log = logging.getLogger(__name__)

_GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY", "")
_BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
_BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
_TENCENT_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
_TENCENT_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")


class MainWindow(QMainWindow):
    """Top-level window that wires dependencies and UI navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.localizer = Localizer(default_locale="zh_CN")
        self.setWindowTitle(self.localizer.tr("app_title"))
        self.resize(980, 720)

        self._recognizer_cache: dict[str, RecognizerBackend] = {}

        session_service = SessionService(generator=ProblemGenerator())
        history_repo = HistoryRepository()
        self.controller = PracticeController(
            session_service=session_service,
            history_repo=history_repo,
            localizer=self.localizer,
        )

        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.setup_page = SetupPage(localizer=self.localizer)
        self.practice_page = PracticePage(localizer=self.localizer)
        self.summary_page = SummaryPage(localizer=self.localizer)
        self.history_page = HistoryPage(localizer=self.localizer)

        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.practice_page)
        self.stack.addWidget(self.summary_page)
        self.stack.addWidget(self.history_page)
        self.stack.setCurrentWidget(self.setup_page)

        self._bind_signals()

    # -- Recognizer factory -------------------------------------------------

    def _get_recognizer(self, key: str) -> RecognizerBackend:
        """Return a (cached) recognizer for *key*, creating it on first use."""
        if key not in self._recognizer_cache:
            self._recognizer_cache[key] = self._build_recognizer(key)
        return self._recognizer_cache[key]

    @staticmethod
    def _build_recognizer(key: str) -> RecognizerBackend:
        if key == "google_vision":
            from app.services.google_vision_recognizer import GoogleVisionRecognizer

            return GoogleVisionRecognizer(api_key=_GOOGLE_VISION_API_KEY)
        if key == "baidu_ocr":
            from app.services.baidu_ocr_recognizer import BaiduOcrRecognizer

            return BaiduOcrRecognizer(api_key=_BAIDU_API_KEY, secret_key=_BAIDU_SECRET_KEY)
        if key == "tencent_ocr":
            from app.services.tencent_ocr_recognizer import TencentOcrRecognizer

            return TencentOcrRecognizer(secret_id=_TENCENT_SECRET_ID, secret_key=_TENCENT_SECRET_KEY)
        if key == "tesseract":
            from app.services.tesseract_recognizer import TesseractRecognizer

            return TesseractRecognizer()
        if key == "paddle_ocr":
            from app.services.paddle_ocr_recognizer import PaddleOcrRecognizer

            return PaddleOcrRecognizer()

        from app.services.handwriting_recognizer import HandwritingRecognizer

        return HandwritingRecognizer()

    # -- Signals ------------------------------------------------------------

    def _bind_signals(self) -> None:
        self.setup_page.start_requested.connect(self._on_start_practice)
        self.setup_page.history_requested.connect(self._show_history_page)
        self.setup_page.locale_changed_requested.connect(self.localizer.set_locale)

        self.practice_page.submit_requested.connect(self.controller.submit_answer)
        self.practice_page.next_requested.connect(self.controller.next_question)
        self.practice_page.quit_requested.connect(self._go_to_menu)

        self.summary_page.back_to_menu_requested.connect(self._go_to_menu)
        self.summary_page.view_history_requested.connect(self._show_history_page)

        self.history_page.search_requested.connect(self.controller.load_history)
        self.history_page.back_to_menu_requested.connect(self._go_to_menu)

        self.controller.question_changed.connect(self.practice_page.show_question)
        self.controller.answer_checked.connect(self.practice_page.show_feedback)
        self.controller.session_finished.connect(self._on_session_finished)
        self.controller.history_loaded.connect(self._on_history_loaded)
        self.controller.error_raised.connect(self._show_error)
        self.localizer.locale_changed.connect(self._on_locale_changed)

    # -- Navigation ---------------------------------------------------------

    def _on_start_practice(self, config) -> None:
        key = self.setup_page.selected_recognizer_key()
        recognizer = self._get_recognizer(key)
        if not recognizer.available:
            QMessageBox.warning(
                self,
                self.localizer.tr("warning_title"),
                self.localizer.tr("warning_backend_unavailable", backend=recognizer.name),
            )
            return
        self.practice_page.set_recognizer(recognizer)
        log.info("Using recognizer backend: %s", recognizer.name)
        self.controller.start_practice(config)
        self.stack.setCurrentWidget(self.practice_page)
        self.practice_page.start_timer()

    def _on_session_finished(self, session) -> None:
        self.practice_page.stop_timer()
        self.summary_page.set_result(session)
        self.stack.setCurrentWidget(self.summary_page)

    def _show_history_page(self) -> None:
        self.controller.load_history(self.history_page.filter_edit.text().strip())
        self.stack.setCurrentWidget(self.history_page)

    def _on_history_loaded(self, sessions, name_filter: str) -> None:
        self.history_page.set_history(sessions, name_filter)

    def _go_to_menu(self) -> None:
        self.practice_page.stop_timer()
        self.stack.setCurrentWidget(self.setup_page)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, self.localizer.tr("warning_title"), message)

    def _on_locale_changed(self, _: str) -> None:
        self.setWindowTitle(self.localizer.tr("app_title"))


def run_app() -> None:
    """Application bootstrap entrypoint used by ``main.py``."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
