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



HELPER_PATH = "/usr/libexec/sireh-doctor/sireh-smart-helper"


def _trusted_helper():
    """Require a root-owned, non-writable installation chain."""
    components = (
        "/usr",
        "/usr/libexec",
        "/usr/libexec/sireh-doctor",
        HELPER_PATH,
    )

    try:
        for path in components:
            info = os.lstat(path)

            if info.st_uid != 0 or info.st_mode & 0o022:
                return False, "Native SMART helper installation is untrusted"

            if path == HELPER_PATH:
                if not stat.S_ISREG(info.st_mode):
                    return False, "Native SMART helper installation is untrusted"
                if not info.st_mode & 0o111:
                    return False, "Native SMART helper is not executable"
            elif not stat.S_ISDIR(info.st_mode):
                return False, "Native SMART helper installation is untrusted"

    except FileNotFoundError:
        return False, "Native SMART helper is not installed"
    except OSError:
        return False, "Cannot verify native SMART helper"

    return True, None


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

    trusted, helper_error = _trusted_helper()

    if not trusted:
        result["error"] = helper_error
        return result

    # Never elevate or execute development-tree helpers here.
    try:
        completed = subprocess.run(
            [HELPER_PATH, device_path],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
    except FileNotFoundError:
        result["error"] = "Native SMART helper is unavailable"
        return result
    except subprocess.TimeoutExpired:
        result["error"] = "SMART query timed out"
        return result
    except OSError:
        result["error"] = "Native SMART helper could not start"
        return result

    if completed.returncode != 0:
        if completed.returncode == 77:
            result["status"] = "PERMISSION_REQUIRED"
            result["error"] = (
                "Administrator permission required for SMART access"
            )
        else:
            result["error"] = (
                "Native SMART helper failed with exit code {}"
                .format(completed.returncode)
            )
        return result

    # Bound JSON input before parsing. A separate process-level
    # output cap is required before enabling privileged execution.
    if len(completed.stdout.encode("utf-8")) > 2 * 1024 * 1024:
        result["error"] = "SMART utility output exceeds safety limit"
        return result

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

    smart_exit = metadata.get("exit_status")

    if (
        type(smart_exit) is not int
        or not 0 <= smart_exit <= 255
    ):
        result["error"] = "SMART diagnostic exit status missing or invalid"
        return result

    result["exit_code"] = smart_exit

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
    elif smart_exit < 0:
        result["error"] = "SMART utility terminated unexpectedly"
    elif smart_exit & 3:
        result["error"] = "SMART device access or command failed"
    elif smart_exit > 255:
        result["error"] = "SMART utility returned an invalid exit status"
    else:
        result["status"] = "AVAILABLE"

    return result
