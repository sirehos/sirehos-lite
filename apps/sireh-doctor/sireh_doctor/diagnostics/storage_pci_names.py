"""Offline, read-only PCI controller name resolution."""

import re
import shutil
import subprocess


PCI_ADDRESS = re.compile(
    r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:"
    r"[0-9a-fA-F]{2}\.[0-7]$"
)


def resolve_pci_name(pci_address, timeout=5):
    """Resolve a PCI controller using the local lspci database."""
    result = {
        "status": "UNKNOWN",
        "pci_address": pci_address,
        "description": None,
        "subsystem": None,
        "kernel_driver": None,
        "kernel_modules": None,
        "error": None,
    }

    if (
        not isinstance(pci_address, str)
        or not PCI_ADDRESS.fullmatch(pci_address)
    ):
        result["error"] = "Invalid PCI address"
        return result

    executable = shutil.which("lspci")

    if executable is None:
        result["error"] = "lspci is not installed"
        return result

    try:
        completed = subprocess.run(
            [executable, "-D", "-nn", "-s", pci_address, "-k"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result["error"] = "PCI name lookup could not complete"
        return result

    if completed.returncode != 0:
        result["error"] = "PCI name lookup failed"
        return result

    lines = completed.stdout.splitlines()

    if not lines or not lines[0].startswith(pci_address + " "):
        result["error"] = "PCI controller not found"
        return result

    description = lines[0].split(": ", 1)

    if len(description) != 2:
        result["error"] = "PCI description unavailable"
        return result

    result["description"] = description[1].strip()

    for line in lines[1:]:
        item = line.strip()

        if item.startswith("Subsystem:"):
            result["subsystem"] = item.partition(":")[2].strip()
        elif item.startswith("Kernel driver in use:"):
            result["kernel_driver"] = item.partition(":")[2].strip()
        elif item.startswith("Kernel modules:"):
            result["kernel_modules"] = item.partition(":")[2].strip()

    result["status"] = "AVAILABLE"
    return result
