from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict


class OAuthCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["google", "github"]
    subject: str
    state: str


class Enrollment(BaseModel):
    learner_id: str
    course_id: str
    course_title: str
    deadline: datetime
    completed_at: datetime | None = None


class CourseDelivery(BaseModel):
    learner_id: str
    course_id: str
    course_title: str
    deadline: datetime
    status: Literal["open", "completed", "overdue"]
    access_granted: bool


class EducatorReport(BaseModel):
    course_id: str
    enrolled: int
    completed: int
    overdue: int


class LearningPortal:
    def __init__(self, enrollments: list[Enrollment]) -> None:
        self._enrollments = enrollments
        self._states: set[str] = set()

    def issue_state(self) -> str:
        state = secrets.token_urlsafe(32)
        self._states.add(state)
        return state

    def complete_social_login(self, callback: OAuthCallback, now: datetime) -> list[CourseDelivery]:
        matched = next((value for value in self._states if secrets.compare_digest(value, callback.state)), None)
        if matched is None:
            raise ValueError("OAuth state did not match the active login")
        self._states.remove(matched)
        return [self._delivery(item, now) for item in self._enrollments if item.learner_id == callback.subject]

    def educator_report(self, course_id: str, now: datetime) -> EducatorReport:
        rows = [item for item in self._enrollments if item.course_id == course_id]
        completed = sum(item.completed_at is not None for item in rows)
        overdue = sum(item.completed_at is None and self._utc(item.deadline) < self._utc(now) for item in rows)
        return EducatorReport(course_id=course_id, enrolled=len(rows), completed=completed, overdue=overdue)

    @classmethod
    def _delivery(cls, enrollment: Enrollment, now: datetime) -> CourseDelivery:
        if enrollment.completed_at is not None:
            status = "completed"
        elif cls._utc(enrollment.deadline) < cls._utc(now):
            status = "overdue"
        else:
            status = "open"
        return CourseDelivery(**enrollment.model_dump(exclude={"completed_at"}), status=status, access_granted=True)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("deadlines must include a timezone")
        return value.astimezone(timezone.utc)

