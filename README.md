# Kalvium Daily Journal

The primary submission schedule is the **Submit Kalvium daily journal** task in
ChatGPT, configured for **16:30 Asia/Kolkata every calendar day**, including
weekends, starting 14 September 2026.

## Current state

- Google sign-in and all four writable journal fields were verified.
- The daily ChatGPT task is enabled and does not require fresh daily notes.
- The form was filled with the standard responses and advanced to the final
  Submit page. Submit was not clicked during setup; a live receipt is still
  pending the scheduled run.
- The old GitHub cron was removed. GitHub Actions runs validation tests only.
- The optional local CLI below is separate and still requires a dated entry.
  It is not the daily scheduler.

## Standing responses

The user requested generic submissions without a daily information request.
The scheduled task uses these exact responses unless a dated override is given:

| Question | Standard response |
| --- | --- |
| Key tasks | Working on ongoing Simulated Work tasks. |
| Problems solved | No specific resolved problem is documented in this entry. |
| Unresolved problems | No specific unresolved problem is documented in this entry. |
| Next-session plan | Continue working on the assigned Simulated Work tasks in the next session. |

The configured attendance default is "It was a working day, and I was present",
matching the user's selected form option. An explicit date-specific holiday or
absence correction overrides it. Weekends alone do not cause a skipped run.
The task does not generate random claims of specific accomplishments.

## Submission behavior

The verified present branch has three pages: email and attendance, four work
answers, and a final page with a Submit button. The heading "Thank you for
filling today's journal" appears BEFORE submission and is not a receipt.
Success requires explicit response-recorded confirmation after clicking Submit.
The form automatically emails a response copy to the signed-in account.

Only the current India date is submitted. Prior run results and form state are
checked for an existing submission; an uncertain attempt is not blindly retried.
The old GitHub submitter is not run in parallel with the ChatGPT task.

Google can require sign-in again. The task reports such blockers and requests
secure sign-in when needed. The configured time is when the task starts;
successful delivery at the exact second cannot be guaranteed.

## Failure audit and early sign-in check

A read-only audit of the nine failed submission runs found eight Google
session-expiry failures and one malformed saved-session JSON failure. The
eight session failures were on 7-13 September 2026; the JSON failure was a
manual run on 8 September. For example:
[expired session](https://github.com/Shubham-Padkonde/kalvium-daily-journal-bot/actions/runs/34763782295)
and [invalid session data](https://github.com/Shubham-Padkonde/kalvium-daily-journal-bot/actions/runs/34187466242).

The separate **Check Kalvium journal sign-in** task is enabled at **16:00
Asia/Kolkata every day**. It checks the intended Google account and form,
preserves the draft, and alerts the user about login or access problems before
the 16:30 submission. It never submits the form. A healthy check is silent.

The submission task checks access again, permits one recovery from an ordinary
transient failure before any Submit attempt, and avoids blind retries after a
possibly completed submission. It distinguishes a confirmed response, a
failure before submission, and an uncertain outcome.

GitHub validation currently passes, but those checks do not submit the form.
The replacement's first live scheduled response has not yet been verified.
Google session expiry, service outages, and delayed execution remain possible.

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
