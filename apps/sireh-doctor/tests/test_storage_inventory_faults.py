"""Fault-injection tests for unified storage inventory."""

import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_inventory import (
    collect_storage_inventory,
)

MODULE = "sireh_doctor.diagnostics.storage_inventory"


def discovery():
    return {
        "status": "AVAILABLE",
        "error": None,
        "devices": [
            {
                "name": "sda",
                "path": "/dev/sda",
                "type": "disk",
                "model": "TEST",
                "size": 1000000000,
            },
        ],
    }


class StorageInventoryFaultTests(unittest.TestCase):

    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_controller_exception_isolated(self, storage, controller):
        storage.return_value = discovery()
        controller.side_effect = OSError("sysfs unavailable")

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(
            result["devices"][0]["controller"]["status"],
            "UNKNOWN",
        )

    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_pci_exception_isolated(self, storage, controller, pci):
        storage.return_value = discovery()
        controller.return_value = {
            "status": "AVAILABLE",
            "pci_address": "0000:00:1f.2",
        }
        pci.side_effect = OSError("PCI metadata unavailable")

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["devices"]), 1)
        self.assertIsNone(result["devices"][0]["classification"])

    @patch(MODULE + ".classify_controller")
    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_classification_exception_isolated(
        self, storage, controller, pci, classify
    ):
        storage.return_value = discovery()
        controller.return_value = {
            "status": "AVAILABLE",
            "pci_address": "0000:00:1f.2",
        }
        pci.return_value = {
            "status": "AVAILABLE",
            "class_code": "010601",
        }
        classify.side_effect = ValueError("unexpected class")

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["devices"]), 1)
        self.assertIsNone(result["devices"][0]["classification"])

    @patch(MODULE + ".collect_storage")
    def test_malformed_disk_entry_isolated(self, storage):
        payload = discovery()
        payload["devices"].insert(0, None)
        payload["devices"].insert(1, "invalid")
        storage.return_value = payload

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["devices"]), 1)


if __name__ == "__main__":
    unittest.main()
