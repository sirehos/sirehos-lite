"""Read-only Linux storage device and partition discovery."""

import json
import subprocess


LSBLK_COLUMNS = (
    "NAME,PATH,TYPE,SIZE,MODEL,TRAN,ROTA,RM,RO,"
    "FSTYPE,MOUNTPOINTS"
)


def collect_storage():
    """Collect block-device metadata without modifying storage."""
    command = [
        "lsblk",
        "--json",
        "--bytes",
        "--output",
        LSBLK_COLUMNS,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "UNKNOWN",
            "devices": [],
            "error": str(exc),
        }

    if result.returncode != 0:
        return {
            "status": "UNKNOWN",
            "devices": [],
            "error": result.stderr.strip() or "lsblk failed",
        }

    try:
        payload = json.loads(result.stdout)
        devices = payload["blockdevices"]

        if not isinstance(devices, list):
            raise ValueError("Invalid block device collection")

    except (ValueError, KeyError, TypeError) as exc:
        return {
            "status": "UNKNOWN",
            "devices": [],
            "error": f"Invalid lsblk output: {exc}",
        }

    return {
        "status": "AVAILABLE",
        "devices": devices,
        "error": None,
    }
