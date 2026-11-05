"""Restricted SMART collection helper for Sireh Doctor.

This module is not privileged by itself. A future installation must place
the executable and its dependencies in root-controlled locations.
"""

import os
import re
import stat
import subprocess
import sys
from pathlib import Path


SMARTCTL = "/usr/sbin/smartctl"
DEVICE_PATTERN = re.compile(r"^/dev/[A-Za-z0-9_.-]+$")


def validate_device(device_path):
    """Accept an existing, direct, whole-disk block device."""

    if not isinstance(device_path, str):
        return False

    if not DEVICE_PATTERN.fullmatch(device_path):
        return False

    path = Path(device_path)

    try:
        details = path.lstat()
    except OSError:
        return False

    # Do not follow user-supplied symlinks.
    if not stat.S_ISBLK(details.st_mode):
        return False

    name = path.name
    sysfs_path = Path("/sys/class/block") / name

    if not sysfs_path.exists():
        return False

    # Reject kernel virtual block devices, including loop and dm devices.
    try:
        resolved_sysfs = sysfs_path.resolve(strict=True)
        virtual_root = Path("/sys/devices/virtual/block").resolve(
            strict=True
        )
    except OSError:
        return False

    if resolved_sysfs == virtual_root or virtual_root in resolved_sysfs.parents:
        return False

    # Partitions expose a 'partition' attribute in sysfs.
    if (sysfs_path / "partition").exists():
        return False

    # Require the kernel's device number to match /dev.
    try:
        major_minor = (sysfs_path / "dev").read_text().strip()
        expected = "{}:{}".format(
            os.major(details.st_rdev),
            os.minor(details.st_rdev),
        )
    except (OSError, ValueError):
        return False

    return major_minor == expected


def run_smart(device_path, timeout=20):
    """Run one fixed SMART information query without a shell."""

    if not validate_device(device_path):
        return 64, "", "Invalid or unsupported whole-disk device"

    try:
        completed = subprocess.run(
            [SMARTCTL, "--json=c", "-a", device_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 69, "", "SMART utility unavailable"
    except subprocess.TimeoutExpired:
        return 124, "", "SMART query timed out"
    except OSError:
        return 70, "", "SMART query could not start"

    return completed.returncode, completed.stdout, completed.stderr


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1:
        print("Exactly one disk device is required", file=sys.stderr)
        return 64

    exit_code, stdout, stderr = run_smart(argv[0])

    if stdout:
        sys.stdout.write(stdout)

    if stderr:
        sys.stderr.write(stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
