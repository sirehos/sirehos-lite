"""Interpret read-only storage metadata without claiming disk health."""


def finding(component, check, status, summary, recommendation):
    return {
        "component": component,
        "check": check,
        "status": status,
        "summary": summary,
        "recommendation": recommendation,
    }


def assess_device(device):
    """Identify a physical disk without asserting SMART health."""
    path = device.get("path") or "Unknown device"
    model = device.get("model") or "Unknown model"
    size = device.get("size")

    if device.get("type") != "disk":
        return finding(
            path, "Device identification", "UNKNOWN",
            "The selected entry is not identified as a physical disk.",
            "Verify the device type before assessing storage health.",
        )

    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        return finding(
            path, "Device identification", "UNKNOWN",
            "The disk capacity could not be verified.",
            "Check whether Linux can read the device metadata.",
        )

    return finding(
        path, "Device identification", "INFO",
        f"{model} detected with {size:,} bytes of capacity.",
        "Device detection does not establish disk health. "
        "Review SMART or NVMe health information separately.",
    )


def assess_partitions(device):
    """Report partition visibility, not partition-table integrity."""
    path = device.get("path") or "Unknown device"
    children = device.get("children")

    if children is None:
        return finding(
            path, "Partition visibility", "UNKNOWN",
            "No partition entries were reported.",
            "This may be normal for an unpartitioned disk. "
            "Inspect its intended use before drawing conclusions.",
        )

    if not isinstance(children, list):
        return finding(
            path, "Partition visibility", "UNKNOWN",
            "Partition information has an unexpected format.",
            "Repeat device discovery.",
        )

    count = sum(
        1 for child in children
        if isinstance(child, dict) and child.get("type") == "part"
    )

    return finding(
        path, "Partition visibility", "INFO",
        f"{count} partition(s) visible to Linux.",
        "Visibility alone does not verify partition-table integrity.",
    )


def assess_filesystems(device):
    """Report detected filesystem types and mount points."""
    path = device.get("path") or "Unknown device"
    children = device.get("children", [])

    if not isinstance(children, list):
        children = []

    entries = [device] + [
        child for child in children if isinstance(child, dict)
    ]

    filesystems = sorted({
        entry["fstype"]
        for entry in entries
        if isinstance(entry.get("fstype"), str)
        and entry["fstype"].strip()
    })

    if not filesystems:
        return finding(
            path, "Filesystem visibility", "UNKNOWN",
            "No filesystem type was identified.",
            "This may be normal for raw, encrypted or unformatted "
            "storage. Do not attempt repairs without identifying it.",
        )

    return finding(
        path, "Filesystem visibility", "INFO",
        "Detected filesystem type(s): " + ", ".join(filesystems) + ".",
        "Filesystem detection does not establish filesystem integrity.",
    )


def assess(data):
    """Return storage findings for discovered physical disks."""
    if data.get("status") != "AVAILABLE":
        return [
            finding(
                "Storage", "Device discovery", "UNKNOWN",
                "Storage device discovery was unavailable.",
                data.get("error") or
                "Check whether the lsblk utility is available.",
            )
        ]

    devices = data.get("devices", [])

    if not isinstance(devices, list):
        devices = []

    findings = []

    for device in devices:
        if not isinstance(device, dict):
            continue

        if device.get("type") != "disk":
            continue

        findings.extend([
            assess_device(device),
            assess_partitions(device),
            assess_filesystems(device),
        ])

    if not findings:
        findings.append(
            finding(
                "Storage", "Device discovery", "UNKNOWN",
                "No physical disks were identified.",
                "Check device connections and Linux storage detection.",
            )
        )

    return findings
