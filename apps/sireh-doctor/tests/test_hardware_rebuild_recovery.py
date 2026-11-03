"""Regression tests for failed Hardware Doctor GUI rebuilds."""

import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox

from sireh_doctor.gui import hardware_page
from sireh_doctor.gui.hardware_page import HardwarePage


class HardwareRebuildRecoveryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HardwarePage()

    def tearDown(self):
        self.page.close()
        self.app.processEvents()

    def simulate_failed_rebuild(self):
        page = self.page

        before = {
            "cards": dict(page.finding_cards),
            "timestamps": dict(page.check_timestamps),
            "findings": list(page.latest_findings),
            "data": page.latest_hardware_data,
            "grid_count": page.grid.count(),
            "summary": {
                key: label.text()
                for key, label in page.summary_cards.items()
            },
        }

        original = hardware_page.create_finding_card
        calls = [0]

        def failing_factory(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 3:
                raise RuntimeError(
                    "Simulated card construction failure"
                )
            return original(*args, **kwargs)

        with patch(
            "sireh_doctor.gui.hardware_page.create_finding_card",
            side_effect=failing_factory,
        ), patch.object(
            QMessageBox,
            "warning",
            return_value=QMessageBox.Ok,
        ) as warning:
            result = page.refresh()

        return before, result, calls[0], warning

    def test_failure_displays_warning(self):
        before, result, calls, warning = (
            self.simulate_failed_rebuild()
        )
        self.assertIsNone(result)
        self.assertEqual(calls, 3)
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(
            warning.call_args.args[1],
            "Full hardware check could not complete",
        )

    def test_failure_preserves_diagnostic_state(self):
        before, _, _, _ = self.simulate_failed_rebuild()

        self.assertEqual(
            self.page.check_timestamps,
            before["timestamps"],
        )
        self.assertEqual(
            self.page.latest_findings,
            before["findings"],
        )
        self.assertIs(
            self.page.latest_hardware_data,
            before["data"],
        )
        self.assertEqual(
            {
                key: label.text()
                for key, label in self.page.summary_cards.items()
            },
            before["summary"],
        )

    def test_failure_preserves_visible_cards(self):
        before, _, _, _ = self.simulate_failed_rebuild()

        self.assertEqual(
            self.page.grid.count(),
            before["grid_count"],
        )
        self.assertEqual(
            len(self.page.finding_cards),
            len(before["cards"]),
        )

        for key, card in before["cards"].items():
            self.assertIs(
                self.page.finding_cards.get(key),
                card,
            )
            self.assertGreaterEqual(
                self.page.grid.indexOf(card),
                0,
            )


if __name__ == "__main__":
    unittest.main()
