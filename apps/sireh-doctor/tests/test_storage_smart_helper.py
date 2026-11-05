"""Security tests for the restricted SMART helper."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sireh_doctor.diagnostics import storage_smart_helper as helper


class SmartHelperSecurityTests(unittest.TestCase):


    def test_rejects_invalid_paths(self):
        invalid = (
            "",
            "/dev/",
            "/dev/../etc/passwd",
            "/dev/disk/by-id/example",
            "/etc/passwd",
            "/dev/sda;id",
            "/dev/sda --test",
            "/dev/sda\nwhoami",
            "/dev/sda/../../tmp",
            "/dev/$(id)",
            "/dev/sda|cat",
        )

        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(helper.validate_device(value))

    def test_rejects_non_block_devices(self):
        self.assertFalse(helper.validate_device("/dev/null"))
        self.assertFalse(helper.validate_device("/dev/zero"))

    def test_rejects_symlink(self):
        self.assertFalse(helper.validate_device("/dev/disk"))

    def test_rejects_virtual_loop_devices(self):
        for name in ("loop0", "loop1"):
            device = Path("/dev") / name

            if device.exists():
                with self.subTest(device=str(device)):
                    self.assertFalse(
                        helper.validate_device(str(device))
                    )

    def test_rejects_partition_when_available(self):
        with patch.object(helper.Path, "exists", return_value=True):
            with patch.object(helper.Path, "lstat") as mocked_stat:
                mocked_stat.return_value.st_mode = 0
                self.assertFalse(helper.validate_device("/dev/sda1"))

    def test_rejects_extra_arguments(self):
        self.assertEqual(helper.main([]), 64)
        self.assertEqual(helper.main(["/dev/sda", "--test"]), 64)

    @patch.object(helper, "validate_device", return_value=True)
    @patch.object(helper.subprocess, "run")
    def test_fixed_command_arguments(self, mocked_run, mocked_validate):
        mocked_run.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"smartctl": {}}',
            stderr="",
        )

        code, stdout, stderr = helper.run_smart("/dev/sda")

        self.assertEqual(code, 0)
        self.assertEqual(stdout, '{"smartctl": {}}')
        self.assertEqual(stderr, "")

        mocked_run.assert_called_once_with(
            [
                "/usr/sbin/smartctl",
                "--json=c",
                "-a",
                "/dev/sda",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    @patch.object(helper.subprocess, "run")
    def test_invalid_device_never_runs_smartctl(self, mocked_run):
        code, _, _ = helper.run_smart("/dev/sda;id")

        self.assertEqual(code, 64)
        mocked_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
