import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from daily_fill import india_date, reserve_attempt, validate_entry


class JournalGuardsTest(unittest.TestCase):
    def entry(self):
        return {"date": "2026-09-14", "attendance": "present", "tasks": "Implemented the project search filter.", "solved": "Fixed search state resetting on navigation.", "pending": "Keyboard navigation remains unfinished.", "plan": "Finish keyboard navigation and test it."}

    def test_india_date_crosses_utc_midnight(self):
        self.assertEqual(india_date(datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc)), "2026-09-14")

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            india_date(datetime(2026, 9, 14))

    def test_dated_complete_entry_keeps_exact_answers(self):
        entry = self.entry()
        self.assertEqual(validate_entry(entry, "2026-09-14"), entry)

    def test_stale_and_future_entries_rejected(self):
        for date in ["2026-09-13", "2026-09-15"]:
            with self.subTest(date=date), self.assertRaises(ValueError):
                validate_entry({**self.entry(), "date": date}, "2026-09-14")

    def test_every_missing_answer_rejected(self):
        for key in ["tasks", "solved", "pending", "plan"]:
            for value in [None, "", "   ", 123]:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_entry({**self.entry(), key: value}, "2026-09-14")

    def test_attendance_is_not_assumed(self):
        for attendance in [None, "unknown"]:
            with self.subTest(attendance=attendance), self.assertRaises(ValueError):
                validate_entry({**self.entry(), "attendance": attendance}, "2026-09-14")

    def test_days_without_work_need_no_fictional_answers(self):
        for attendance in ["holiday", "not_scheduled", "absent"]:
            entry = {"date": "2026-09-14", "attendance": attendance}
            self.assertEqual(validate_entry(entry, "2026-09-14"), entry)

    def test_duplicate_or_uncertain_attempt_blocks_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            self.assertTrue(reserve_attempt(state, "2026-09-14").is_file())
            with self.assertRaises(ValueError):
                reserve_attempt(state, "2026-09-14")
            self.assertTrue(reserve_attempt(state, "2026-09-15").is_file())


if __name__ == "__main__":
    unittest.main()
