"""Regression tests for read-only storage discovery."""

import json
import subprocess
import unittest
from unittest.mock import patch

from sireh_doctor.diagnostics.storage import collect_storage


class StorageDiscoveryTests(unittest.TestCase):

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_successful_discovery(self, run):
        devices = [{
            "name": "sda",
            "path": "/dev/sda",
            "type": "disk",
            "size": 512110190592,
            "children": [{"name": "sda1", "type": "part"}],
        }]
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps({"blockdevices": devices}), ""
        )

        result = collect_storage()

        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["devices"], devices)
        self.assertIsNone(result["error"])
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][0], "lsblk")
        self.assertTrue(run.call_args.kwargs["capture_output"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_empty_device_list(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, '{"blockdevices": []}', ""
        )
        result = collect_storage()
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["devices"], [])

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_invalid_json(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "not-json", ""
        )
        result = collect_storage()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["devices"], [])
        self.assertIn("Invalid lsblk output", result["error"])

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_missing_blockdevices_key(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, '{"unexpected": []}', ""
        )
        self.assertEqual(collect_storage()["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_invalid_device_collection_type(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, '{"blockdevices": {}}', ""
        )
        self.assertEqual(collect_storage()["status"], "UNKNOWN")

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_nonzero_exit_code(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "device discovery failed"
        )
        result = collect_storage()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("device discovery failed", result["error"])

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_missing_executable(self, run):
        run.side_effect = FileNotFoundError("lsblk not installed")
        result = collect_storage()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["devices"], [])

    @patch("sireh_doctor.diagnostics.storage.subprocess.run")
    def test_timeout(self, run):
        run.side_effect = subprocess.TimeoutExpired(["lsblk"], 10)
        result = collect_storage()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()
