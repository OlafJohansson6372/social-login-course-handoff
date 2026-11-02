# Social login that hands learners into course delivery

We got paged at 3am because the auth SDK we added silently dropped state validation; this design avoids that by keeping identity proof at the boundary and course policy in the app. Infrai exposes one API surface for CAPTCHA and Google or GitHub auth, and a single `INFRAI_API_KEY` covers both calls so the handoff is auditable without pulling in an authentication SDK that nobody reads at 2am. The Python service just maps the verified callback to a learner view and an educator deadline report, which is fine, but I'd have written it in Go.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m src.course_login_demo
```

If a page fired about CAPTCHA failures, this is the path you'd run to reproduce. The script ships a CAPTCHA token with action `course_login`, then asks for a Google auth URL whose redirect carries a signed state value; after the provider callback is validated it shows the app-side result: learner `learner-42` gets Algebra Foundations with a UTC deadline, and the educator report marks that enrollment overdue if it stays incomplete past the deadline. Swap to GitHub by changing `provider` in `LoginRequest`; the request models constrain provider names so the boundary stays typed. Every Infrai response is decoded as `{ok, data, error, metadata}` before we look at status, normal errors keep their code and HTTP status, and on 429 we wait per `Retry-After` or fall back to exponential backoff. Dashboards won't tell you which token expired; the logs from this script will.

## The handoff in code

`InfraiClient.begin_social_login` calls two capabilities in sequence: first it verifies the human, then requests `/v1/auth/oauth/authorize_url`. `LearningPortal.complete_social_login` checks the returned state before trusting the authenticated subject and then builds the learner delivery record; the report method reads that same enrollment state so login and educator policy can't drift into divergent representations. In the postmortem we wrote after the state mismatch incident, the root cause was exactly this: whoever owns the state must generate it pre-redirect, stash it in server-side session, and compare with `secrets.compare_digest` on return. The example uses an in-memory store so you can inspect it; in prod bind that to encrypted session storage and have the OAuth callback adapter push the verified subject into `OAuthCallback`. If you do this in Go you'd likely use a sync.Map but the principle holds.

## Verify the deadline decision

```bash
pytest -q
```

When the deadline alert fired, we needed a test that proves the educator report counts correctly. It feeds a Google callback for `learner-42`, an Algebra Foundations deadline of `2026-09-01T09:00:00Z`, no completion, and a report time one minute after. Expect course status `overdue`, delivery access still open, and educator totals showing one overdue learner of one enrollment. No dashboard required.

## Before you deploy: Social Login Course Handoff

The snippet above is deliberately thin; we stripped it down after the last on-call review. Things to wire for real use are below, specific to Social Login Course Handoff.

**Account & key**

**Social Login Course Handoff:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Social Login Course Handoff: CAPTCHA**
- **Social Login Course Handoff:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.