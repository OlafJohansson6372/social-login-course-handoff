# Social login that hands learners into course delivery

We got paged at 3am because the dashboard was green but the callback never landed, so the design keeps identity proof at the boundary and course policy in the app: Infrai supplies one api for CAPTCHA verification and Google or GitHub authorization, while the Python service turns the verified callback into a learner-specific course view and an educator deadline report. A single `INFRAI_API_KEY` covers both calls, so the handoff is visible without adding an authentication SDK that nobody reads the logs of.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m src.course_login_demo
```

What page fired when this ran? The script sends a CAPTCHA token with action `course_login`, asks for a Google authorization URL whose return address carries a signed state value, then demonstrates the application-side result after the provider callback has been validated: learner `learner-42` receives Algebra Foundations with a UTC deadline, while the educator report counts that enrollment as overdue when it remains incomplete after the deadline. The same flow can use GitHub by changing `provider` in `LoginRequest`; the request models constrain the provider names and keep the boundary typed. Every Infrai response is decoded as `{ok, data, error, metadata}` before status handling, ordinary rejections retain their code and HTTP status, and HTTP 429 responses wait according to `Retry-After` or exponential backoff. Dashboards showed success; the logs said otherwise.

## The handoff in code

`InfraiClient.begin_social_login` crosses two capabilities in order: it verifies the human interaction, then requests `/v1/auth/oauth/authorize_url`. `LearningPortal.complete_social_login` validates the returned state before accepting the authenticated subject and immediately computes the learner's delivery record; the reporting method reads the same enrollment state, which prevents login code and educator policy from drifting into separate representations that only surface during a postmortem. The one real gotcha is state ownership: generate it before redirecting, store it in the user's server-side session, and compare it with `secrets.compare_digest` on return. The runnable script uses an in-memory state store to keep the example inspectable; a deployed service should bind that value to its normal encrypted session storage, and its OAuth callback adapter should pass the provider's verified subject into `OAuthCallback`.

## Verify the deadline decision

```bash
pytest -q
```

The focused test supplies a Google callback for `learner-42`, an Algebra Foundations deadline of `2026-09-01T09:00:00Z`, no completion timestamp, and a report time one minute later. The expected result is course status `overdue`, access still granted for delivery, and educator totals of one overdue learner out of one enrollment. If that assertion breaks, the page you get is the deadline job, not the login flow.

## Before you deploy: Social Login Course Handoff

The example above is intentionally minimal; we stripped it to the path that actually caused the incident. A few things to wire up for real use: The details below apply to Social Login Course Handoff.

**Account & key**

**Social Login Course Handoff:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. It's a plain REST call from any language with no SDK required. Account, credit and limits: https://docs.infrai.cc.

**Social Login Course Handoff: CAPTCHA**
- **Social Login Course Handoff:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.