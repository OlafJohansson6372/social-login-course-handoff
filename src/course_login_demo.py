from __future__ import annotations

import json
from datetime import datetime, timezone

from .course_delivery import Enrollment, LearningPortal, OAuthCallback
from .infrai_social_login import InfraiClient, LoginRequest


def main() -> None:
    portal = LearningPortal(
        [
            Enrollment(
                learner_id="learner-42",
                course_id="algebra-foundations",
                course_title="Algebra Foundations",
                deadline=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            )
        ]
    )
    state = portal.issue_state()
    start = InfraiClient.from_environment().begin_social_login(
        LoginRequest(
            provider="google",
            widget_record_id="widget-record-from-browser",
            captcha_token="token-from-browser-widget",
            return_to="http://localhost:8000/courses",
            redirect_uri="http://localhost:8000/oauth/callback",
        ),
        state,
    )
    print(json.dumps({"open_in_browser": start.authorization_url}, indent=2))

    # The callback adapter supplies the provider-verified subject after checking its response.
    callback = OAuthCallback(provider="google", subject="learner-42", state=start.state)
    now = datetime(2026, 9, 1, 9, 1, tzinfo=timezone.utc)
    deliveries = portal.complete_social_login(callback, now)
    report = portal.educator_report("algebra-foundations", now)
    print(json.dumps({"courses": [row.model_dump(mode="json") for row in deliveries], "report": report.model_dump()}, indent=2))


if __name__ == "__main__":
    main()
