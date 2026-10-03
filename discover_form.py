"""
One-time interactive script.
Opens a real Chromium window, lets you log into your Kalvium Google account
by hand, then:
  1. Saves the logged-in browser session to auth_state.json (for reuse).
  2. Extracts the form's internal structure (question text, type, entry IDs,
     options) from Google's embedded FB_PUBLIC_LOAD_DATA_ JSON and writes it
     to form_structure.json so we can build the daily auto-fill payload.

Run it with: venv\\Scripts\\python.exe discover_form.py
"""
import json
import re
from playwright.sync_api import sync_playwright

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc8RRUAG8n8nPB9dm21m_MxwHQ-JuDnEj7GnvwEkWXykkKFuQ/viewform"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(FORM_URL)

    input(
        "\nA browser window has opened.\n"
        "1. Log into your Kalvium Google account.\n"
        "2. Make sure you land on the actual form page (with the questions visible).\n"
        "Once you can see the form, come back here and press Enter...\n"
    )

    page.wait_for_load_state("networkidle")
    html = None
    for attempt in range(5):
        try:
            html = page.content()
            break
        except Exception:
            page.wait_for_timeout(1000)
    if html is None:
        raise SystemExit("Page kept navigating; re-run the script and wait a moment longer before pressing Enter.")

    context.storage_state(path="auth_state.json")
    print("Saved logged-in session to auth_state.json")

    match = re.search(r"var FB_PUBLIC_LOAD_DATA_ = (.*?);\s*</script>", html, re.S)
    if not match:
        print("Could not find FB_PUBLIC_LOAD_DATA_ in the page.")
        print("Dumping raw HTML to form_page.html for manual inspection instead.")
        with open("form_page.html", "w", encoding="utf-8") as f:
            f.write(html)
    else:
        data = json.loads(match.group(1))
        with open("form_structure_raw.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        try:
            title = data[1][8][0][3] if (len(data) > 1 and len(data[1]) > 8 and data[1][8] and data[1][8][0]) else None
            questions = []
            for item in data[1][1]:
                q_title = item[1]
                q_type = item[3]
                entry_block = item[4][0]
                entry_id = entry_block[0]
                options = None
                if entry_block[1]:
                    options = [opt[0] for opt in entry_block[1]]
                required = bool(entry_block[2]) if len(entry_block) > 2 else None
                questions.append({
                    "title": q_title,
                    "type_code": q_type,
                    "entry_id": f"entry.{entry_id}",
                    "options": options,
                    "required": required,
                })

            with open("form_structure.json", "w", encoding="utf-8") as f:
                json.dump({"questions": questions}, f, indent=2, ensure_ascii=False)

            print(f"\nExtracted {len(questions)} questions -> form_structure.json")
            for q in questions:
                print(f"- [{q['entry_id']}] ({q['type_code']}) {q['title']!r} options={q['options']}")
        except Exception as err:
            print(f"Session saved successfully, but structure parsing was skipped: {err}")

    browser.close()
