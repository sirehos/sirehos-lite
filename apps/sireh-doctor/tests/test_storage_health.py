"""Regression tests for Storage Doctor metadata assessments."""

import unittest

from sireh_doctor.diagnostics.storage_health import (
    assess,
    assess_device,
    assess_partitions,
    assess_filesystems,
)


def sample_disk():
    return {
        "name": "sda",
        "path": "/dev/sda",
        "type": "disk",
        "model": "Samsung SSD",
        "size": 512110190592,
        "children": [
            {
                "name": "sda1",
                "type": "part",
                "fstype": "vfat",
                "mountpoints": ["/boot/efi"],
            },
            {
                "name": "sda2",
                "type": "part",
                "fstype": "ext4",
                "mountpoints": ["/"],
            },
        ],
    }


class StorageHealthTests(unittest.TestCase):

    def test_valid_disk_is_informational(self):
        result = assess_device(sample_disk())
        self.assertEqual(result["status"], "INFO")
        self.assertIn("Samsung SSD", result["summary"])

    def test_invalid_capacity_is_unknown(self):
        disk = sample_disk()
        disk["size"] = 0
        self.assertEqual(assess_device(disk)["status"], "UNKNOWN")

    def test_boolean_capacity_is_rejected(self):
        disk = sample_disk()
        disk["size"] = True
        self.assertEqual(assess_device(disk)["status"], "UNKNOWN")

    def test_non_disk_is_unknown(self):
        disk = sample_disk()
        disk["type"] = "part"
        self.assertEqual(assess_device(disk)["status"], "UNKNOWN")

    def test_partition_count(self):
        result = assess_partitions(sample_disk())
        self.assertEqual(result["status"], "INFO")
        self.assertIn("2 partition(s)", result["summary"])

    def test_missing_partitions_is_unknown(self):
        disk = sample_disk()
        disk.pop("children")
        self.assertEqual(
            assess_partitions(disk)["status"], "UNKNOWN"
        )

    def test_malformed_partitions_is_unknown(self):
        disk = sample_disk()
        disk["children"] = "invalid"
        self.assertEqual(
            assess_partitions(disk)["status"], "UNKNOWN"
        )

    def test_unpartitioned_disk_is_informational(self):
        disk = sample_disk()
        disk["children"] = []
        result = assess_partitions(disk)
        self.assertEqual(result["status"], "INFO")
        self.assertIn("0 partition(s)", result["summary"])

    def test_filesystem_detection(self):
        result = assess_filesystems(sample_disk())
        self.assertEqual(result["status"], "INFO")
        self.assertIn("ext4", result["summary"])
        self.assertIn("vfat", result["summary"])

    def test_unknown_filesystem(self):
        disk = sample_disk()
        disk["children"] = []
        result = assess_filesystems(disk)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_discovery_failure(self):
        result = assess({
            "status": "UNKNOWN",
            "devices": [],
            "error": "lsblk unavailable",
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "UNKNOWN")
        self.assertIn("lsblk unavailable", result[0]["recommendation"])

    def test_complete_disk_assessment(self):
        result = assess({
            "status": "AVAILABLE",
            "devices": [sample_disk()],
        })
        self.assertEqual(len(result), 3)
        self.assertTrue(
            all(item["status"] == "INFO" for item in result)
        )

    def test_no_disks(self):
        result = assess({
            "status": "AVAILABLE",
            "devices": [],
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "UNKNOWN")

    def test_invalid_device_collection(self):
        result = assess({
            "status": "AVAILABLE",
            "devices": "invalid",
        })
        self.assertEqual(result[0]["status"], "UNKNOWN")

    def test_non_disk_entries_ignored(self):
        result = assess({
            "status": "AVAILABLE",
            "devices": [
                {"type": "loop", "path": "/dev/loop0"},
                sample_disk(),
            ],
        })
        self.assertEqual(len(result), 3)

    def test_finding_contract(self):
        result = assess_device(sample_disk())
        self.assertEqual(
            set(result),
            {
                "component",
                "check",
                "status",
                "summary",
                "recommendation",
            },
        )


if __name__ == "__main__":
    unittest.main()
