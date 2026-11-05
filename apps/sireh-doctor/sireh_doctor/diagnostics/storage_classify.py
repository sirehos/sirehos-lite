"""Classify PCI storage-controller types without probing hardware."""

import re


CONTROLLER_TYPES = {
    "010100": "IDE",
    "010400": "RAID",
    "010601": "SATA_AHCI",
    "010700": "SAS",
    "010802": "NVME",
}


def classify_controller(class_code):
    """Classify a PCI controller using its six-digit class code."""
    result = {
        "status": "UNKNOWN",
        "class_code": class_code,
        "controller_type": "UNKNOWN",
        "description": "Controller type unavailable",
        "physical_disk_visibility": "UNKNOWN",
    }

    if (
        not isinstance(class_code, str)
        or re.fullmatch(r"[0-9a-fA-F]{6}", class_code) is None
    ):
        return result

    code = class_code.lower()
    result["class_code"] = code
    result["status"] = "AVAILABLE"

    if code.startswith("0c03"):
        result["controller_type"] = "USB_HOST"
        result["description"] = "USB host controller"
        result["physical_disk_visibility"] = "BRIDGE_DEPENDENT"
        return result

    controller_type = CONTROLLER_TYPES.get(code)

    if controller_type is None:
        result["controller_type"] = "OTHER"
        result["description"] = "Other PCI controller"
        return result

    result["controller_type"] = controller_type

    descriptions = {
        "IDE": "IDE storage controller",
        "RAID": "RAID storage controller",
        "SATA_AHCI": "SATA controller operating in AHCI mode",
        "SAS": "Serial Attached SCSI controller",
        "NVME": "NVMe storage controller",
    }

    result["description"] = descriptions[controller_type]

    if controller_type == "RAID":
        result["physical_disk_visibility"] = "CONTROLLER_DEPENDENT"
    else:
        result["physical_disk_visibility"] = "NOT_ASSESSED"

    return result
