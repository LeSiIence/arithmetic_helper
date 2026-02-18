from __future__ import annotations

"""CSV-backed repository for session history."""

import csv
import json
from pathlib import Path

from app.domain.models import AnswerRecord, SessionResult


class HistoryRepository:
    """Persist and query `SessionResult` records from local CSV file."""

    def __init__(self, csv_path: Path | None = None) -> None:
        self._csv_path = csv_path or Path("data/history.csv")
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._headers = [
            "timestamp",
            "username",
            "score",
            "total",
            "accuracy",
            "elapsed_seconds",
            "details_json",
        ]
        if not self._csv_path.exists():
            with self._csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self._headers)
                writer.writeheader()

    def save_session(self, session: SessionResult) -> None:
        """Append one finished session as a single CSV row."""
        row = {
            "timestamp": session.timestamp,
            "username": session.username,
            "score": session.score,
            "total": session.total,
            "accuracy": f"{session.accuracy:.2f}",
            "elapsed_seconds": session.elapsed_seconds,
            "details_json": json.dumps([item.to_dict() for item in session.details], ensure_ascii=False),
        }
        with self._csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self._headers)
            writer.writerow(row)

    def load_sessions(self, name_filter: str = "") -> list[SessionResult]:
        """Load sessions, optionally filtered by case-insensitive name match."""
        if not self._csv_path.exists():
            return []

        normalized = name_filter.strip().lower()
        sessions: list[SessionResult] = []
        with self._csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                username = str(row.get("username", ""))
                if normalized and normalized not in username.lower():
                    continue

                raw_details = row.get("details_json", "[]")
                try:
                    details_data = json.loads(raw_details) if raw_details else []
                except json.JSONDecodeError:
                    details_data = []

                details = [AnswerRecord.from_dict(item) for item in details_data]
                sessions.append(
                    SessionResult(
                        timestamp=str(row.get("timestamp", "")),
                        username=username,
                        score=int(row.get("score", 0)),
                        total=int(row.get("total", 0)),
                        accuracy=float(row.get("accuracy", 0.0)),
                        elapsed_seconds=int(row.get("elapsed_seconds", 0)),
                        details=details,
                    )
                )

        sessions.sort(key=lambda item: item.timestamp, reverse=True)
        return sessions
