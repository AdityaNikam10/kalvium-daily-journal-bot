"""Optional local submitter using an explicit, dated journal entry.

The primary daily schedule is the ChatGPT automation. This CLI is a manual
fallback; it validates only unless --submit is supplied. Never run both for
the same date. Browser session files contain credentials and stay local.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc8RRUAG8n8nPB9dm21m_MxwHQ-JuDnEj7GnvwEkWXykkKFuQ/viewform"
IST = ZoneInfo("Asia/Kolkata")
QUESTIONS = {
    "tasks": "What were your key tasks for the day?",
    "solved": "What challenges/problems did you solve today?",
    "pending": "What challenges/problems you were NOT able to solve today and are planning to solve in upcoming days?",
    "plan": "What is your plan for the next day of Simulated Work?",
}
STATUSES = {"present", "absent", "holiday", "not_scheduled"}


def india_date(now=None):
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        raise ValueError("A timezone-aware timestamp is required.")
    return now.astimezone(IST).date().isoformat()


def validate_entry(entry, today=None):
    today = today or india_date()
    if not isinstance(entry, dict):
        raise ValueError("The journal entry must be a JSON object.")
    if entry.get("date") != today:
        raise ValueError("Only today's India date is accepted; no stale or future entries.")
    if entry.get("attendance") not in STATUSES:
        raise ValueError("Set attendance to present, absent, holiday, or not_scheduled.")
    if entry["attendance"] == "present":
        for key in QUESTIONS:
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing actual daily work detail: {key}.")
    return entry


def reserve_attempt(state_dir, date):
    """Exclusive local claim: an uncertain attempt must be checked manually."""
    state_dir.mkdir(parents=True, exist_ok=True)
    receipt = state_dir / f"{date}.json"
    try:
        with receipt.open("x", encoding="utf-8") as stream:
            json.dump({"date": date, "status": "attempting"}, stream)
    except FileExistsError as exc:
        raise ValueError("A submission was already attempted for this date. Check its outcome before retrying.") from exc
    return receipt


def submit(entry, expected_email, auth_state, state_dir):
    validate_entry(entry)
    if entry["attendance"] in {"holiday", "not_scheduled"}:
        print("Skipped: no Simulated Work journal required for this date.")
        return
    if entry["attendance"] == "absent":
        raise ValueError("Use the signed-in form for leave/absence; its additional questions need inspection.")
    if not expected_email or "@" not in expected_email:
        raise ValueError("Set EXPECTED_EMAIL to the Google account that must submit this journal.")
    if not auth_state.is_file():
        raise ValueError("Missing local Google session. Sign in using discover_form.py.")
    if (state_dir / f"{entry['date']}.json").exists():
        raise ValueError("A local attempt already exists for this date; inspect it before retrying.")

    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=str(auth_state))
            page = context.new_page()
            page.goto(FORM_URL, wait_until="domcontentloaded")
            if "accounts.google.com" in page.url:
                raise ValueError("Google sign-in has expired. No submission was made.")
            email_box = page.get_by_role("checkbox", name=f"Record {expected_email} as the email to be included with my response", exact=True)
            expect(email_box).to_be_visible()
            if email_box.get_attribute("aria-checked") != "true":
                email_box.click()
            
            present_radio = page.get_by_role("radio", name="It was a working day, and I was present", exact=True)
            expect(present_radio).to_be_visible()
            if present_radio.get_attribute("aria-checked") != "true":
                present_radio.click()
            page.get_by_role("button", name="Next", exact=True).click()

            for key, question in QUESTIONS.items():
                answer = page.get_by_role("textbox", name=re.compile("^" + re.escape(question)))
                answer.fill(entry[key])
                expect(answer).to_have_value(entry[key])
            page.get_by_role("button", name="Next", exact=True).click()
            submit_button = page.get_by_role("button", name="Submit", exact=True)
            expect(submit_button).to_be_visible()
            expect(submit_button).to_be_enabled()

            # Recheck date immediately before the irreversible action.
            validate_entry(entry)
            receipt = reserve_attempt(state_dir, entry["date"])
            submit_button.click()
            # The form intro also includes "recorded"; require the exact receipt.
            expect(page.get_by_text("Your response has been recorded.", exact=True)).to_be_visible(timeout=15000)
            temporary = receipt.with_suffix(".tmp")
            temporary.write_text(json.dumps({"date": entry["date"], "status": "confirmed", "confirmed_at": datetime.now(IST).isoformat()}), encoding="utf-8")
            temporary.replace(receipt)
            print(f"Confirmed journal submission for {entry['date']}.")
        finally:
            browser.close()


STANDING_RESPONSES = {
    "tasks": "Working on ongoing Simulated Work tasks.",
    "solved": "No specific resolved problem is documented in this entry.",
    "pending": "No specific unresolved problem is documented in this entry.",
    "plan": "Continue working on the assigned Simulated Work tasks in the next session.",
}


def get_default_entry(today=None):
    today = today or india_date()
    return {
        "date": today,
        "attendance": "present",
        **STANDING_RESPONSES,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", type=Path, default=Path("journal_entry.json"))
    parser.add_argument("--auth-state", type=Path, default=Path("auth_state.json"))
    parser.add_argument("--state-dir", type=Path, default=Path(".journal-state"))
    parser.add_argument("--submit", action="store_true", help="Actually submit the dated entry; otherwise validate only.")
    parser.add_argument("--auto", action="store_true", help="Use default standing responses for today if entry file is missing.")
    args = parser.parse_args()
    try:
        if args.entry.exists():
            entry = validate_entry(json.loads(args.entry.read_text(encoding="utf-8")))
        elif args.auto or not args.entry.exists():
            print("No journal_entry.json found; using standing default responses.")
            entry = validate_entry(get_default_entry())
        else:
            raise ValueError(f"Entry file '{args.entry}' not found.")

        # If auth_state file doesn't exist but AUTH_STATE_JSON env var is set, create it
        if not args.auth_state.exists() and os.environ.get("AUTH_STATE_JSON"):
            args.auth_state.write_text(os.environ["AUTH_STATE_JSON"], encoding="utf-8")

        if args.submit:
            submit(entry, os.environ.get("EXPECTED_EMAIL", ""), args.auth_state, args.state_dir)
        else:
            print(f"Validated entry for {entry['date']}; nothing submitted.")
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
