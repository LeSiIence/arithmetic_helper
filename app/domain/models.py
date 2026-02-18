from __future__ import annotations

"""Core domain data models shared across layers.

These dataclasses are intentionally UI-agnostic and persistence-agnostic.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class PracticeConfig:
    """User-selected configuration for one practice session."""

    username: str
    operations: list[str]
    number_min: int
    number_max: int
    question_count: int
    mixed_operator_count: int = 2
    enable_parentheses: bool = False
    max_parentheses_pairs: int = 0


@dataclass(slots=True)
class PracticeQuestion:
    """Generated question and its integer ground-truth answer."""

    expression: str
    correct_answer: int


@dataclass(slots=True)
class AnswerRecord:
    """One answered question in a finished or in-progress session."""

    question: str
    user_answer: Optional[int]
    correct_answer: int
    is_correct: bool

    def to_dict(self) -> dict:
        """Serialize to plain dict for CSV JSON column storage."""
        return {
            "question": self.question,
            "user_answer": self.user_answer,
            "correct_answer": self.correct_answer,
            "is_correct": self.is_correct,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnswerRecord":
        """Deserialize from repository payload with defensive defaults."""
        return cls(
            question=str(data.get("question", "")),
            user_answer=data.get("user_answer"),
            correct_answer=int(data.get("correct_answer", 0)),
            is_correct=bool(data.get("is_correct", False)),
        )


@dataclass(slots=True)
class SessionResult:
    """Final summary of a completed session for reporting and persistence."""

    timestamp: str
    username: str
    score: int
    total: int
    accuracy: float
    elapsed_seconds: int
    details: list[AnswerRecord] = field(default_factory=list)
