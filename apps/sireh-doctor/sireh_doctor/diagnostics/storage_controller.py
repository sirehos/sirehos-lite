"""Read-only Linux storage-controller discovery."""

import re
from pathlib import Path


PCI_ADDRESS = re.compile(
    r"^[0-9a-fA-F]{4}:"
    r"[0-9a-fA-F]{2}:"
    r"[0-1][0-9a-fA-F]" + re.escape(".") +
    r"[0-7]$"
)



def discover_controller(device_name, sysfs_root="/sys/block"):
    """Identify a disk's PCI controller through its sysfs path."""
    result = {
        "status": "UNKNOWN",
        "device": device_name,
        "pci_address": None,
        "hardware_path": None,
        "error": None,
    }

    if (
        not isinstance(device_name, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]+", device_name)
        or device_name in (".", "..")
    ):
        result["error"] = "Invalid block-device name"
        return result

    try:
        root = Path(sysfs_root)
        device_link = root / device_name / "device"

        if not device_link.exists():
            result["error"] = "Device hardware path unavailable"
            return result

        resolved = device_link.resolve(strict=True)
        result["hardware_path"] = str(resolved)

        pci_addresses = [
            part for part in resolved.parts
            if PCI_ADDRESS.fullmatch(part)
        ]

        if not pci_addresses:
            result["error"] = "No PCI controller found in hardware path"
            return result

        result["pci_address"] = pci_addresses[-1]
        result["status"] = "AVAILABLE"

    except (OSError, RuntimeError, ValueError) as exc:
        result["error"] = "Controller discovery failed: {}".format(exc)

    return result
