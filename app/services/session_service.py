from __future__ import annotations

"""Practice session orchestration service.

Owns session lifecycle state, grading logic, and summary calculation.
"""

from dataclasses import dataclass
from datetime import datetime
from time import monotonic

from app.domain.models import AnswerRecord, PracticeConfig, PracticeQuestion, SessionResult
from app.services.problem_generator import ProblemGenerator


@dataclass(slots=True)
class SubmitResult:
    """Result payload returned immediately after answer submission."""

    is_correct: bool
    correct_answer: int
    answered_count: int
    correct_count: int


class SessionService:
    """Stateful session engine independent from UI layer."""

    def __init__(self, generator: ProblemGenerator) -> None:
        self._generator = generator
        self._config: PracticeConfig | None = None
        self._questions: list[PracticeQuestion] = []
        self._records: list[AnswerRecord] = []
        self._current_index = 0
        self._start_time = 0.0

    def start(self, config: PracticeConfig) -> None:
        """Start a new session and reset previous transient state."""
        self._config = config
        self._questions = self._generator.generate_questions(config)
        self._records = []
        self._current_index = 0
        self._start_time = monotonic()

    @property
    def has_active_session(self) -> bool:
        return self._config is not None and bool(self._questions)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total_questions(self) -> int:
        return len(self._questions)

    @property
    def answered_count(self) -> int:
        return len(self._records)

    @property
    def correct_count(self) -> int:
        return sum(1 for item in self._records if item.is_correct)

    def elapsed_seconds(self) -> int:
        """Elapsed wall-clock seconds since `start`."""
        if self._start_time <= 0:
            return 0
        return int(monotonic() - self._start_time)

    def current_question(self) -> PracticeQuestion:
        """Return current question; requires active session."""
        if not self.has_active_session:
            raise RuntimeError("session not started")
        return self._questions[self._current_index]

    def submit_answer(self, answer_text: str) -> SubmitResult:
        """Validate and grade answer for current question."""
        if not self.has_active_session:
            raise RuntimeError("session not started")
        if self._current_index >= len(self._questions):
            raise RuntimeError("session already complete")
        if not answer_text.strip():
            raise ValueError("empty_answer")

        user_answer = int(answer_text.strip())
        question = self._questions[self._current_index]
        is_correct = user_answer == question.correct_answer
        self._records.append(
            AnswerRecord(
                question=question.expression,
                user_answer=user_answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
            )
        )
        return SubmitResult(
            is_correct=is_correct,
            correct_answer=question.correct_answer,
            answered_count=self.answered_count,
            correct_count=self.correct_count,
        )

    def move_next(self) -> bool:
        """Returns True when there are more questions to answer."""
        if not self.has_active_session:
            return False

        self._current_index += 1
        return self._current_index < len(self._questions)

    def finish(self) -> SessionResult:
        """Finalize current session and return immutable summary."""
        if not self.has_active_session:
            raise RuntimeError("session not started")

        total = self.total_questions
        score = self.correct_count
        accuracy = (score / total * 100.0) if total else 0.0
        result = SessionResult(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username=self._config.username,
            score=score,
            total=total,
            accuracy=accuracy,
            elapsed_seconds=self.elapsed_seconds(),
            details=list(self._records),
        )

        # Keep config for "practice again", clear active question state.
        self._questions = []
        self._records = []
        self._current_index = 0
        self._start_time = 0.0
        return result

    @property
    def current_config(self) -> PracticeConfig | None:
        return self._config
