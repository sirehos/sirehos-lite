"""Read-only crash evidence discovery for Sireh Doctor Benih 1.0."""

from datetime import datetime
import re
import subprocess
from pathlib import Path


CHECKS = {
    "previous_boot": "Previous Boot Analysis",
    "kernel": "Kernel Crash Analysis",
    "services": "Failed Services",
    "applications": "Application Crashes",
    "windows": "Windows Crash Evidence",
}

CRASH_PATTERN = re.compile(
    r"kernel panic|not syncing|kernel oops|BUG: unable to handle|"
    r"general protection fault|watchdog: BUG:|"
    r"out of memory: killed process|oom-killer|"
    r"machine check exception|hardware error",
    re.IGNORECASE,
)


def result(status, summary, details):
    return {
        "status": status,
        "summary": summary,
        "details": details,
    }


def command_output(args, timeout=12):
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout


def matching_lines(text, pattern=CRASH_PATTERN, limit=8):
    return [
        line.strip()[:300]
        for line in text.splitlines()
        if pattern.search(line)
    ][:limit]


def previous_boot():
    text = command_output(
        ["journalctl", "--no-pager", "-k", "-b", "-1", "-n", "3000"]
    )
    if text is None or not text.strip():
        return result(
            "UNKNOWN",
            "Previous Linux boot history is unavailable.",
            "This does not establish whether an installed OS crashed.",
        )

    matches = matching_lines(text)
    if matches:
        return result(
            "WARN",
            "Crash-related evidence found in previous Linux boot logs.",
            "\\n".join(matches),
        )

    return result(
        "INFO",
        "No recognized crash signatures in accessible previous-boot logs.",
        "Only the available Linux journal was examined.",
    )


def kernel():
    text = command_output(["dmesg", "--color=never"])
    if text is None or not text.strip():
        text = command_output(
            ["journalctl", "--no-pager", "-k", "-b", "0", "-n", "3000"]
        )

    if text is None or not text.strip():
        return result(
            "UNKNOWN",
            "Kernel crash logs could not be accessed.",
            "Insufficient evidence for a kernel crash assessment.",
        )

    matches = matching_lines(text)
    if matches:
        return result(
            "WARN",
            "Potential crash signatures found in current kernel logs.",
            "\\n".join(matches),
        )

    return result(
        "INFO",
        "No recognized crash signatures in accessible kernel logs.",
        "This covers the running Linux session, not an offline Windows OS.",
    )


def services():
    text = command_output(
        [
            "journalctl", "--no-pager", "-b", "0",
            "-o", "short-iso", "-n", "3000",
        ]
    )

    if text is None or not text.strip():
        return result(
            "UNKNOWN",
            "Service crash history is unavailable.",
            "System journal access was not sufficient.",
        )

    pattern = re.compile(
        r"Main process exited.*(code=dumped|status=11/SEGV|"
        r"status=6/ABRT)|code=dumped|core-dump",
        re.IGNORECASE,
    )
    matches = matching_lines(text, pattern)

    if matches:
        return result(
            "WARN",
            "Service process crash evidence was found.",
            "\\n".join(matches),
        )

    return result(
        "INFO",
        "No service process crash signatures found.",
        "Ordinary failed units were not counted as crashes.",
    )


def applications():
    found = []
    accessible = False

    for directory in (
        Path("/var/crash"),
        Path("/var/lib/systemd/coredump"),
    ):
        try:
            if not directory.is_dir():
                continue
            for entry in directory.iterdir():
                if entry.is_file() and (
                    entry.name.endswith((".crash", ".core", ".zst"))
                    or entry.name.startswith("core.")
                ):
                    found.append(str(entry))
                    if len(found) >= 20:
                        break
            accessible = True
        except (OSError, PermissionError):
            continue

    if found:
        descriptions = []
        for filename in found[:20]:
            artifact = Path(filename)
            name = artifact.name
            application = "UNKNOWN"

            if name.startswith("core."):
                parts = name.split(".")
                if len(parts) > 1 and parts[1]:
                    application = parts[1]
            elif name.endswith(".crash"):
                application = name.split(".")[0].split("_")[0]

            try:
                modified = datetime.fromtimestamp(
                    artifact.stat().st_mtime
                ).astimezone().strftime("%d %b %Y, %H:%M:%S %Z")
            except OSError:
                modified = "UNKNOWN"

            descriptions.append(
                "Application: {}\n"
                "Evidence: Crash artifact discovered\n"
                "File modified: {} (not necessarily crash time)\n"
                "Source: Running Linux installation\n"
                "Artifact: {}".format(
                    application, modified, artifact
                )
            )

        return result(
            "WARN",
            "Application crash artifacts were discovered; "
            "root cause is not established.",
            "\\n\\n".join(descriptions),
        )

    if accessible:
        return result(
            "INFO",
            "No application crash artifacts found in accessible locations.",
            "No core dumps were opened or executed.",
        )

    return result(
        "UNKNOWN",
        "Application crash storage was not accessible.",
        "No conclusion about application stability can be made.",
    )


def windows():
    roots = [Path("/media"), Path("/mnt"), Path("/run/media")]
    found = []
    inspected = 0

    for root in roots:
        if not root.is_dir():
            continue
        try:
            candidates = list(root.iterdir())
            for candidate in candidates:
                if candidate.is_dir():
                    candidates.extend(
                        child for child in candidate.iterdir()
                        if child.is_dir()
                    )
        except (OSError, PermissionError):
            continue

        for volume in candidates[:100]:
            try:
                windows_dir = volume / "Windows"
                if not windows_dir.is_dir():
                    continue
                inspected += 1

                dump = windows_dir / "MEMORY.DMP"
                if dump.is_file():
                    found.append(str(dump))

                minidump = windows_dir / "Minidump"
                if minidump.is_dir():
                    for item in minidump.iterdir():
                        if item.is_file() and item.suffix.lower() == ".dmp":
                            found.append(str(item))
                            if len(found) >= 20:
                                break
            except (OSError, PermissionError):
                continue

    if found:
        return result(
            "WARN",
            "Windows crash dump evidence was discovered.",
            "\\n".join(found[:20]),
        )

    if inspected:
        return result(
            "INFO",
            "No Windows crash dumps found in inspected mounted volumes.",
            "Windows dump decoding is planned for a later release.",
        )

    return result(
        "UNKNOWN",
        "No accessible mounted Windows installation was identified.",
        "Sireh Doctor did not mount or modify any partition.",
    )


RUNNERS = {
    "previous_boot": previous_boot,
    "kernel": kernel,
    "services": services,
    "applications": applications,
    "windows": windows,
}


def run_check(check_id):
    if check_id not in RUNNERS:
        raise ValueError("Unknown crash check: " + str(check_id))
    try:
        return RUNNERS[check_id]()
    except Exception:
        return result(
            "UNKNOWN",
            "Crash investigation could not complete.",
            "An unexpected diagnostic error occurred.",
        )
