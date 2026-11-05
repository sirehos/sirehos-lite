"""Regression tests for PCI controller classification."""

import unittest

from sireh_doctor.diagnostics.storage_classify import classify_controller


class StorageClassificationTests(unittest.TestCase):

    def test_sata_ahci(self):
        result = classify_controller("010601")
        self.assertEqual(result["controller_type"], "SATA_AHCI")
        self.assertEqual(result["status"], "AVAILABLE")

    def test_nvme(self):
        result = classify_controller("010802")
        self.assertEqual(result["controller_type"], "NVME")

    def test_raid(self):
        result = classify_controller("010400")
        self.assertEqual(result["controller_type"], "RAID")

    def test_raid_visibility_not_assumed(self):
        result = classify_controller("010400")
        self.assertEqual(
            result["physical_disk_visibility"],
            "CONTROLLER_DEPENDENT",
        )

    def test_sas(self):
        result = classify_controller("010700")
        self.assertEqual(result["controller_type"], "SAS")

    def test_ide(self):
        result = classify_controller("010100")
        self.assertEqual(result["controller_type"], "IDE")

    def test_usb_host(self):
        result = classify_controller("0c0330")
        self.assertEqual(result["controller_type"], "USB_HOST")
        self.assertEqual(
            result["physical_disk_visibility"],
            "BRIDGE_DEPENDENT",
        )

    def test_other_pci_device(self):
        result = classify_controller("020000")
        self.assertEqual(result["controller_type"], "OTHER")
        self.assertEqual(result["status"], "AVAILABLE")

    def test_case_insensitive(self):
        result = classify_controller("0C0330")
        self.assertEqual(result["controller_type"], "USB_HOST")
        self.assertEqual(result["class_code"], "0c0330")

    def test_invalid_codes(self):
        for code in (None, "", "invalid", "01060", "01060100", 10601):
            with self.subTest(code=code):
                result = classify_controller(code)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(result["controller_type"], "UNKNOWN")

    def test_unknown_visibility_not_assumed(self):
        result = classify_controller(None)
        self.assertEqual(
            result["physical_disk_visibility"], "UNKNOWN"
        )

    def test_sata_visibility_not_assessed(self):
        result = classify_controller("010601")
        self.assertEqual(
            result["physical_disk_visibility"], "NOT_ASSESSED"
        )


if __name__ == "__main__":
    unittest.main()
