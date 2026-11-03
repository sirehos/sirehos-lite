"""Full-refresh early-failure regression tests."""

import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox
from sireh_doctor.gui.hardware_page import HardwarePage


class HardwareRefreshFailureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HardwarePage()

    def tearDown(self):
        self.page.close()
        self.app.processEvents()

    def simulate_failure(self, failure_point):
        page = self.page

        before_timestamps = dict(page.check_timestamps)
        before_findings = [
            dict(f) for f in page.latest_findings
        ]
        before_cards = dict(page.finding_cards)
        before_data = page.latest_hardware_data
        before_counts = {
            key: label.text()
            for key, label in page.summary_cards.items()
        }

        with patch(
            "sireh_doctor.gui.hardware_page." + failure_point,
            side_effect=RuntimeError("Simulated failure"),
        ), patch.object(
            QMessageBox,
            "warning",
            return_value=QMessageBox.Ok,
        ) as warning:
            result = page.refresh()

        return {
            "result": result,
            "warning_count": warning.call_count,
            "warning_args": warning.call_args,
            "timestamps_ok": (
                page.check_timestamps == before_timestamps
            ),
            "findings_ok": (
                page.latest_findings == before_findings
            ),
            "cards_ok": (
                len(page.finding_cards) == len(before_cards)
                and all(
                    page.finding_cards.get(key) is card
                    for key, card in before_cards.items()
                )
            ),
            "data_ok": page.latest_hardware_data is before_data,
            "counts_ok": all(
                page.summary_cards[key].text() == value
                for key, value in before_counts.items()
            ),
        }

    def test_collect_failure_warning(self):
        result = self.simulate_failure("collect")
        self.assertIsNone(result["result"])
        self.assertEqual(result["warning_count"], 1)
        self.assertEqual(
            result["warning_args"].args[1],
            "Full hardware check could not complete",
        )

    def test_collect_failure_preserves_timestamps(self):
        result = self.simulate_failure("collect")
        self.assertTrue(result["timestamps_ok"])

    def test_collect_failure_preserves_results(self):
        result = self.simulate_failure("collect")
        self.assertTrue(result["findings_ok"])
        self.assertTrue(result["cards_ok"])
        self.assertTrue(result["data_ok"])
        self.assertTrue(result["counts_ok"])

    def test_assess_failure_warning(self):
        result = self.simulate_failure("assess")
        self.assertIsNone(result["result"])
        self.assertEqual(result["warning_count"], 1)
        self.assertEqual(
            result["warning_args"].args[1],
            "Full hardware check could not complete",
        )

    def test_assess_failure_preserves_timestamps(self):
        result = self.simulate_failure("assess")
        self.assertTrue(result["timestamps_ok"])

    def test_assess_failure_preserves_results(self):
        result = self.simulate_failure("assess")
        self.assertTrue(result["findings_ok"])
        self.assertTrue(result["cards_ok"])
        self.assertTrue(result["data_ok"])
        self.assertTrue(result["counts_ok"])


if __name__ == "__main__":
    unittest.main()
