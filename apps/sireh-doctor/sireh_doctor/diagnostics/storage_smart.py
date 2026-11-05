"""Read-only SMART collection for Sireh Doctor."""

import json
import os
import stat
import subprocess


def _valid_device_path(device_path):
    """Accept only existing block devices directly under /dev."""
    if not isinstance(device_path, str):
        return False

    if (
        not device_path.startswith("/dev/")
        or device_path == "/dev/"
        or any(character.isspace() for character in device_path)
    ):
        return False

    if os.path.normpath(device_path) != device_path:
        return False

    if os.path.dirname(device_path) != "/dev":
        return False

    try:
        details = os.stat(device_path)
    except (OSError, ValueError):
        return False

    return stat.S_ISBLK(details.st_mode)


def collect_smart(device_path, timeout=20):
    """Collect SMART JSON without initiating tests or repairs."""
    result = {
        "status": "UNKNOWN",
        "device": device_path,
        "data": None,
        "exit_code": None,
        "error": None,
    }

    if not _valid_device_path(device_path):
        result["error"] = "Invalid or unavailable block device"
        return result

    try:
        completed = subprocess.run(
            ["smartctl", "--json=c", "-a", device_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        result["error"] = "smartctl is not installed"
        return result
    except subprocess.TimeoutExpired:
        result["error"] = "SMART query timed out"
        return result
    except OSError as exc:
        result["error"] = "SMART query could not start: {}".format(exc)
        return result

    result["exit_code"] = completed.returncode

    try:
        data = json.loads(completed.stdout)
    except (ValueError, TypeError):
        result["error"] = "SMART utility returned invalid JSON"
        return result

    if not isinstance(data, dict):
        result["error"] = "SMART utility returned unexpected data"
        return result

    metadata = data.get("smartctl")

    if not isinstance(metadata, dict):
        result["error"] = "SMART utility metadata missing or invalid"
        return result

    messages = metadata.get("messages", [])

    if not isinstance(messages, list):
        result["error"] = "SMART utility messages malformed"
        return result

    message_parts = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        value = message.get("string")

        if isinstance(value, str):
            message_parts.append(value.lower())

    message_text = " ".join(message_parts)

    result["data"] = data

    if "permission denied" in message_text:
        result["status"] = "PERMISSION_REQUIRED"
        result["error"] = "Administrator permission required for SMART access"
    elif completed.returncode < 0:
        result["error"] = "SMART utility terminated unexpectedly"
    elif completed.returncode & 3:
        result["error"] = "SMART device access or command failed"
    elif completed.returncode > 255:
        result["error"] = "SMART utility returned an invalid exit status"
    else:
        result["status"] = "AVAILABLE"

    return result
