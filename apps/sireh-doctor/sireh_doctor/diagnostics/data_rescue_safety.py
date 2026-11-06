"""Conservative source eligibility checks for Sireh Doctor Data Rescue.

B016 Benih 1.0: no mounting, repair, or source writes.
"""

from pathlib import Path


def _unescape_mount_path(value):
    """Decode mountinfo's octal-escaped path characters."""
    import re

    return re.sub(
        r"\\([0-7]{3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


def read_mountinfo(path="/proc/self/mountinfo"):
    """Read current mount metadata without changing mount state."""
    records = []

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if " - " not in line:
            continue

        left, right = line.split(" - ", 1)
        fields = left.split()
        details = right.split()

        if len(fields) < 6 or len(details) < 2:
            continue

        options = fields[5].split(",")

        records.append({
            "mountpoint": _unescape_mount_path(fields[4]),
            "source": _unescape_mount_path(details[1]),
            "major_minor": fields[2],
            "filesystem": details[0],
            "read_only": "ro" in options and "rw" not in options,
            "options": options,
        })

    return records


def evaluate_rescue_source(device, mounts):
    """Return a conservative eligibility decision for one partition.

    This checks mount state only. It does not authorize copying or
    guarantee protection against concurrent external writes.
    """
    def decision(eligible, reason, mountpoint=None):
        return {
            "eligible": eligible,
            "reason": reason,
            "mountpoint": mountpoint,
        }

    if device.get("type") != "part":
        return decision(False, "Not a partition")

    if device.get("encrypted"):
        return decision(False, "Encrypted filesystem")

    if device.get("filesystem_class") != "SUPPORTED":
        return decision(False, "Unsupported or unknown filesystem")

    path = device.get("path")
    if not isinstance(path, str) or not path.startswith("/dev/"):
        return decision(False, "Invalid device path")

    matching = [
        entry for entry in mounts
        if entry.get("source") == path
    ]

    if not matching:
        return decision(False, "Filesystem not mounted")

    if any(not entry.get("read_only") for entry in matching):
        return decision(False, "Filesystem has a read-write mount")

    if any(entry.get("mountpoint") == "/" for entry in matching):
        return decision(False, "Active system filesystem")

    mountpoint = matching[0].get("mountpoint")

    if not mountpoint or not Path(mountpoint).is_dir():
        return decision(False, "Mountpoint unavailable")

    return decision(
        True,
        "Existing read-only mount verified; browsing candidate",
        mountpoint,
    )


def evaluate_rescue_source_by_identity(device, mounts):
    """Conservative mount eligibility using kernel major/minor identity.

    The identity must be obtained from current trusted device metadata.
    Callers must revalidate before browsing or copying. This function
    does not mount devices or authorize file-copy operations.
    """
    def deny(reason):
        return {
            "eligible": False,
            "reason": reason,
            "mountpoint": None,
        }

    if device.get("type") != "part":
        return deny("Not a partition")

    if device.get("encrypted"):
        return deny("Encrypted filesystem")

    if device.get("filesystem_class") != "SUPPORTED":
        return deny("Unsupported or unknown filesystem")

    identity = device.get("maj:min")

    if not isinstance(identity, str):
        return deny("Kernel device identity unavailable")

    import re

    if not re.fullmatch(r"[0-9]+:[0-9]+", identity):
        return deny("Invalid kernel device identity")

    matches = [
        entry for entry in mounts
        if entry.get("major_minor") == identity
    ]

    if not matches:
        return deny("No matching mounted filesystem")

    if len(matches) != 1:
        return deny("Ambiguous or multiple filesystem mounts")

    entry = matches[0]

    if not entry.get("read_only"):
        return deny("Filesystem mounted read-write")

    mountpoint = entry.get("mountpoint")

    if mountpoint in ("/", "/boot", "/boot/efi"):
        return deny("Active system filesystem")

    if not isinstance(mountpoint, str) or not mountpoint.startswith("/"):
        return deny("Invalid mountpoint")

    if not Path(mountpoint).is_dir():
        return deny("Mountpoint unavailable")

    return {
        "eligible": True,
        "reason": "Read-only mount and kernel identity matched",
        "mountpoint": mountpoint,
    }
