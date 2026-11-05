"""Unified read-only storage hardware inventory."""

from sireh_doctor.diagnostics.storage import collect_storage
from sireh_doctor.diagnostics.storage_controller import discover_controller
from sireh_doctor.diagnostics.storage_pci import collect_pci_controller
from sireh_doctor.diagnostics.storage_classify import classify_controller


def collect_storage_inventory():
    """Combine disk discovery and PCI metadata without health claims."""
    discovery = collect_storage()

    result = {
        "status": discovery.get("status", "UNKNOWN"),
        "devices": [],
        "error": discovery.get("error"),
    }

    if result["status"] != "AVAILABLE":
        return result

    devices = discovery.get("devices", [])

    if not isinstance(devices, list):
        result["status"] = "UNKNOWN"
        result["error"] = "Invalid device collection"
        return result

    for device in devices:
        if not isinstance(device, dict):
            continue

        if device.get("type") != "disk":
            continue

        name = device.get("name")
        try:
            controller = discover_controller(name)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            controller = {
                "status": "UNKNOWN",
                "device": name,
                "pci_address": None,
                "hardware_path": None,
                "error": "Controller discovery failed: {}".format(exc),
            }

        pci = None
        classification = None

        if controller.get("status") == "AVAILABLE":
            try:
                pci = collect_pci_controller(
                    controller.get("pci_address")
                )
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                pci = {
                    "status": "UNKNOWN",
                    "pci_address": controller.get("pci_address"),
                    "class_code": None,
                    "error": "PCI metadata failed: {}".format(exc),
                }

            if pci.get("status") == "AVAILABLE":
                try:
                    classification = classify_controller(
                        pci.get("class_code")
                    )
                except (OSError, RuntimeError, ValueError, TypeError):
                    classification = None

        result["devices"].append({
            "name": name,
            "path": device.get("path"),
            "model": device.get("model"),
            "size_bytes": device.get("size"),
            "transport": device.get("tran"),
            "removable": device.get("rm"),
            "rotational": device.get("rota"),
            "read_only": device.get("ro"),
            "partitions": device.get("children", []),
            "controller": controller,
            "pci": pci,
            "classification": classification,
        })

    return result
