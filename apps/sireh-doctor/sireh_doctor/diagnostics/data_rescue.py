"""Sireh Doctor Data Rescue: read-only device discovery.

Benih 1.0 — B016.
Discovery never authorizes file access or recovery.
"""

import json
import subprocess

SUPPORTED_FILESYSTEMS = frozenset({
    "ntfs", "ntfs3", "vfat", "exfat",
    "ext2", "ext3", "ext4", "btrfs", "xfs",
})

ENCRYPTED_FILESYSTEMS = frozenset({
    "bitlocker", "crypto_bitlocker", "bitlk",
    "crypto_luks",
})


def _classify_filesystem(value):
    """Classify filesystem metadata without opening the device."""
    filesystem = str(value or "").strip().lower()

    if filesystem in ENCRYPTED_FILESYSTEMS:
        return "ENCRYPTED"
    if filesystem in SUPPORTED_FILESYSTEMS:
        return "SUPPORTED"
    if not filesystem:
        return "UNKNOWN"
    return "UNSUPPORTED"


def _flatten_devices(devices, parent=None):
    """Return a flat, normalized view of lsblk device metadata."""
    records = []

    for device in devices:
        if not isinstance(device, dict):
            continue

        path = device.get("path")
        device_type = device.get("type")
        filesystem = device.get("fstype")
        mountpoints = device.get("mountpoints") or []

        if isinstance(mountpoints, str):
            mountpoints = [mountpoints]

        mountpoints = [
            point for point in mountpoints
            if isinstance(point, str) and point
        ]

        classification = _classify_filesystem(filesystem)

        records.append({
            "name": device.get("name"),
            "maj:min": device.get("maj:min"),
            "path": path,
            "parent": parent,
            "type": device_type,
            "size_bytes": device.get("size"),
            "filesystem": filesystem,
            "filesystem_class": classification,
            "mountpoints": mountpoints,
            "block_read_only": device.get("ro"),
            "removable": device.get("rm"),
            "model": device.get("model"),
            "transport": device.get("tran"),
            "encrypted": classification == "ENCRYPTED",
            "rescue_eligible": False,
            "eligibility_reason": "Read-only source access not yet verified",
        })

        records.extend(
            _flatten_devices(
                device.get("children") or [],
                parent=path,
            )
        )

    return records


def discover_rescue_drives():
    """Discover devices; never mount or authorize source access."""
    try:
        completed = subprocess.run(
            [
                "lsblk", "--json", "--bytes",
                "--output",
                "NAME,PATH,TYPE,SIZE,MODEL,TRAN,ROTA,RM,RO,"
                "FSTYPE,MOUNTPOINTS,MAJ:MIN",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip() or "lsblk failed"
            )

        result = {
            "status": "AVAILABLE",
            "devices": json.loads(completed.stdout)["blockdevices"],
            "error": None,
        }

    except (OSError, ValueError, KeyError, TypeError,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        result = {
            "status": "UNKNOWN",
            "devices": [],
            "error": str(exc),
        }

    if result.get("status") != "AVAILABLE":
        return {
            "status": "UNKNOWN",
            "devices": [],
            "error": result.get("error") or "Discovery unavailable",
        }

    devices = result.get("devices")

    if not isinstance(devices, list):
        return {
            "status": "UNKNOWN",
            "devices": [],
            "error": "Invalid storage discovery response",
        }

    records = _flatten_devices(devices)

    return {
        "status": "AVAILABLE",
        "devices": records,
        "error": None,
    }
