"""Privilege-boundary regression tests for SMART collection."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sireh_doctor.diagnostics import storage_smart_helper as helper


class SmartPrivilegeBoundaryTests(unittest.TestCase):

    @patch.object(helper, "validate_device", return_value=False)
    @patch.object(helper.subprocess, "run")
    def test_rejected_device_never_executes_smartctl(
        self, mocked_run, mocked_validate
    ):
        code, stdout, stderr = helper.run_smart("/dev/sda")

        self.assertEqual(code, 64)
        self.assertEqual(stdout, "")
        self.assertIn("Invalid", stderr)
        mocked_run.assert_not_called()

    @patch.object(helper, "validate_device", return_value=True)
    @patch.object(helper.subprocess, "run")
    def test_approved_device_uses_fixed_executable(
        self, mocked_run, mocked_validate
    ):
        mocked_run.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"smartctl": {}}',
            stderr="",
        )

        code, stdout, stderr = helper.run_smart("/dev/nvme0n1")

        self.assertEqual(code, 0)
        self.assertEqual(stdout, '{"smartctl": {}}')
        self.assertEqual(stderr, "")

        args, kwargs = mocked_run.call_args

        self.assertEqual(args[0], [
            "/usr/sbin/smartctl",
            "--json=c",
            "-a",
            "/dev/nvme0n1",
        ])
        self.assertNotIn("shell", kwargs)

    @patch.object(helper, "validate_device", return_value=True)
    @patch.object(helper.subprocess, "run")
    def test_smart_timeout_is_bounded(
        self, mocked_run, mocked_validate
    ):
        import subprocess

        mocked_run.side_effect = subprocess.TimeoutExpired(
            cmd="smartctl", timeout=20
        )

        code, stdout, stderr = helper.run_smart("/dev/sda")

        self.assertEqual(code, 124)
        self.assertEqual(stdout, "")
        self.assertIn("timed out", stderr.lower())


if __name__ == "__main__":
    unittest.main()
