"""Simulated kernel-device validation tests for SMART helper."""

import os
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sireh_doctor.diagnostics import storage_smart_helper as helper


class SmartHelperDeviceFixtureTests(unittest.TestCase):

    def check_device(
        self,
        name,
        kernel_target,
        device_number,
        kernel_number=None,
        partition=False,
        block=True,
    ):
        """Exercise actual validation with simulated device metadata."""

        if kernel_number is None:
            kernel_number = device_number

        device_path = "/dev/" + name
        sysfs_path = Path("/sys/class/block") / name
        virtual_root = Path("/sys/devices/virtual/block")

        original_exists = Path.exists
        original_resolve = Path.resolve
        original_read_text = Path.read_text

        def fake_exists(path):
            if path == sysfs_path:
                return True
            if path == sysfs_path / "partition":
                return partition
            return original_exists(path)

        def fake_resolve(path, *args, **kwargs):
            if path == sysfs_path:
                return Path(kernel_target)
            if path == virtual_root:
                return virtual_root
            return original_resolve(path, *args, **kwargs)

        def fake_read_text(path, *args, **kwargs):
            if path == sysfs_path / "dev":
                return kernel_number + "\n"
            return original_read_text(path, *args, **kwargs)

        major, minor = map(int, device_number.split(":"))

        details = SimpleNamespace(
            st_mode=stat.S_IFBLK if block else stat.S_IFREG,
            st_rdev=os.makedev(major, minor),
        )

        with (
            patch.object(Path, "lstat", return_value=details),
            patch.object(Path, "exists", autospec=True,
                         side_effect=fake_exists),
            patch.object(Path, "resolve", autospec=True,
                         side_effect=fake_resolve),
            patch.object(Path, "read_text", autospec=True,
                         side_effect=fake_read_text),
        ):
            return helper.validate_device(device_path)

    def test_sata_whole_disk_accepted(self):
        self.assertTrue(self.check_device(
            "sda",
            "/sys/devices/pci0000:00/block/sda",
            "8:0",
        ))

    def test_nvme_whole_disk_accepted(self):
        self.assertTrue(self.check_device(
            "nvme0n1",
            "/sys/devices/pci0000:00/nvme/nvme0n1",
            "259:0",
        ))

    def test_partition_rejected(self):
        self.assertFalse(self.check_device(
            "sda1",
            "/sys/devices/pci0000:00/block/sda/sda1",
            "8:1",
            partition=True,
        ))

    def test_virtual_loop_rejected(self):
        self.assertFalse(self.check_device(
            "loop0",
            "/sys/devices/virtual/block/loop0",
            "7:0",
        ))

    def test_device_number_mismatch_rejected(self):
        self.assertFalse(self.check_device(
            "sda",
            "/sys/devices/pci0000:00/block/sda",
            "8:0",
            kernel_number="8:1",
        ))

    def test_non_block_device_rejected(self):
        self.assertFalse(self.check_device(
            "sda",
            "/sys/devices/pci0000:00/block/sda",
            "8:0",
            block=False,
        ))


if __name__ == "__main__":
    unittest.main()
