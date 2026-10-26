"""
Helper script to refresh Google Form authentication session and update GitHub Secrets.

Usage:
  .venv/bin/python refresh_session.py
"""
import json
import os
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc8RRUAG8n8nPB9dm21m_MxwHQ-JuDnEj7GnvwEkWXykkKFuQ/viewform"
REPO = "AdityaNikam10/kalvium-daily-journal-bot"
DEFAULT_EMAIL = "aditya.nikam.s73@kalvium.community"


def refresh():
    print("=" * 60)
    print("  KALVIUM JOURNAL BOT - SESSION REFRESH TOOL")
    print("=" * 60)
    print(f"Target Form: {FORM_URL}")
    print(f"GitHub Repo: {REPO}\n")
    print("1. Opening a browser window...")
    print("2. Please sign into your Kalvium Google account.")
    print("3. Once the form questions are loaded, return here.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(FORM_URL)

        print("Waiting for login... (Complete login in the opened browser window)")
        
        # Wait until user reaches the form page and is not on accounts.google.com
        while True:
            try:
                if page.is_closed():
                    print("\n[-] Browser window was closed before completing login.")
                    sys.exit(1)
                url = page.url
                if "accounts.google.com" not in url and "docs.google.com/forms" in url:
                    if page.locator("form").count() > 0 or page.get_by_role("button", name="Next").count() > 0:
                        print("\n[+] Successfully detected logged-in Google Form page!")
                        break
            except Exception as e:
                # Catch browser disconnection or closed page
                if "closed" in str(e).lower() or "target" in str(e).lower():
                    print("\n[-] Browser window was closed.")
                    sys.exit(1)
            time.sleep(1)

        # Give a moment for network to settle and cookies to finish syncing
        time.sleep(2)
        auth_state_path = "auth_state.json"
        context.storage_state(path=auth_state_path)
        print(f"[+] Saved valid session to {auth_state_path}")
        browser.close()

    # Step 2: Validate the session in headless mode
    print("\nValidating session in background headless browser...")
    with sync_playwright() as p:
        test_browser = p.chromium.launch(headless=True)
        test_context = test_browser.new_context(storage_state=auth_state_path)
        test_page = test_context.new_page()
        test_page.goto(FORM_URL, wait_until="domcontentloaded")
        if "accounts.google.com" in test_page.url:
            test_browser.close()
            print("[-] Validation failed: page still redirected to accounts.google.com")
            sys.exit(1)
        print("[+] Session validated successfully! Google Form loaded without login prompt.")
        test_browser.close()

    # Step 3: Update GitHub Secret if gh CLI is available
    print("\nUpdating GitHub Repository Secrets...")
    try:
        # Check gh auth
        check_gh = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if check_gh.returncode == 0:
            # Set AUTH_STATE_JSON
            with open(auth_state_path, "r", encoding="utf-8") as f:
                json_content = f.read()
            proc = subprocess.run(
                ["gh", "secret", "set", "AUTH_STATE_JSON", "--repo", REPO],
                input=json_content,
                text=True,
                capture_output=True,
            )
            if proc.returncode == 0:
                print(f"[+] GitHub Secret 'AUTH_STATE_JSON' updated successfully on {REPO}!")
            else:
                print(f"[-] Could not update secret via gh: {proc.stderr}")

            # Ensure EXPECTED_EMAIL is also set
            proc_email = subprocess.run(
                ["gh", "secret", "set", "EXPECTED_EMAIL", "--repo", REPO, "--body", DEFAULT_EMAIL],
                capture_output=True,
                text=True,
            )
            if proc_email.returncode == 0:
                print(f"[+] GitHub Secret 'EXPECTED_EMAIL' confirmed as {DEFAULT_EMAIL}!")
            else:
                print(f"[-] Could not set EXPECTED_EMAIL: {proc_email.stderr}")
        else:
            print("[-] 'gh' CLI not logged in. Please update secrets manually in GitHub repo settings.")
    except Exception as e:
        print(f"[-] Error updating GitHub secret automatically: {e}")

    print("\n" + "=" * 60)
    print("  ALL DONE! YOUR FORM BOT IS READY.")
    print("=" * 60)


if __name__ == "__main__":
    refresh()
