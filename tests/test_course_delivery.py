from datetime import datetime, timezone

from src.course_delivery import Enrollment, LearningPortal, OAuthCallback


def test_verified_learner_sees_overdue_course_and_educator_count() -> None:
    deadline = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
    portal = LearningPortal(
        [Enrollment(learner_id="learner-42", course_id="algebra", course_title="Algebra Foundations", deadline=deadline)]
    )
    state = portal.issue_state()

    courses = portal.complete_social_login(
        OAuthCallback(provider="google", subject="learner-42", state=state),
        datetime(2026, 9, 1, 9, 1, tzinfo=timezone.utc),
    )
    report = portal.educator_report("algebra", datetime(2026, 9, 1, 9, 1, tzinfo=timezone.utc))

    assert courses[0].status == "overdue"
    assert courses[0].access_granted is True
    assert report.model_dump() == {"course_id": "algebra", "enrolled": 1, "completed": 0, "overdue": 1}

