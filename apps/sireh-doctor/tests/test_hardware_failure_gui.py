"""Regression tests for Hardware Doctor GUI failure handling."""

import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox

from sireh_doctor.gui.hardware_page import HardwarePage


class HardwareFailureGuiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HardwarePage()
        self.check_id = "battery:BAT0"

        self.before_timestamps = dict(
            self.page.check_timestamps
        )
        self.before_findings = [
            dict(f) for f in self.page.latest_findings
        ]
        self.before_card = self.page.finding_cards[
            self.check_id
        ]

        with patch(
            "sireh_doctor.gui.hardware_page.collect",
            side_effect=RuntimeError("Simulated failure"),
        ), patch.object(
            QMessageBox,
            "warning",
            return_value=QMessageBox.Ok,
        ) as warning:
            self.result = self.page.rerun_card(
                self.check_id
            )
            self.warning_args = warning.call_args
            self.warning_count = warning.call_count

    def tearDown(self):
        self.page.close()
        self.app.processEvents()

    def test_failure_is_handled(self):
        self.assertIsNone(self.result)

    def test_warning_is_displayed(self):
        self.assertEqual(self.warning_count, 1)
        self.assertEqual(
            self.warning_args.args[1],
            "Diagnostic could not complete",
        )

    def test_timestamps_are_preserved(self):
        self.assertEqual(
            self.page.check_timestamps,
            self.before_timestamps,
        )

    def test_findings_are_preserved(self):
        self.assertEqual(
            self.page.latest_findings,
            self.before_findings,
        )

    def test_original_card_is_preserved(self):
        self.assertIs(
            self.page.finding_cards[self.check_id],
            self.before_card,
        )


if __name__ == "__main__":
    unittest.main()
