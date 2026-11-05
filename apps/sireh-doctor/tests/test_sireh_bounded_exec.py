"""Regression tests for the unprivileged bounded-execution harness."""

from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "packaging"
    / "sireh-bounded-exec.c"
)


class BoundedExecutionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(
            prefix="sireh-bounded-tests-"
        )
        cls.binary = Path(cls.workspace.name) / "bounded"

        try:
            result = subprocess.run(
                [
                    "/usr/bin/gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    str(SOURCE),
                    "-o",
                    str(cls.binary),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            if result.returncode != 0:
                raise AssertionError(result.stderr)
        except BaseException:
            cls.workspace.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def run_case(self, argument):
        return subprocess.run(
            [str(self.binary), argument],
            capture_output=True,
            timeout=8,
            check=False,
        )

    def test_normal_execution(self):
        result = self.run_case("normal")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"SIREH_BOUNDED_OK")

    def test_oversized_output_rejected_without_leakage(self):
        result = self.run_case("large")
        self.assertEqual(result.returncode, 75)
        self.assertEqual(result.stdout, b"")

    def test_timeout_rejected_without_leakage(self):
        result = self.run_case("slow")
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
