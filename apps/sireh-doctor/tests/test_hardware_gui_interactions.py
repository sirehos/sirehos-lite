"""Hardware Doctor GUI interaction regression tests."""

import unittest

from PyQt5.QtWidgets import QApplication, QPushButton

from sireh_doctor.gui.hardware_page import HardwarePage


class HardwareGuiInteractionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HardwarePage()

    def tearDown(self):
        self.page.close()
        self.app.processEvents()

    def positions(self):
        result = {}

        for check_id, card in self.page.finding_cards.items():
            index = self.page.grid.indexOf(card)
            self.assertGreaterEqual(index, 0)
            result[check_id] = self.page.grid.getItemPosition(index)

        return result

    def test_grid_positions_survive_repeated_refreshes(self):
        initial = self.positions()

        self.assertEqual(len(initial), 7)

        for _ in range(3):
            self.page.refresh()
            self.assertEqual(self.positions(), initial)
            self.assertEqual(len(self.page.finding_cards), 7)
            self.assertEqual(len(self.page.check_timestamps), 7)

    def test_actual_button_clicks_are_isolated(self):
        self.page.refresh()
        self.page.refresh()

        check_ids = list(self.page.finding_cards)
        self.assertEqual(len(check_ids), 7)

        for check_id in check_ids:
            before = dict(self.page.finding_cards)
            before_timestamps = dict(self.page.check_timestamps)

            button = before[check_id].findChild(
                QPushButton, "runCheckButton"
            )

            self.assertIsNotNone(button)
            self.assertTrue(button.isEnabled())

            button.click()

            self.assertIsNot(
                self.page.finding_cards[check_id],
                before[check_id],
            )

            for other_id in check_ids:
                if other_id != check_id:
                    self.assertIs(
                        self.page.finding_cards[other_id],
                        before[other_id],
                    )
                    self.assertEqual(
                        self.page.check_timestamps[other_id],
                        before_timestamps[other_id],
                    )

    def test_grid_survives_all_individual_checks(self):
        initial = self.positions()
        check_ids = list(self.page.finding_cards)

        for check_id in check_ids:
            card = self.page.finding_cards[check_id]
            button = card.findChild(
                QPushButton, "runCheckButton"
            )

            self.assertIsNotNone(button)
            button.click()

        self.assertEqual(len(self.page.finding_cards), 7)
        self.assertEqual(len(self.page.check_timestamps), 7)
        self.assertEqual(self.positions(), initial)


if __name__ == "__main__":
    unittest.main()
