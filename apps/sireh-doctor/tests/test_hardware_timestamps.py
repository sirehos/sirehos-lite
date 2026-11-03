"""Regression tests for Hardware Doctor timestamps."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QLabel

from sireh_doctor.gui.hardware_page import HardwarePage


class HardwareTimestampTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HardwarePage()

    def tearDown(self):
        self.page.close()
        self.app.processEvents()

    def timestamp_label(self, check_id):
        card = self.page.finding_cards[check_id]
        label = card.findChild(QLabel, "lastCheckedLabel")
        self.assertIsNotNone(label)
        return label.text()

    def test_all_findings_have_timestamps(self):
        self.assertEqual(len(self.page.check_timestamps), 7)

    def test_all_cards_display_timestamps(self):
        for check_id in self.page.finding_cards:
            self.assertTrue(
                self.timestamp_label(check_id).startswith(
                    "Last checked: "
                )
            )

    def test_individual_check_preserves_other_timestamps(self):
        before = dict(self.page.check_timestamps)

        with patch(
            "sireh_doctor.gui.hardware_page.datetime"
        ) as mock_datetime:
            fixed_time = datetime(
                2026, 11, 3, 21, 5, 0,
                tzinfo=timezone.utc
            )
            mock_datetime.now.return_value.astimezone.return_value = (
                fixed_time
            )

            self.page.rerun_card("battery:BAT0")

        self.assertEqual(
            self.page.check_timestamps["battery:BAT0"],
            fixed_time
        )

        for check_id in before:
            if check_id != "battery:BAT0":
                self.assertEqual(
                    self.page.check_timestamps[check_id],
                    before[check_id]
                )

    def test_timestamp_visible_after_rerun(self):
        self.page.rerun_card("memory")

        checked_at = self.page.check_timestamps["memory"]
        formatted = checked_at.strftime(
            "%d %b %Y, %H:%M:%S %Z"
        )

        self.assertIn(
            formatted,
            self.timestamp_label("memory")
        )

    def test_full_refresh_updates_all_timestamps(self):
        old_time = datetime(
            2020, 1, 1, tzinfo=timezone.utc
        )

        for check_id in self.page.check_timestamps:
            self.page.check_timestamps[check_id] = old_time

        self.page.refresh()

        self.assertEqual(len(self.page.check_timestamps), 7)

        for timestamp in self.page.check_timestamps.values():
            self.assertNotEqual(timestamp, old_time)


if __name__ == "__main__":
    unittest.main()
