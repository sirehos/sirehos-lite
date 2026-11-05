"""Portable tests for SMART block-device validation."""

import os
import stat
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_smart import _valid_device_path


class SmartDeviceValidationTests(unittest.TestCase):

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_sata_disk(self, mock_stat):
        mock_stat.return_value = SimpleNamespace(st_mode=stat.S_IFBLK)
        self.assertTrue(_valid_device_path("/dev/sda"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_nvme_disk(self, mock_stat):
        mock_stat.return_value = SimpleNamespace(st_mode=stat.S_IFBLK)
        self.assertTrue(_valid_device_path("/dev/nvme0n1"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_usb_disk(self, mock_stat):
        mock_stat.return_value = SimpleNamespace(st_mode=stat.S_IFBLK)
        self.assertTrue(_valid_device_path("/dev/sdb"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_regular_file_rejected(self, mock_stat):
        mock_stat.return_value = SimpleNamespace(st_mode=stat.S_IFREG)
        self.assertFalse(_valid_device_path("/dev/fakefile"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_missing_device_rejected(self, mock_stat):
        mock_stat.side_effect = FileNotFoundError()
        self.assertFalse(_valid_device_path("/dev/missing"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_permission_error_rejected(self, mock_stat):
        mock_stat.side_effect = PermissionError()
        self.assertFalse(_valid_device_path("/dev/sda"))

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_traversal_rejected(self, mock_stat):
        self.assertFalse(_valid_device_path("/dev/../etc/passwd"))
        mock_stat.assert_not_called()

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_nested_path_rejected(self, mock_stat):
        self.assertFalse(_valid_device_path("/dev/disk/by-id/example"))
        mock_stat.assert_not_called()

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_whitespace_rejected(self, mock_stat):
        self.assertFalse(_valid_device_path("/dev/sda bad"))
        mock_stat.assert_not_called()

    @patch("sireh_doctor.diagnostics.storage_smart.os.stat")
    def test_relative_path_rejected(self, mock_stat):
        self.assertFalse(_valid_device_path("sda"))
        mock_stat.assert_not_called()

    def test_invalid_types_rejected(self):
        for value in (None, 123, [], {}):
            with self.subTest(value=value):
                self.assertFalse(_valid_device_path(value))


if __name__ == "__main__":
    unittest.main()
