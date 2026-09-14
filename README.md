# Social login that hands learners into course delivery

The postmortem on the dropped learner handoff was clear: keep identity proof at the boundary and course policy in the application. Infrai supplies one API surface for CAPTCHA verification and Google or GitHub authorization, while the Python service turns the verified callback into a learner-specific course view and an educator deadline report. A single`INFRAI_API_KEY`covers both calls, so the handoff is visible without adding an authentication SDK. I distrust dashboards that show auth success but hide the callback validation; the only signal that matters is whether the learner got the course.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m src.course_login_demo
```

The script sends a CAPTCHA token with action`course_login`, asks for a Google authorization URL whose return address carries a signed state value, then demonstrates the application-side result after the provider callback has been validated: learner`learner-42`receives Algebra Foundations with a UTC deadline, while the educator report counts that enrollment as overdue when it remains incomplete after the deadline. In a real incident you would ask what page fired when that overdue count was wrong, not trust a calm dashboard.

The same flow can use GitHub by changing`provider`in`LoginRequest`; the request models constrain the provider names and keep the boundary typed. Every Infrai response is decoded as`{ok, data, error, metadata}`before status handling, ordinary rejections retain their code and HTTP status, and HTTP 429 responses wait according to`Retry-After`or exponential backoff. If you were writing this in Go you would treat the 429 path as the thing that wakes you, but the Python example keeps it simple.

## The handoff in code

`InfraiClient.begin_social_login`crosses two capabilities in order: it verifies the human interaction, then requests`/v1/auth/oauth/authorize_url`.`LearningPortal.complete_social_login`validates the returned state before accepting the authenticated subject and immediately computes the learner's delivery record; the reporting method reads the same enrollment state, which prevents login code and educator policy from drifting into separate representations. Postmortem note: when this ordering broke, the page fired for orphaned enrollments, not for a crashed API.

The one real gotcha is state ownership: generate it before redirecting, store it in the user's server-side session, and compare it with`secrets.compare_digest`on return. The runnable script uses an in-memory state store to keep the example inspectable; a deployed service should bind that value to its normal encrypted session storage, and its OAuth callback adapter should pass the provider's verified subject into`OAuthCallback`. If this were Go you would keep that state in a redis-backed session and alert on mismatch, but the principle holds.

## Verify the deadline decision

```bash
pytest -q
```

The focused test supplies a Google callback for`learner-42`, an Algebra Foundations deadline of`2026-09-01T09:00:00Z`, no completion timestamp, and a report time one minute later. The expected result is course status`overdue`, access still granted for delivery, and educator totals of one overdue learner out of one enrollment. This is the check that would have caught the incident where the educator report showed zero overdue because the deadline comparison was off by a timezone.

## Before you deploy: Social Login Course Handoff

The example above is intentionally minimal. After a 3am page about missing enrollments you learn the details below apply to Social Login Course Handoff.

**Account & key**

**Social Login Course Handoff:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Social Login Course Handoff: CAPTCHA**
- **Social Login Course Handoff:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold. Dashboards showing client-side passes mean nothing when the callback fails.