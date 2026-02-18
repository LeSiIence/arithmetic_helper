from __future__ import annotations

"""Controller layer bridging UI events and business services."""

from PyQt5.QtCore import QObject, pyqtSignal

from app.domain.models import PracticeConfig, SessionResult
from app.i18n.localizer import Localizer
from app.repositories.history_repository import HistoryRepository
from app.services.session_service import SessionService


class PracticeController(QObject):
    """Translate UI actions into service calls and emit UI-friendly signals."""

    question_changed = pyqtSignal(str, int, int, int, int, int)
    answer_checked = pyqtSignal(bool, int, int, int)
    session_finished = pyqtSignal(object)
    history_loaded = pyqtSignal(object, str)
    error_raised = pyqtSignal(str)

    def __init__(
        self,
        session_service: SessionService,
        history_repo: HistoryRepository,
        localizer: Localizer,
    ) -> None:
        super().__init__()
        self._session_service = session_service
        self._history_repo = history_repo
        self._localizer = localizer
        self._last_config: PracticeConfig | None = None

    @property
    def last_config(self) -> PracticeConfig | None:
        return self._last_config

    def start_practice(self, config: PracticeConfig) -> None:
        """Create a session and publish the first question."""
        try:
            self._session_service.start(config)
        except Exception as exc:  # pragma: no cover - UI error path
            self.error_raised.emit(self._localizer.tr("error_start_failed", error=str(exc)))
            return
        self._last_config = config
        self._emit_current_question()

    def submit_answer(self, answer_text: str) -> None:
        """Grade current answer and emit result state for UI rendering."""
        try:
            result = self._session_service.submit_answer(answer_text)
        except ValueError as exc:
            if str(exc) == "empty_answer":
                self.error_raised.emit(self._localizer.tr("error_empty_answer"))
            else:
                self.error_raised.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - UI error path
            self.error_raised.emit(self._localizer.tr("error_submit_failed", error=str(exc)))
            return

        self.answer_checked.emit(
            result.is_correct,
            result.correct_answer,
            result.correct_count,
            result.answered_count,
        )

    def next_question(self) -> None:
        """Advance to next question or finish and persist current session."""
        has_more = self._session_service.move_next()
        if has_more:
            self._emit_current_question()
            return

        try:
            session = self._session_service.finish()
            self._history_repo.save_session(session)
            self.session_finished.emit(session)
        except Exception as exc:  # pragma: no cover - UI error path
            self.error_raised.emit(self._localizer.tr("error_finish_failed", error=str(exc)))

    def load_history(self, name_filter: str = "") -> None:
        """Query historical records and pass them to presentation layer."""
        try:
            history = self._history_repo.load_sessions(name_filter=name_filter)
            self.history_loaded.emit(history, name_filter.strip())
        except Exception as exc:  # pragma: no cover - UI error path
            self.error_raised.emit(self._localizer.tr("error_load_failed", error=str(exc)))

    def _emit_current_question(self) -> None:
        """Emit a normalized question payload for the practice page."""
        question = self._session_service.current_question()
        self.question_changed.emit(
            question.expression,
            self._session_service.current_index + 1,
            self._session_service.total_questions,
            self._session_service.elapsed_seconds(),
            self._session_service.correct_count,
            self._session_service.answered_count,
        )
