"""SMART button and result-display regression tests."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from sireh_doctor.gui.storage_page import StoragePage

MODULE = "sireh_doctor.gui.storage_page"


def inventory():
    return {
        "status": "AVAILABLE",
        "error": None,
        "devices": [{
            "name": "sda",
            "path": "/dev/sda",
            "model": "TEST SSD",
            "size_bytes": 512000000000,
            "transport": "sata",
            "removable": False,
            "rotational": False,
            "controller": {},
            "pci": {},
            "classification": {},
        }],
    }


def identity():
    return {
        "status": "UNKNOWN",
        "description": None,
        "subsystem": None,
        "kernel_driver": None,
        "kernel_modules": None,
    }


class SmartPageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_page(self):
        inventory_patch = patch(
            MODULE + ".collect_storage_inventory",
            return_value=inventory(),
        )
        pci_patch = patch(
            MODULE + ".resolve_pci_name",
            return_value=identity(),
        )

        self.addCleanup(inventory_patch.stop)
        self.addCleanup(pci_patch.stop)

        inventory_mock = inventory_patch.start()
        pci_patch.start()

        page = StoragePage()
        self.addCleanup(page.close)
        return page, inventory_mock

    def test_button_created_without_smart_execution(self):
        with patch(MODULE + ".SmartWorker") as worker:
            page, _ = self.make_page()
            self.assertIn("/dev/sda", page.smart_buttons)
            self.assertTrue(page.smart_buttons["/dev/sda"].isEnabled())
            worker.assert_not_called()

    def test_successful_smart_result(self):
        page, _ = self.make_page()

        page.on_smart_completed({
            "device": "/dev/sda",
            "collection": {"status": "AVAILABLE"},
            "assessment": {
                "status": "PASS",
                "summary": "SMART indicators passed.",
                "recommendation": "",
                "metrics": {
                    "temperature_c": 27,
                    "power_on_hours": 18369,
                },
            },
        })

        text = page.smart_labels["/dev/sda"].text()
        self.assertIn("SMART: PASS", text)
        self.assertIn("Temperature C: 27", text)
        self.assertIn("Power On Hours: 18369", text)

    def test_permission_denied_remains_unknown(self):
        page, _ = self.make_page()

        page.on_smart_completed({
            "device": "/dev/sda",
            "collection": {
                "status": "PERMISSION_REQUIRED",
                "error": "Administrator permission required",
            },
            "assessment": {
                "status": "UNKNOWN",
                "summary": "SMART health could not be assessed.",
                "recommendation": "Administrator permission required",
                "metrics": {},
            },
        })

        text = page.smart_labels["/dev/sda"].text()
        self.assertIn("SMART: UNKNOWN", text)
        self.assertIn("Administrator permission required", text)
        self.assertNotIn("SMART: PASS", text)

    def test_button_starts_worker_and_disables_itself(self):
        page, _ = self.make_page()

        with patch(MODULE + ".SmartWorker") as worker_class:
            worker = worker_class.return_value
            page.smart_buttons["/dev/sda"].click()

            worker_class.assert_called_once_with("/dev/sda", page)
            worker.start.assert_called_once()
            self.assertFalse(
                page.smart_buttons["/dev/sda"].isEnabled()
            )

    def test_inventory_refresh_does_not_start_smart(self):
        page, inventory_mock = self.make_page()

        with patch(MODULE + ".SmartWorker") as worker:
            page.refresh_button.click()
            self.assertEqual(inventory_mock.call_count, 2)
            worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
