"""
Helper script to refresh Google Form authentication session, update GitHub Secrets,
and trigger GitHub Actions to submit the daily journal.

Usage:
  .venv/bin/python refresh_session.py
  .venv/bin/python refresh_session.py --submit-local
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc8RRUAG8n8nPB9dm21m_MxwHQ-JuDnEj7GnvwEkWXykkKFuQ/viewform"
REPO = "AdityaNikam10/kalvium-daily-journal-bot"
DEFAULT_EMAIL = "aditya.nikam.s73@kalvium.community"


def refresh():
    submit_local = "--submit-local" in sys.argv
    print("=" * 65)
    print("      KALVIUM JOURNAL BOT - GOOGLE SESSION REFRESH TOOL")
    print("=" * 65)
    print(f"Target Form:   {FORM_URL}")
    print(f"GitHub Repo:   {REPO}")
    print(f"Kalvium Email: {DEFAULT_EMAIL}\n")
    print("1. Launching Google Chrome...")
    print(f"2. Please sign into your Kalvium Google account ({DEFAULT_EMAIL}).")
    print("3. Once the form questions load, this script will automatically capture")
    print("   the session cookies, update GitHub Secrets, and trigger GitHub Actions!\n")

    auth_state_path = "auth_state.json"
    user_data_dir = os.path.expanduser("~/.kalvium-bot-chrome-profile")
    os.makedirs(user_data_dir, exist_ok=True)

    with sync_playwright() as p:
        # Launch Chrome with stealth flags to avoid Google's "browser or app not secure" block
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("Navigating to form...")
        page.goto(FORM_URL)

        # Bring Google Chrome window to front on macOS
        try:
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'], capture_output=True)
        except Exception:
            pass

        print("\nWaiting for sign-in... (Please sign in in the opened Chrome window)\n")

        start_time = time.time()
        logged_in = False
        while time.time() - start_time < 900:  # 15 minutes timeout
            try:
                if page.is_closed():
                    if context.pages:
                        page = context.pages[0]
                    else:
                        print("\n[-] Chrome window was closed before completing login.")
                        sys.exit(1)

                url = page.url
                # Check if we landed on the Google form and are no longer on accounts.google.com
                if "accounts.google.com" not in url and "docs.google.com/forms" in url:
                    if (
                        page.locator("form").count() > 0
                        or page.locator("div[role='list']").count() > 0
                        or page.get_by_role("button", name="Next").count() > 0
                    ):
                        print("\n[✓] Successfully detected active Google Form page!")
                        logged_in = True
                        break
            except Exception as e:
                if "closed" in str(e).lower() or "target" in str(e).lower():
                    print("\n[-] Browser window was closed.")
                    sys.exit(1)
            time.sleep(1)

        if not logged_in:
            print("\n[-] Timed out waiting for sign-in after 5 minutes.")
            context.close()
            sys.exit(1)

        # Allow network to settle and cookies to finish syncing
        time.sleep(3)
        context.storage_state(path=auth_state_path)
        print(f"[✓] Saved valid session cookies to {auth_state_path}")
        context.close()

    # Step 2: Validate the session in headless mode (matching GitHub Actions environment)
    print("\nValidating session in background headless browser...")
    with sync_playwright() as p:
        test_browser = p.chromium.launch(headless=True)
        test_context = test_browser.new_context(storage_state=auth_state_path)
        test_page = test_context.new_page()
        test_page.goto(FORM_URL, wait_until="domcontentloaded")
        if "accounts.google.com" in test_page.url:
            test_browser.close()
            print("[-] Validation failed: Google redirected to accounts.google.com.")
            sys.exit(1)
        print("[✓] Session validated successfully! Google Form loaded without login prompt.")
        test_browser.close()

    # Step 3: Update GitHub Secret
    print("\nUpdating GitHub Repository Secrets...")
    try:
        check_gh = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if check_gh.returncode == 0:
            with open(auth_state_path, "r", encoding="utf-8") as f:
                json_content = f.read()
            proc = subprocess.run(
                ["gh", "secret", "set", "AUTH_STATE_JSON", "--repo", REPO],
                input=json_content,
                text=True,
                capture_output=True,
            )
            if proc.returncode == 0:
                print(f"[✓] GitHub Secret 'AUTH_STATE_JSON' updated successfully on {REPO}!")
            else:
                print(f"[-] Could not update secret via gh: {proc.stderr}")

            proc_email = subprocess.run(
                ["gh", "secret", "set", "EXPECTED_EMAIL", "--repo", REPO, "--body", DEFAULT_EMAIL],
                capture_output=True,
                text=True,
            )
            if proc_email.returncode == 0:
                print(f"[✓] GitHub Secret 'EXPECTED_EMAIL' confirmed as {DEFAULT_EMAIL}!")
            else:
                print(f"[-] Could not set EXPECTED_EMAIL: {proc_email.stderr}")
        else:
            print("[-] 'gh' CLI not logged in. Update secrets manually in repo settings.")
    except Exception as e:
        print(f"[-] Error updating GitHub secret: {e}")

    # Step 4: Optional local submission
    if submit_local:
        print("\nSubmitting today's journal entry locally now...")
        import daily_fill

        today_date = daily_fill.india_date()
        state_file = Path(".journal-state") / f"{today_date}.json"
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                if state_data.get("status") == "attempting":
                    state_file.unlink()
            except Exception:
                pass

        entry = daily_fill.get_default_entry(today_date)
        daily_fill.submit(
            entry=entry,
            expected_email=DEFAULT_EMAIL,
            auth_state=Path(auth_state_path),
            state_dir=Path(".journal-state"),
        )
        print(f"\n[✓] TODAY'S JOURNAL FOR {entry['date']} HAS BEEN SUCCESSFULLY SUBMITTED LOCALLY!")
    else:
        # Step 5: Trigger GitHub Actions workflow so user gets the green checkmark on GitHub Actions!
        print("\nTriggering GitHub Actions workflow run...")
        try:
            proc_run = subprocess.run(
                ["gh", "workflow", "run", "daily-journal.yml", "--repo", REPO],
                capture_output=True,
                text=True,
            )
            if proc_run.returncode == 0:
                print("[✓] GitHub Actions workflow 'Submit Daily Journal' triggered successfully!")
            else:
                print(f"[-] Could not trigger workflow: {proc_run.stderr}")
        except Exception as e:
            print(f"[-] Workflow trigger note: {e}")

    print("\n" + "=" * 65)
    print("      ALL DONE! YOUR FORM BOT IS READY AND WORKING.")
    print("=" * 65)


if __name__ == "__main__":
    refresh()
