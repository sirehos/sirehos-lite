"""SD-04: read-only operating-system and boot diagnostics.

Benih 1.0. No mounting, elevation, repair or disk writes.
"""
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


def result(status, summary, details=None):
    return {
        "status": status,
        "summary": summary,
        "details": details or [],
    }


def command(argv, timeout=5):
    executable = shutil.which(argv[0])
    if not executable:
        return None, "Utility not installed: " + argv[0]
    try:
        proc = subprocess.run(
            [executable, *argv[1:]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode:
            return None, (
                proc.stderr.strip()[:240]
                or "Command exited with code " + str(proc.returncode)
            )
        return proc.stdout, None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)[:240]


def disks():
    output, error = command([
        "lsblk", "-J", "-b", "-o",
        "NAME,PATH,TYPE,FSTYPE,PARTTYPE,PTTYPE,UUID,LABEL,"
        "SIZE,MOUNTPOINTS,PARTUUID"
    ])
    if error:
        return [], error
    try:
        data = json.loads(output)
    except (TypeError, ValueError):
        return [], "Cannot decode disk metadata"
    entries = []

    def walk(nodes, parent=""):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            item = dict(node)
            item["parent_disk"] = parent
            entries.append(item)
            walk(node.get("children") or [], parent or node.get("path", ""))

    walk(data.get("blockdevices") or [])
    return entries, None


def mounted_paths(item):
    return [
        p for p in (item.get("mountpoints") or [])
        if isinstance(p, str) and p.startswith("/")
    ]


def inspect_os():
    details = [
        "Running system: " + platform.system(),
        "Kernel: " + platform.release(),
        "Architecture: " + platform.machine(),
    ]
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        try:
            for line in os_release.read_text(errors="replace").splitlines():
                if line.startswith("PRETTY_NAME="):
                    details.append(
                        "Running distribution: "
                        + line.partition("=")[2].strip().strip('"')
                    )
                    break
        except OSError:
            pass

    entries, error = disks()
    if error:
        details.append("Installed OS discovery: UNKNOWN (" + error + ")")
        return result("UNKNOWN", "Running OS identified; disk inventory unavailable", details)

    installed = []
    for item in entries:
        if item.get("type") != "part":
            continue
        for mount in mounted_paths(item):
            root = Path(mount)
            if not root.is_dir():
                continue
            try:
                linux = root / "etc/os-release"
                windows = root / "Windows/System32/config/SYSTEM"
                if linux.is_file():
                    label = "Linux installation"
                    for line in linux.read_text(errors="replace").splitlines():
                        if line.startswith("PRETTY_NAME="):
                            label = line.partition("=")[2].strip().strip('"')
                            break
                    installed.append(
                        "{} on {}".format(label, item.get("path", "?"))
                    )
                elif windows.is_file():
                    installed.append(
                        "Windows installation evidence on "
                        + str(item.get("path", "?"))
                    )
            except (OSError, PermissionError):
                continue

    details.extend(installed)
    details.append(
        "Only already-mounted, accessible partitions are inspected."
    )
    if installed:
        return result("PASS", "Accessible OS installation evidence found", details)
    return result(
        "UNKNOWN",
        "Running OS identified; other installations not confirmed",
        details,
    )


def inspect_firmware():
    efi = Path("/sys/firmware/efi")
    mode = "UEFI" if efi.is_dir() else "Legacy BIOS"
    details = [
        "Current live-session boot mode: " + mode,
        "CPU architecture: " + platform.machine(),
        "Firmware CSM setting: UNKNOWN",
    ]
    if not efi.is_dir():
        details.append("Secure Boot: unavailable in Legacy BIOS mode")
        return result("PASS", "Current session uses Legacy BIOS", details)

    secure = "UNKNOWN"
    efivars = efi / "efivars"
    try:
        for path in efivars.glob("SecureBoot-*"):
            raw = path.read_bytes()
            if len(raw) >= 5:
                secure = "Enabled" if raw[4] == 1 else "Disabled"
                break
    except (OSError, PermissionError):
        pass

    details.append("Secure Boot: " + secure)
    details.append(
        "This reports the live USB boot mode, not necessarily "
        "the installed OS boot mode."
    )
    return result("PASS", "Current session uses UEFI", details)


def inspect_boot_partitions():
    entries, error = disks()
    if error:
        return result("UNKNOWN", "Boot partition metadata unavailable", [error])

    esp_guid = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
    bios_guid = "21686148-6449-6e6f-744e-656564454649"
    found = []

    for item in entries:
        if item.get("type") != "part":
            continue
        parttype = str(item.get("parttype") or "").lower()
        if parttype == esp_guid or parttype in ("0xef", "ef"):
            kind = "EFI System Partition"
        elif parttype == bios_guid:
            kind = "BIOS boot partition"
        else:
            continue
        found.append(
            "{}: {} | filesystem={} | mounted={}".format(
                item.get("path", "?"),
                kind,
                item.get("fstype") or "UNKNOWN",
                ", ".join(mounted_paths(item)) or "No",
            )
        )

    if found:
        return result("PASS", "Boot-related partition(s) identified", found)

    return result(
        "UNKNOWN",
        "No identifiable EFI or BIOS boot partition",
        [
            "This alone does not prove a boot failure.",
            "Legacy BIOS/MBR systems may not use a dedicated boot partition.",
        ],
    )


def inspect_bootloaders():
    details = []
    efi = Path("/sys/firmware/efi")

    if efi.is_dir():
        output, error = command(["efibootmgr", "-v"])
        if error:
            details.append("EFI NVRAM: UNKNOWN (" + error + ")")
        else:
            lines = [
                line.strip()[:250]
                for line in output.splitlines()
                if line.startswith(("BootCurrent:", "BootOrder:", "Boot"))
            ]
            details.extend(lines[:25])
            if not lines:
                details.append("No readable EFI NVRAM entries returned")
    else:
        details.append("EFI NVRAM unavailable in Legacy BIOS session")

    entries, error = disks()
    if error:
        details.append("Bootloader file inspection: UNKNOWN (" + error + ")")
    else:
        seen = set()
        for item in entries:
            for mount in mounted_paths(item):
                if mount in seen:
                    continue
                seen.add(mount)
                for rel in (
                    "EFI/Microsoft/Boot/bootmgfw.efi",
                    "EFI/BOOT/BOOTX64.EFI",
                    "EFI/BOOT/BOOTIA32.EFI",
                    "boot/grub/grub.cfg",
                    "loader/loader.conf",
                ):
                    path = Path(mount) / rel
                    try:
                        if path.is_file():
                            details.append(
                                "Accessible bootloader evidence: "
                                + str(path)
                            )
                    except OSError:
                        pass

    if any("bootloader evidence:" in d for d in details):
        return result("PASS", "Accessible bootloader files identified", details)
    return result(
        "UNKNOWN",
        "Bootloader integrity cannot be confirmed",
        details or ["No accessible bootloader evidence"],
    )


def inspect_boot_config():
    details = []
    entries, error = disks()
    if error:
        return result("UNKNOWN", "Boot configuration inaccessible", [error])

    seen = set()
    for item in entries:
        for mount in mounted_paths(item):
            if mount in seen:
                continue
            seen.add(mount)
            root = Path(mount)
            candidates = (
                "boot/grub/grub.cfg",
                "boot/loader/entries",
                "loader/entries",
                "EFI/Microsoft/Boot/BCD",
                "etc/fstab",
            )
            for relative in candidates:
                path = root / relative
                try:
                    if path.is_file() or path.is_dir():
                        details.append("Present: " + str(path))
                except OSError:
                    continue
            boot = root / "boot"
            try:
                if boot.is_dir():
                    for pattern in ("vmlinuz-*", "initrd.img-*"):
                        for path in list(boot.glob(pattern))[:10]:
                            if path.is_file():
                                size = path.stat().st_size
                                details.append(
                                    "{}: {} bytes".format(path, size)
                                )
            except OSError:
                pass

    details.append(
        "File presence is not proof of a valid boot configuration."
    )
    if len(details) > 1:
        return result("PASS", "Accessible boot configuration evidence found", details)
    return result(
        "UNKNOWN",
        "Installed OS boot configuration not accessible",
        details,
    )


def diagnose_boot():
    checks = {
        "firmware": inspect_firmware(),
        "boot_partitions": inspect_boot_partitions(),
        "bootloaders": inspect_bootloaders(),
        "boot_config": inspect_boot_config(),
    }
    details = [
        "{}: {} — {}".format(
            name, value["status"], value["summary"]
        )
        for name, value in checks.items()
    ]
    details.append(
        "A successful live USB boot does not prove the installed OS can boot."
    )
    return result(
        "UNKNOWN",
        "No definitive installed-OS boot verdict from read-only evidence",
        details,
    )


CHECKS = {
    "os": ("Detect OS", inspect_os),
    "firmware": ("Check Firmware", inspect_firmware),
    "boot_partitions": ("Inspect Boot Partitions", inspect_boot_partitions),
    "bootloaders": ("Check Bootloaders", inspect_bootloaders),
    "boot_config": ("Check Boot Config", inspect_boot_config),
    "diagnose": ("Diagnose Boot", diagnose_boot),
}


def run_check(check_id):
    if check_id not in CHECKS:
        raise ValueError("Unknown OS & Boot check: " + str(check_id))
    try:
        return CHECKS[check_id][1]()
    except Exception as exc:
        return result(
            "UNKNOWN",
            "Diagnostic check could not be completed",
            [type(exc).__name__ + ": " + str(exc)[:200]],
        )


def run_all():
    return {check_id: run_check(check_id) for check_id in CHECKS}
