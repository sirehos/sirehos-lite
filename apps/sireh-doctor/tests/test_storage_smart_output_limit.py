"""Regression tests for SMART JSON output limits."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sireh_doctor.diagnostics.storage_smart import collect_smart


class SmartOutputLimitTests(unittest.TestCase):

    def collect_mocked(self, output):
        fake = SimpleNamespace(
            stdout=output,
            stderr="",
            returncode=0,
        )

        with patch(
            "sireh_doctor.diagnostics.storage_smart._trusted_helper",
            return_value=(True, None),
        ), patch(
            "sireh_doctor.diagnostics.storage_smart._valid_device_path",
            return_value=True,
        ), patch(
            "sireh_doctor.diagnostics.storage_smart.subprocess.run",
            return_value=fake,
        ):
            return collect_smart("/dev/sda")

    def test_normal_json_is_accepted(self):
        result = self.collect_mocked(
            '{"smartctl":{"version":[7,4],"exit_status":0,"messages":[]}}'
        )
        self.assertEqual(result["status"], "AVAILABLE")

    def test_oversized_json_is_rejected(self):
        output = (
            '{"smartctl":{"messages":[],"padding":"'
            + ("X" * (2 * 1024 * 1024))
            + '"}}'
        )

        result = self.collect_mocked(output)

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["error"],
            "SMART utility output exceeds safety limit",
        )


if __name__ == "__main__":
    unittest.main()
