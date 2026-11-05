"""SMART collector robustness and safety tests."""

import json
import subprocess
import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_smart import collect_smart


class SmartEdgeCaseTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._device_patch = patch(
            "sireh_doctor.diagnostics.storage_smart._valid_device_path",
            side_effect=lambda value: value == "/dev/sda",
        )
        cls._device_patch.start()
        cls._helper_patch = patch(
            "sireh_doctor.diagnostics.storage_smart._trusted_helper",
            return_value=(True, None),
        )
        cls._helper_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._helper_patch.stop()
        cls._device_patch.stop()


    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_null_smartctl_metadata(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps({"smartctl": None}), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_malformed_messages(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 2, json.dumps({"smartctl": {"messages": None}}), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_missing_smartctl_metadata(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps({"device": {"name": "/dev/sda"}}), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_command_line_parse_error(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps({"smartctl": {"exit_status": 1}}), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_reject_path_traversal(self, run):
        result = collect_smart("/dev/../etc/passwd")
        self.assertEqual(result["status"], "UNKNOWN")
        run.assert_not_called()

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_reject_non_device_path(self, run):
        result = collect_smart("/dev/not-a-real-device")
        self.assertEqual(result["status"], "UNKNOWN")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
