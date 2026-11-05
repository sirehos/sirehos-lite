"""Read-only PCI storage-controller metadata collection."""

import re
from pathlib import Path

from sireh_doctor.diagnostics.storage_controller import PCI_ADDRESS


PCI_FIELDS = {
    "vendor_id": ("vendor", 4),
    "device_id": ("device", 4),
    "subsystem_vendor_id": ("subsystem_vendor", 4),
    "subsystem_device_id": ("subsystem_device", 4),
    "class_code": ("class", 6),
    "revision": ("revision", 2),
}


def _read_hex_field(directory, filename, digits):
    """Read a fixed-width hexadecimal PCI sysfs attribute."""
    try:
        value = (directory / filename).read_text(
            encoding="ascii"
        ).strip()
    except (OSError, UnicodeError, ValueError):
        return None

    pattern = r"0x[0-9a-fA-F]{" + str(digits) + r"}"

    if not re.fullmatch(pattern, value):
        return None

    return value[2:].lower()


def collect_pci_controller(
    pci_address, pci_root="/sys/bus/pci/devices"
):
    """Collect PCI identity and active driver without modifying hardware."""
    result = {
        "status": "UNKNOWN",
        "pci_address": pci_address,
        "vendor_id": None,
        "device_id": None,
        "subsystem_vendor_id": None,
        "subsystem_device_id": None,
        "class_code": None,
        "revision": None,
        "driver": None,
        "error": None,
    }

    if (
        not isinstance(pci_address, str)
        or PCI_ADDRESS.fullmatch(pci_address) is None
    ):
        result["error"] = "Invalid PCI address"
        return result

    directory = Path(pci_root) / pci_address

    if not directory.is_dir():
        result["error"] = "PCI controller unavailable"
        return result

    for key, (filename, digits) in PCI_FIELDS.items():
        result[key] = _read_hex_field(
            directory, filename, digits
        )

    try:
        driver_link = directory / "driver"

        if driver_link.is_symlink():
            driver_name = driver_link.resolve(
                strict=True
            ).name

            if re.fullmatch(r"[A-Za-z0-9_.-]+", driver_name):
                result["driver"] = driver_name

    except (OSError, RuntimeError, ValueError):
        pass

    if (
        result["vendor_id"] is not None
        and result["device_id"] is not None
        and result["class_code"] is not None
    ):
        result["status"] = "AVAILABLE"
    else:
        result["error"] = (
            "Required PCI controller metadata missing or invalid"
        )

    return result
