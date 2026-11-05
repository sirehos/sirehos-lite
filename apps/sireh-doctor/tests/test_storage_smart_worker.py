"""Tests for Storage Doctor SMART background worker."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from sireh_doctor.gui.storage_smart_worker import SmartWorker


MODULE = "sireh_doctor.gui.storage_smart_worker"


class SmartWorkerTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @patch(MODULE + ".assess_smart")
    @patch(MODULE + ".collect_smart")
    def test_successful_assessment(self, collect, assess):
        collect.return_value = {
            "status": "AVAILABLE",
            "data": {"smart_status": {"passed": True}},
        }
        assess.return_value = {
            "status": "PASS",
            "summary": "SMART indicators passed.",
            "recommendation": None,
            "metrics": {"temperature_c": 27},
        }

        results = []
        worker = SmartWorker("/dev/sda")
        worker.completed.connect(results.append)
        worker.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["device"], "/dev/sda")
        self.assertEqual(results[0]["assessment"]["status"], "PASS")
        self.assertEqual(
            results[0]["assessment"]["metrics"]["temperature_c"],
            27,
        )
        collect.assert_called_once_with("/dev/sda")

    @patch(MODULE + ".assess_smart")
    @patch(MODULE + ".collect_smart")
    def test_permission_required(self, collect, assess):
        collect.return_value = {
            "status": "PERMISSION_REQUIRED",
            "error": "Administrator permission required",
            "data": None,
        }
        assess.return_value = {
            "status": "UNKNOWN",
            "summary": "SMART health could not be assessed.",
            "recommendation": "Administrator permission required",
            "metrics": {},
        }

        results = []
        worker = SmartWorker("/dev/sda")
        worker.completed.connect(results.append)
        worker.run()

        self.assertEqual(
            results[0]["collection"]["status"],
            "PERMISSION_REQUIRED",
        )
        self.assertEqual(
            results[0]["assessment"]["status"],
            "UNKNOWN",
        )

    @patch(MODULE + ".collect_smart")
    def test_unexpected_error(self, collect):
        collect.side_effect = RuntimeError("Synthetic failure")

        results = []
        worker = SmartWorker("/dev/sda")
        worker.completed.connect(results.append)
        worker.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["assessment"]["status"],
            "UNKNOWN",
        )
        self.assertNotIn(
            "Synthetic failure",
            str(results[0]),
        )


if __name__ == "__main__":
    unittest.main()
