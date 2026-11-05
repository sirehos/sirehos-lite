"""Regression tests for SMART collection."""

import json
import subprocess
import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_smart import collect_smart


class SmartCollectorTests(unittest.TestCase):

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
    def test_success(self, run):
        payload = {
            "smartctl": {"exit_status": 0},
            "smart_status": {"passed": True},
        }
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps(payload), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertTrue(result["data"]["smart_status"]["passed"])
        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0],
            ["/usr/libexec/sireh-doctor/sireh-smart-helper",
             "/dev/sda"],
        )

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_permission_denied(self, run):
        payload = {
            "smartctl": {
                "exit_status": 2,
                "messages": [
                    {"string": "Permission denied", "severity": "error"}
                ],
            }
        }
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps(payload), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "PERMISSION_REQUIRED")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_smart_health_failure_exit_bit(self, run):
        payload = {
            "smartctl": {"exit_status": 8},
            "smart_status": {"passed": False},
        }
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps(payload), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["exit_code"], 8)

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_missing_executable(self, run):
        run.side_effect = FileNotFoundError()
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("unavailable", result["error"])

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_timeout(self, run):
        run.side_effect = subprocess.TimeoutExpired("smartctl", 20)
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("timed out", result["error"])

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_invalid_json(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "invalid-json", ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_non_object_json(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "[]", ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_device_access_failure(self, run):
        payload = {"smartctl": {"exit_status": 2}}
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps(payload), ""
        )
        result = collect_smart("/dev/sda")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("access", result["error"])

    @patch("sireh_doctor.diagnostics.storage_smart.subprocess.run")
    def test_invalid_device_path(self, run):
        result = collect_smart("/dev/")
        self.assertEqual(result["status"], "UNKNOWN")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
