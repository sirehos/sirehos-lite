"""Regression tests for storage controller discovery."""

import tempfile
import unittest
from pathlib import Path

from sireh_doctor.diagnostics.storage_controller import (
    PCI_ADDRESS,
    discover_controller,
)


class StorageControllerTests(unittest.TestCase):

    def test_valid_pci_addresses(self):
        for address in (
            "0000:00:1f.2",
            "0000:01:00.0",
            "0000:3b:1a.7",
        ):
            with self.subTest(address=address):
                self.assertIsNotNone(PCI_ADDRESS.fullmatch(address))

    def test_invalid_pci_addresses(self):
        for address in (
            "0000:00:1f:2",
            "0000:00:20.0",
            "0000:00:1fX2",
            "invalid",
        ):
            with self.subTest(address=address):
                self.assertIsNone(PCI_ADDRESS.fullmatch(address))

    def _discover_from_path(self, hardware_path):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            disk = root / "block" / "sda"
            disk.mkdir(parents=True)

            hardware = root / "devices" / hardware_path
            hardware.mkdir(parents=True)

            (disk / "device").symlink_to(
                hardware, target_is_directory=True
            )

            return discover_controller(
                "sda", sysfs_root=str(root / "block")
            )

    def test_sata_controller(self):
        result = self._discover_from_path(
            "pci0000:00/0000:00:1f.2/ata1/host0"
        )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["pci_address"], "0000:00:1f.2")

    def test_nvme_controller(self):
        result = self._discover_from_path(
            "pci0000:00/0000:01:00.0/nvme/nvme0"
        )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["pci_address"], "0000:01:00.0")

    def test_nearest_pci_device_selected(self):
        result = self._discover_from_path(
            "pci0000:00/0000:00:1c.0/0000:03:00.0/host0"
        )
        self.assertEqual(result["pci_address"], "0000:03:00.0")

    def test_no_pci_controller(self):
        result = self._discover_from_path(
            "platform/example/host0"
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["pci_address"])

    def test_missing_device(self):
        with tempfile.TemporaryDirectory() as directory:
            result = discover_controller(
                "missing", sysfs_root=directory
            )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_device_names(self):
        for name in (
            "../sda",
            "/dev/sda",
            "sda/../../etc",
            "",
            None,
        ):
            with self.subTest(name=name):
                result = discover_controller(name)
                self.assertEqual(result["status"], "UNKNOWN")

    def test_result_contract(self):
        result = self._discover_from_path(
            "pci0000:00/0000:00:1f.2/ata1"
        )
        self.assertEqual(
            set(result),
            {
                "status",
                "device",
                "pci_address",
                "hardware_path",
                "error",
            },
        )


if __name__ == "__main__":
    unittest.main()
