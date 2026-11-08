"""SD-10 Health Report GUI regression tests."""

import unittest
from PyQt5.QtWidgets import QApplication, QLabel
from sireh_doctor.gui.health_report_page import HealthReportPage


class HealthReportGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_generate_refresh_clear(self):
        data = {
            "hardware": {
                "cpu": {"status": "PASS", "summary": "OK"}
            }
        }
        page = HealthReportPage(lambda: data)
        page.generate()
        self.assertEqual(page.report["counts"]["PASS"], 1)

        data["hardware"]["cpu"]["status"] = "WARN"
        page.generate()
        self.assertEqual(page.report["counts"]["WARN"], 1)

        page.clear_results()
        self.assertIsNone(page.report)
        self.assertFalse(page.copy_button.isEnabled())
        self.assertTrue(page.print_button.isEnabled())
        self.assertEqual(
            data["hardware"]["cpu"]["status"], "WARN"
        )

    def test_notices(self):
        page = HealthReportPage()
        labels = [
            item.text()
            for item in page.findChildren(QLabel)
        ]
        self.assertTrue(any(
            "BEFORE GENERATING" in x for x in labels
        ))
        self.assertTrue(any(
            "COMING SOON" in x for x in labels
        ))


if __name__ == "__main__":
    unittest.main()
