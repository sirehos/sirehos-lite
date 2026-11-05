"""Regression tests for PCI storage-controller metadata."""

import tempfile
import unittest
from pathlib import Path

from sireh_doctor.diagnostics.storage_pci import collect_pci_controller


class StoragePciTests(unittest.TestCase):

    def _make_controller(
        self, root, address="0000:00:1f.2",
        class_code="0x010601", driver="ahci"
    ):
        directory = root / address
        directory.mkdir(parents=True)

        fields = {
            "vendor": "0x8086",
            "device": "0x9c83",
            "subsystem_vendor": "0x17aa",
            "subsystem_device": "0x5034",
            "class": class_code,
            "revision": "0x03",
        }

        for name, value in fields.items():
            (directory / name).write_text(value + "\n")

        if driver:
            driver_directory = root / "drivers" / driver
            driver_directory.mkdir(parents=True, exist_ok=True)
            (directory / "driver").symlink_to(
                driver_directory, target_is_directory=True
            )

        return directory

    def test_sata_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_controller(root)
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["vendor_id"], "8086")
        self.assertEqual(result["device_id"], "9c83")
        self.assertEqual(result["class_code"], "010601")
        self.assertEqual(result["driver"], "ahci")

    def test_nvme_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_controller(
                root, class_code="0x010802", driver="nvme"
            )
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["class_code"], "010802")
        self.assertEqual(result["driver"], "nvme")

    def test_raid_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_controller(
                root, class_code="0x010400", driver="megaraid_sas"
            )
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["class_code"], "010400")
        self.assertEqual(result["driver"], "megaraid_sas")

    def test_missing_driver_is_not_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_controller(root, driver=None)
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertIsNone(result["driver"])

    def test_missing_required_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = self._make_controller(root)
            (directory / "vendor").unlink()
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_malformed_hex_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = self._make_controller(root)
            (directory / "device").write_text("invalid")
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_missing_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=temporary
            )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_addresses(self):
        for address in (
            "../etc",
            "/dev/sda",
            "0000:00:1f:2",
            "",
            None,
        ):
            with self.subTest(address=address):
                result = collect_pci_controller(address)
                self.assertEqual(result["status"], "UNKNOWN")

    def test_result_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_controller(root)
            result = collect_pci_controller(
                "0000:00:1f.2", pci_root=root
            )

        self.assertEqual(
            set(result),
            {
                "status",
                "pci_address",
                "vendor_id",
                "device_id",
                "subsystem_vendor_id",
                "subsystem_device_id",
                "class_code",
                "revision",
                "driver",
                "error",
            },
        )


if __name__ == "__main__":
    unittest.main()
