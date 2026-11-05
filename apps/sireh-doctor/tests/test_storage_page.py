"""Regression tests for Storage Doctor GUI."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLabel
from sireh_doctor.gui.storage_page import StoragePage


MODULE = "sireh_doctor.gui.storage_page"


def sample_inventory():
    return {
        "status": "AVAILABLE",
        "error": None,
        "devices": [{
            "name": "sda",
            "path": "/dev/sda",
            "model": "TEST SATA SSD",
            "size_bytes": 512000000000,
            "transport": "sata",
            "removable": False,
            "rotational": False,
            "controller": {
                "status": "AVAILABLE",
                "pci_address": "0000:00:1f.2",
            },
            "pci": {
                "pci_address": "0000:00:1f.2",
                "vendor_id": "8086",
                "device_id": "9c83",
                "class_code": "010601",
                "driver": "ahci",
            },
            "classification": {
                "controller_type": "SATA_AHCI",
                "physical_disk_visibility": "NOT_ASSESSED",
            },
        }],
    }


class StoragePageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @patch(MODULE + ".resolve_pci_name")
    @patch(MODULE + ".collect_storage_inventory")
    def test_inventory_rendering(self, inventory, resolver):
        inventory.return_value = sample_inventory()
        resolver.return_value = {
            "status": "AVAILABLE",
            "description": (
                "Intel Corporation Wildcat Point-LP SATA "
                "Controller [AHCI Mode] [8086:9c83] (rev 03)"
            ),
            "subsystem": "Lenovo SATA Controller [17aa:5034]",
            "kernel_driver": "ahci",
            "kernel_modules": "ahci",
        }

        page = StoragePage()
        labels = [
            item.text()
            for item in page.findChildren(QLabel)
        ]

        self.assertIn("TEST SATA SSD", labels)
        self.assertIn("512.00 GB", labels)
        self.assertIn("PCI revision", labels)
        self.assertIn("03", labels)
        self.assertIn("NOT YET ASSESSED", labels)

        inventory.assert_called_once()
        resolver.assert_called_once_with("0000:00:1f.2")

        page.close()
        page.deleteLater()

    @patch(MODULE + ".resolve_pci_name")
    @patch(MODULE + ".collect_storage_inventory")
    def test_missing_controller_is_not_fabricated(
        self, inventory, resolver
    ):
        payload = sample_inventory()
        payload["devices"][0]["controller"] = None
        payload["devices"][0]["pci"] = None
        payload["devices"][0]["classification"] = None

        inventory.return_value = payload
        resolver.return_value = {
            "status": "UNKNOWN",
            "description": None,
            "subsystem": None,
            "kernel_driver": None,
            "kernel_modules": None,
        }

        page = StoragePage()
        labels = [
            item.text()
            for item in page.findChildren(QLabel)
        ]

        self.assertIn("UNKNOWN", labels)
        self.assertNotIn("Intel Corporation", labels)

        page.close()
        page.deleteLater()

    @patch(MODULE + ".resolve_pci_name")
    @patch(MODULE + ".collect_storage_inventory")
    def test_refresh_repeats_discovery(self, inventory, resolver):
        inventory.return_value = sample_inventory()
        resolver.return_value = {
            "status": "UNKNOWN",
            "description": None,
            "subsystem": None,
            "kernel_driver": None,
            "kernel_modules": None,
        }

        page = StoragePage()
        page.refresh_button.click()

        self.assertEqual(inventory.call_count, 2)

        page.close()
        page.deleteLater()


if __name__ == "__main__":
    unittest.main()
