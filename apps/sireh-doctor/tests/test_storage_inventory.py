"""Regression tests for unified storage inventory."""

import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_inventory import (
    collect_storage_inventory,
)


MODULE = "sireh_doctor.diagnostics.storage_inventory"


def disk(name="sda"):
    return {
        "name": name,
        "path": "/dev/" + name,
        "type": "disk",
        "model": "TEST SSD",
        "size": 512000000000,
        "tran": "sata",
        "rm": False,
        "rota": False,
        "ro": False,
        "children": [],
    }


def controller(status="AVAILABLE"):
    return {
        "status": status,
        "pci_address": "0000:00:1f.2" if status == "AVAILABLE" else None,
        "error": None,
    }


def pci(status="AVAILABLE", class_code="010601"):
    return {
        "status": status,
        "pci_address": "0000:00:1f.2",
        "class_code": class_code if status == "AVAILABLE" else None,
        "driver": "ahci",
        "error": None,
    }


class StorageInventoryTests(unittest.TestCase):

    @patch(MODULE + ".classify_controller")
    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_sata_inventory(self, storage, discover, metadata, classify):
        storage.return_value = {
            "status": "AVAILABLE", "devices": [disk()], "error": None
        }
        discover.return_value = controller()
        metadata.return_value = pci()
        classify.return_value = {
            "status": "AVAILABLE", "controller_type": "SATA_AHCI"
        }

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(
            result["devices"][0]["classification"]["controller_type"],
            "SATA_AHCI",
        )

    @patch(MODULE + ".classify_controller")
    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_raid_inventory(self, storage, discover, metadata, classify):
        storage.return_value = {
            "status": "AVAILABLE", "devices": [disk()], "error": None
        }
        discover.return_value = controller()
        metadata.return_value = pci(class_code="010400")
        classify.return_value = {
            "status": "AVAILABLE",
            "controller_type": "RAID",
            "physical_disk_visibility": "CONTROLLER_DEPENDENT",
        }

        result = collect_storage_inventory()
        classification = result["devices"][0]["classification"]

        self.assertEqual(classification["controller_type"], "RAID")
        self.assertEqual(
            classification["physical_disk_visibility"],
            "CONTROLLER_DEPENDENT",
        )

    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_controller_unavailable(self, storage, discover, metadata):
        storage.return_value = {
            "status": "AVAILABLE", "devices": [disk()], "error": None
        }
        discover.return_value = controller("UNKNOWN")

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertIsNone(result["devices"][0]["pci"])
        self.assertIsNone(result["devices"][0]["classification"])
        metadata.assert_not_called()

    @patch(MODULE + ".classify_controller")
    @patch(MODULE + ".collect_pci_controller")
    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_pci_metadata_unavailable(
        self, storage, discover, metadata, classify
    ):
        storage.return_value = {
            "status": "AVAILABLE", "devices": [disk()], "error": None
        }
        discover.return_value = controller()
        metadata.return_value = pci("UNKNOWN")

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertIsNone(result["devices"][0]["classification"])
        classify.assert_not_called()

    @patch(MODULE + ".collect_storage")
    def test_discovery_failure(self, storage):
        storage.return_value = {
            "status": "UNKNOWN",
            "devices": [],
            "error": "lsblk unavailable",
        }

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["devices"], [])
        self.assertEqual(result["error"], "lsblk unavailable")

    @patch(MODULE + ".collect_storage")
    def test_invalid_device_collection(self, storage):
        storage.return_value = {
            "status": "AVAILABLE",
            "devices": "invalid",
            "error": None,
        }

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "UNKNOWN")

    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_non_disk_entries_skipped(self, storage, discover):
        storage.return_value = {
            "status": "AVAILABLE",
            "devices": [
                {"name": "sda1", "type": "part"},
                {"name": "loop0", "type": "loop"},
            ],
            "error": None,
        }

        result = collect_storage_inventory()

        self.assertEqual(result["devices"], [])
        discover.assert_not_called()

    @patch(MODULE + ".discover_controller")
    @patch(MODULE + ".collect_storage")
    def test_multiple_disks(self, storage, discover):
        storage.return_value = {
            "status": "AVAILABLE",
            "devices": [disk("sda"), disk("sdb")],
            "error": None,
        }
        discover.return_value = controller("UNKNOWN")

        result = collect_storage_inventory()

        self.assertEqual(len(result["devices"]), 2)
        self.assertEqual(
            [item["name"] for item in result["devices"]],
            ["sda", "sdb"],
        )

    @patch(MODULE + ".collect_storage")
    def test_empty_inventory(self, storage):
        storage.return_value = {
            "status": "AVAILABLE",
            "devices": [],
            "error": None,
        }

        result = collect_storage_inventory()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["devices"], [])


if __name__ == "__main__":
    unittest.main()
