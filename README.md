# Kalvium Daily Journal

The primary submission schedule is the **Submit Kalvium daily journal** task in
ChatGPT, configured for **16:30 Asia/Kolkata every day**, starting 14 September
2026. It uses the signed-in Kalvium Google account and the actual dated work
notes supplied in the Form Automation project, or a work source explicitly
identified by the user.

## Current state

- Google sign-in and access to the four journal fields were verified.
- The daily ChatGPT task has been created and enabled.
- No live response was submitted during setup: today's actual work answers
  were not supplied. End-to-end submission remains unverified until the first
  real dated entry is available.
- The old GitHub cron has been removed to avoid two independent submitters.
  GitHub Actions now runs validation tests only and does not read AUTH_STATE.
- The old random answer generator has been removed. Missing attendance or
  work details cause a request for the missing information, not a fabricated
  submission.

## Daily information

Provide the current India date, attendance (present, absent, campus holiday,
or no scheduled Simulated Work), key tasks, solved problems, unresolved
problems, and the plan for the next Simulated Work day. Explicitly say when
there were no blockers. Keep private notes in ChatGPT or local files, not in
this public repository.

The task submits only after all required information is known, skips confirmed
holidays and unscheduled days, checks the intended Google account, and treats
only an explicit recorded-response confirmation as success. It checks prior
results to avoid duplicates and does not blindly retry an uncertain submission.
Notes from another date are not reused as today's work.

Google can require sign-in again. If that happens, the task will report the
blocker and request secure sign-in; no automation can guarantee uninterrupted
authentication. The configured time is the start of the task, not a guarantee
that Google has received the response at that exact second.

## Optional local fallback

Pause the ChatGPT task before using a separate local submitter for the same
date. The local receipt guard is not shared with ChatGPT or other computers.

Install Python 3.12+, the dependencies in `requirements.txt`, and Playwright
Chromium. The existing `discover_form.py` is a local-only sign-in helper.
Its `auth_state.json` contains reusable authentication credentials; never
commit it or upload it to the public repository. ChatGPT's cloud sign-in does
not refresh a locally saved session or the former GitHub AUTH_STATE secret.

Create a local, ignored `journal_entry.json` with these fields:

| Field | Value |
| --- | --- |
| `date` | Today's India date, `YYYY-MM-DD` |
| `attendance` | `present`, `absent`, `holiday`, or `not_scheduled` |
| `tasks` | Actual tasks completed or worked on |
| `solved` | Problems actually solved |
| `pending` | Actual unresolved problems, or an explicit statement of none |
| `plan` | Actual plan for the next Simulated Work day |

Validate without opening or submitting the form:

```sh
python daily_fill.py --entry journal_entry.json
```

To submit locally, set `EXPECTED_EMAIL` to the intended Kalvium account in your
shell, then run:

```sh
python daily_fill.py --entry journal_entry.json --submit
```

The local fallback supports present working days, skips holidays and
unscheduled days, and directs absence entries to the interactive form because
their additional questions have not been inspected. It writes a local attempt
receipt immediately before clicking Submit. If the result is uncertain, inspect
the form outcome before removing the attempt receipt. Do not retry blindly.
The local browser submission path has not been tested against a live response;
the data and duplicate guards are covered by unit tests.

## Validation

```sh
python -m unittest -v test_daily_fill.py
```

## References

- [Google journal form](https://docs.google.com/forms/d/e/1FAIpQLSc8RRUAG8n8nPB9dm21m_MxwHQ-JuDnEj7GnvwEkWXykkKFuQ/viewform)
- [GitHub scheduled workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Playwright authentication state guidance](https://playwright.dev/python/docs/auth)
