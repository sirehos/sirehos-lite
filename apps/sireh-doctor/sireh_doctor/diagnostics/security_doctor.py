"""Read-only security evidence checks for Sireh Doctor Benih 1.0."""

from pathlib import Path
import shutil
import subprocess


CHECKS = {
    "access_control": "Access Control Doctor",
    "firewall": "Firewall & Network Exposure",
    "privileged_accounts": "Privileged Accounts & Sudo",
    "file_permissions": "Critical File Permissions",
    "remote_access": "SSH & Remote Access",
    "boot_encryption": "Boot & Encryption Security",
    "patch_evidence": "Security Updates & Patch Evidence",
    "industrial_media": "Industrial & Removable-Media Security",
}


def result(status, summary, details):
    return {
        "status": status,
        "summary": summary,
        "details": details,
    }


def command_output(args, timeout=8):
    """Run a bounded local read-only query without shell or elevation."""
    if not shutil.which(args[0]):
        return None
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
    return completed.stdout[:12000]


def read_text(path):
    try:
        return Path(path).read_text(errors="replace")[:12000].strip()
    except (OSError, UnicodeError):
        return None


def access_control():
    """Inspect runtime Linux MAC evidence; do not infer offline OS status."""
    evidence = []
    enforced = False
    observed = False

    apparmor = read_text("/sys/module/apparmor/parameters/enabled")
    if apparmor is not None:
        observed = True
        evidence.append("AppArmor kernel enabled: " + apparmor)
        if apparmor.upper().startswith("Y"):
            enforced = True

    selinux = read_text("/sys/fs/selinux/enforce")
    if selinux is not None:
        observed = True
        evidence.append("SELinux enforcement: " + selinux)
        if selinux == "1":
            enforced = True

    evidence.append("Target: Running Linux session")
    evidence.append(
        "Limitation: Kernel MAC enablement does not prove "
        "that every application has an enforcing policy."
    )

    if enforced:
        return result(
            "INFO",
            "A Linux mandatory access-control mechanism is enabled.",
            "\n".join(evidence),
        )
    if observed:
        return result(
            "WARN",
            "No enforcing MAC mechanism was confirmed from available evidence.",
            "\n".join(evidence),
        )
    return result(
        "UNKNOWN",
        "Mandatory access-control runtime evidence was unavailable.",
        "\n".join(evidence),
    )


def firewall():
    """Inspect local socket and firewall evidence without network probes."""
    evidence = ["Target: Running Linux session"]
    sockets = command_output(["ss", "-H", "-lntu"])
    ufw = command_output(["ufw", "status"])
    nft = command_output(["nft", "list", "ruleset"])

    if sockets is not None:
        lines = sockets.splitlines()
        evidence.append(
            "Listening TCP/UDP socket entries: {}".format(len(lines))
        )
        evidence.extend(lines[:12])
        if len(lines) > 12:
            evidence.append(
                "Additional socket entries omitted: {}".format(
                    len(lines) - 12
                )
            )
    else:
        evidence.append("Listening sockets: Not accessible")

    if ufw is not None:
        evidence.append("UFW evidence: " + ufw.strip()[:500])

    if nft is not None:
        evidence.append(
            "nftables ruleset readable: Yes "
            "(ruleset contents not displayed)"
        )

    if ufw is None and nft is None:
        evidence.append(
            "Firewall policy: Not verified; privileges may be required."
        )

    evidence.append(
        "Limitation: Listening sockets are not proof of external "
        "reachability. No remote hosts were contacted."
    )

    if sockets is None and ufw is None and nft is None:
        return result(
            "UNKNOWN",
            "Local firewall and listening-socket evidence was unavailable.",
            "\n".join(evidence),
        )

    return result(
        "INFO",
        "Local network exposure evidence collected; protection not certified.",
        "\n".join(evidence),
    )



def privileged_accounts():
    """Inspect local account metadata without reading password hashes."""
    import grp
    import pwd

    evidence = ["Target: Running Linux session"]
    warnings = []
    unknowns = []

    try:
        accounts = pwd.getpwall()
    except (OSError, KeyError):
        accounts = []
        unknowns.append("Account database could not be enumerated.")

    if accounts:
        root_accounts = sorted(
            account.pw_name for account in accounts
            if account.pw_uid == 0
        )
        evidence.append(
            "UID 0 accounts: " + ", ".join(root_accounts)
        )

        unexpected = [
            name for name in root_accounts if name != "root"
        ]
        if unexpected:
            warnings.append(
                "Additional UID 0 accounts detected: "
                + ", ".join(unexpected)
            )

    for group_name in ("sudo", "wheel"):
        try:
            group = grp.getgrnam(group_name)
        except KeyError:
            continue
        except OSError:
            unknowns.append(
                "Could not inspect group: " + group_name
            )
            continue

        members = set(group.gr_mem)

        for account in accounts:
            if account.pw_gid == group.gr_gid:
                members.add(account.pw_name)

        evidence.append(
            "{} group members: {}".format(
                group_name,
                ", ".join(sorted(members)) if members else "None"
            )
        )

    sudoers = Path("/etc/sudoers")
    try:
        if sudoers.is_file():
            sudoers.read_text(errors="replace")
            evidence.append(
                "Main sudoers policy: Readable; detailed policy "
                "evaluation not implemented."
            )
        else:
            unknowns.append(
                "Main sudoers policy is unavailable."
            )
    except OSError:
        unknowns.append(
            "Main sudoers policy cannot be read without "
            "additional privileges."
        )

    evidence.extend(warnings)
    evidence.extend(unknowns)
    evidence.append(
        "Limitation: Group membership does not establish "
        "effective sudo privileges. Included policy files, "
        "directory services and authentication rules "
        "have not been fully evaluated."
    )

    if warnings:
        status = "WARN"
        summary = "Additional UID 0 accounts require review."
    elif unknowns:
        status = "UNKNOWN"
        summary = (
            "Account metadata collected; privileged access "
            "assessment is incomplete."
        )
    elif accounts:
        status = "INFO"
        summary = (
            "Local privileged account metadata collected; "
            "effective sudo permissions not certified."
        )
    else:
        status = "UNKNOWN"
        summary = "Privileged account evidence unavailable."

    return result(status, summary, "\n".join(evidence))



def file_permissions():
    """Inspect a bounded set of local Linux security-sensitive paths."""
    import stat

    targets = (
        ("/etc/passwd", False, False),
        ("/etc/shadow", True, False),
        ("/etc/group", False, False),
        ("/etc/gshadow", True, False),
        ("/etc/sudoers", True, False),
        ("/etc/sudoers.d", False, True),
        ("/etc/ssh", False, True),
        ("/etc/ssh/sshd_config", False, False),
    )

    evidence = ["Target: Running Linux session"]
    warnings = []
    unknowns = []
    inspected = 0

    for filename, restricted, directory in targets:
        target = Path(filename)

        try:
            metadata = target.lstat()
        except FileNotFoundError:
            evidence.append(filename + ": Not present")
            continue
        except OSError:
            unknowns.append(filename + ": Metadata unavailable")
            continue

        mode = metadata.st_mode
        permissions = stat.S_IMODE(mode)
        kind = (
            "directory" if stat.S_ISDIR(mode)
            else "file" if stat.S_ISREG(mode)
            else "other"
        )

        evidence.append(
            "{}: {} | mode {:04o} | UID {} | GID {}".format(
                filename,
                kind,
                permissions,
                metadata.st_uid,
                metadata.st_gid,
            )
        )

        inspected += 1

        if stat.S_ISLNK(mode):
            unknowns.append(filename + ": Symbolic link requires review")
            continue

        if directory and not stat.S_ISDIR(mode):
            warnings.append(filename + ": Expected a directory")
        elif not directory and not stat.S_ISREG(mode):
            warnings.append(filename + ": Expected a regular file")

        if permissions & 0o002:
            warnings.append(filename + ": World-writable")
        if permissions & 0o020:
            warnings.append(filename + ": Group-writable; review ownership")

        if restricted and permissions & 0o007:
            warnings.append(
                filename + ": Accessible to other users"
            )

        if metadata.st_uid != 0:
            warnings.append(filename + ": Not owned by root")

    evidence.extend(warnings)
    evidence.extend(unknowns)
    evidence.append(
        "Limitation: Metadata only. ACLs, immutable attributes, "
        "filesystem integrity, nested files, and SUID/SGID "
        "inventory were not assessed. Missing optional paths "
        "do not automatically indicate a vulnerability."
    )

    if warnings:
        status = "WARN"
        summary = "Potentially unsafe critical-path metadata found."
    elif unknowns:
        status = "UNKNOWN"
        summary = "Critical-path inspection was incomplete."
    elif inspected:
        status = "INFO"
        summary = (
            "No selected permission warning patterns detected; "
            "filesystem security not certified."
        )
    else:
        status = "UNKNOWN"
        summary = "No critical-path metadata could be inspected."

    return result(status, summary, "\n".join(evidence))



def remote_access():
    """Inspect local SSH configuration and remote-access listeners."""
    import re

    evidence = ["Target: Running Linux session"]
    warnings = []
    unknowns = []

    config_path = Path("/etc/ssh/sshd_config")
    config = read_text(config_path)

    settings = (
        "permitrootlogin",
        "passwordauthentication",
        "permitemptypasswords",
    )

    if config is None:
        evidence.append(
            "SSH server configuration: Not readable or not installed"
        )
        unknowns.append("Effective SSH authentication policy not verified.")
    else:
        evidence.append(
            "SSH configuration source: /etc/ssh/sshd_config"
        )

        observed = {}

        for line in config.splitlines():
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split(None, 1)

            if len(parts) != 2:
                continue

            key = parts[0].lower()
            value = parts[1].strip().split("#", 1)[0].strip()

            if key in settings:
                observed[key] = value

        for key in settings:
            value = observed.get(key, "Not explicitly configured")
            evidence.append("{}: {}".format(key, value))

        if observed.get("permitrootlogin", "").lower() == "yes":
            warnings.append(
                "SSH configuration explicitly permits root login."
            )

        if observed.get("permitemptypasswords", "").lower() == "yes":
            warnings.append(
                "SSH configuration explicitly permits empty passwords."
            )

        if observed.get("passwordauthentication", "").lower() == "yes":
            warnings.append(
                "SSH password authentication is explicitly enabled; "
                "review against the intended security policy."
            )

        unknowns.append(
            "Effective SSH policy not verified: Include, Match, "
            "defaults and runtime overrides may apply."
        )

    sockets = command_output(["ss", "-H", "-lnt"])

    if sockets is None:
        unknowns.append("TCP listener inventory unavailable.")
    else:
        listeners = []

        for line in sockets.splitlines():
            parts = line.split()

            if len(parts) < 5:
                continue

            address = parts[4]
            match = re.search(r":(\\d+)$", address)

            if not match:
                continue

            port = int(match.group(1))

            if port in (21, 22, 23):
                listeners.append(
                    "TCP port {}: {}".format(port, address)
                )

                if port in (21, 23):
                    warnings.append(
                        "Potential legacy FTP/Telnet listener on TCP {}."
                        .format(port)
                    )

        evidence.extend(listeners or [
            "No listeners observed on TCP ports 21, 22 or 23."
        ])

        evidence.append(
            "Limitation: SSH may use a custom port. "
            "A listening port alone does not identify its application."
        )

    evidence.extend(warnings)
    evidence.extend(unknowns)
    evidence.append(
        "Inspection scope: Local configuration and socket metadata only. "
        "No login attempts, service changes or remote connections."
    )

    if warnings:
        status = "WARN"
        summary = "Remote-access configuration requires review."
    elif unknowns:
        status = "UNKNOWN"
        summary = (
            "Remote-access evidence collected; effective security "
            "configuration remains unverified."
        )
    else:
        status = "INFO"
        summary = "No selected remote-access warning patterns observed."

    return result(status, summary, "\n".join(evidence))



def boot_encryption():
    """Inspect current boot and encryption metadata without changes."""
    evidence = ["Target: Running Linux session"]
    unknowns = []

    efi = Path("/sys/firmware/efi")

    if efi.is_dir():
        evidence.append("Firmware boot mode: UEFI")

        secure_boot = command_output(["mokutil", "--sb-state"])

        if secure_boot is None:
            evidence.append("Secure Boot: Status unavailable")
            unknowns.append("Secure Boot enforcement not verified.")
        else:
            lines = secure_boot.strip().splitlines()
            state = lines[0] if lines else "Unknown"
            evidence.append("Secure Boot tool reports: " + state)

            if "disabled" in state.lower():
                evidence.append(
                    "Review: Secure Boot is reported disabled. "
                    "This is a configuration observation, not proof "
                    "of compromise."
                )
            elif "enabled" not in state.lower():
                unknowns.append(
                    "Secure Boot state could not be interpreted."
                )
    else:
        evidence.append(
            "Firmware boot mode: Legacy BIOS or UEFI evidence unavailable"
        )
        evidence.append(
            "Secure Boot: Not assessable through the UEFI runtime interface"
        )

    devices = command_output(
        ["lsblk", "-n", "-o", "NAME,TYPE,FSTYPE,MOUNTPOINTS"]
    )

    if devices is None:
        unknowns.append("Block-device metadata unavailable.")
    else:
        lines = devices.splitlines()
        evidence.append(
            "Block-device entries observed: {}".format(len(lines))
        )

        encrypted = [
            line.strip()[:240]
            for line in lines
            if "crypto_LUKS" in line or " crypt " in " " + line + " "
        ]

        if encrypted:
            evidence.append(
                "Observed encryption-related block devices:"
            )
            evidence.extend(encrypted[:12])
        else:
            evidence.append(
                "No LUKS/dm-crypt indicators observed in "
                "the accessible block-device listing."
            )

    evidence.extend(unknowns)
    evidence.append(
        "Limitation: Metadata inspection does not prove full-disk "
        "encryption, key protection or boot-chain integrity. "
        "BitLocker and offline installations are not assessed."
    )
    evidence.append(
        "Safety: No partitions mounted, unlocked or modified."
    )

    if unknowns:
        status = "UNKNOWN"
        summary = "Boot or encryption evidence is incomplete."
    else:
        status = "INFO"
        summary = (
            "Boot and encryption metadata collected; "
            "security properties not certified."
        )

    return result(status, summary, "\n".join(evidence))



def patch_evidence():
    """Inspect local OS and package metadata without repository access."""
    import datetime
    import platform

    evidence = ["Target: Running Linux session"]
    unknowns = []

    os_release = read_text("/etc/os-release")

    if os_release:
        identity = {}

        for line in os_release.splitlines():
            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            if key in ("PRETTY_NAME", "VERSION_ID", "ID"):
                identity[key] = value.strip().strip('"')

        evidence.append(
            "Operating system: {}".format(
                identity.get("PRETTY_NAME", "Not identified")
            )
        )
    else:
        unknowns.append("Operating-system release metadata unavailable.")

    evidence.append("Running kernel: " + platform.release())

    apt_lists = Path("/var/lib/apt/lists")
    timestamps = []

    if apt_lists.is_dir():
        try:
            for entry in apt_lists.iterdir():
                if not entry.is_file():
                    continue

                if entry.name in ("lock",):
                    continue

                if entry.name.endswith((
                    "_Packages", "_Packages.lz4",
                    "_Sources", "_InRelease", "_Release"
                )):
                    timestamps.append(entry.stat().st_mtime)

        except OSError:
            unknowns.append("APT package-index metadata inaccessible.")

        if timestamps:
            latest = datetime.datetime.fromtimestamp(
                max(timestamps)
            ).astimezone()

            evidence.append(
                "Newest local APT index modification: "
                + latest.strftime("%d %b %Y, %H:%M:%S %Z")
            )

            evidence.append(
                "Index modification time does not prove "
                "repository freshness or patch compliance."
            )
        else:
            unknowns.append(
                "No usable local APT index timestamps found."
            )
    else:
        unknowns.append("APT index directory unavailable.")

    dpkg_status = Path("/var/lib/dpkg/status")

    if dpkg_status.is_file():
        try:
            metadata = dpkg_status.stat()
            evidence.append(
                "Local dpkg status database: Present"
            )
            evidence.append(
                "dpkg status database size: {} bytes".format(
                    metadata.st_size
                )
            )
        except OSError:
            unknowns.append("dpkg status metadata inaccessible.")
    else:
        unknowns.append("dpkg status database unavailable.")

    evidence.extend(unknowns)
    evidence.append(
        "Limitation: No repository refresh, package upgrade simulation, "
        "CVE matching or internet connectivity was used. "
        "Installed security-update compliance is not established."
    )

    if unknowns:
        status = "UNKNOWN"
        summary = "Local patch evidence collected incompletely."
    else:
        status = "INFO"
        summary = (
            "Local OS and package metadata collected; "
            "security-update status not certified."
        )

    return result(status, summary, "\n".join(evidence))



def industrial_media():
    """Inspect local removable-media and service exposure metadata."""
    import re

    evidence = ["Target: Running Linux session"]
    unknowns = []
    observations = []

    usb_root = Path("/sys/bus/usb/devices")
    usb_count = 0

    if usb_root.is_dir():
        try:
            for entry in usb_root.iterdir():
                if not (entry / "idVendor").is_file():
                    continue
                if not (entry / "idProduct").is_file():
                    continue

                usb_count += 1

                if usb_count >= 100:
                    observations.append(
                        "USB inventory truncated at 100 devices."
                    )
                    break

            evidence.append(
                "USB devices observed: {}".format(usb_count)
            )
        except OSError:
            unknowns.append("USB device inventory inaccessible.")
    else:
        unknowns.append("USB sysfs inventory unavailable.")

    block_devices = command_output(
        ["lsblk", "-n", "-o", "NAME,RM,TYPE,TRAN"]
    )

    if block_devices is None:
        unknowns.append("Removable block-device inventory unavailable.")
    else:
        removable = []

        for line in block_devices.splitlines():
            fields = line.split()

            if len(fields) >= 3 and fields[1] == "1":
                removable.append(line.strip()[:200])

        evidence.append(
            "Removable block-device entries: {}".format(
                len(removable)
            )
        )

        evidence.extend(removable[:12])

    tcp = command_output(["ss", "-H", "-lnt"])
    udp = command_output(["ss", "-H", "-lnu"])

    interesting_ports = {
        21: "FTP",
        23: "Telnet",
        139: "NetBIOS",
        445: "SMB",
        502: "Modbus/TCP",
        102: "ISO-on-TCP",
        44818: "EtherNet/IP",
        4840: "OPC UA",
        20000: "DNP3",
    }

    observed = set()

    for protocol, output in (("TCP", tcp), ("UDP", udp)):
        if output is None:
            unknowns.append(
                "{} listener inventory unavailable.".format(protocol)
            )
            continue

        for line in output.splitlines():
            fields = line.split()

            if len(fields) < 5:
                continue

            address = fields[4]
            match = re.search(r":(\\d+)$", address)

            if not match:
                continue

            port = int(match.group(1))

            if port in interesting_ports:
                observed.add(
                    (protocol, port, interesting_ports[port])
                )

    if observed:
        for protocol, port, label in sorted(observed):
            observations.append(
                "{} port {} observed ({})".format(
                    protocol, port, label
                )
            )

        evidence.extend(observations)
    else:
        evidence.append(
            "No selected industrial/legacy listening ports observed."
        )
        evidence.extend(observations)

    evidence.extend(unknowns)
    evidence.append(
        "Limitation: Local listeners do not identify protocols "
        "or prove vulnerability. USB presence does not establish "
        "malicious activity. OT networks and PLCs were not scanned."
    )
    evidence.append(
        "Safety: No network probes, USB mounts, writes or device control."
    )

    if unknowns:
        status = "UNKNOWN"
        summary = "Industrial/media evidence collected incompletely."
    elif observed:
        status = "INFO"
        summary = (
            "Selected local listening ports observed; "
            "service identity and risk require verification."
        )
    else:
        status = "INFO"
        summary = (
            "Local USB and listener metadata collected; "
            "industrial security not certified."
        )

    return result(status, summary, "\n".join(evidence))


RUNNERS = {
    "access_control": access_control,
    "firewall": firewall,
    "privileged_accounts": privileged_accounts,
    "file_permissions": file_permissions,
    "remote_access": remote_access,
    "boot_encryption": boot_encryption,
    "patch_evidence": patch_evidence,
    "industrial_media": industrial_media,
}


def run_check(check_id):
    if check_id not in RUNNERS:
        raise ValueError("Unknown security check: " + str(check_id))
    try:
        return RUNNERS[check_id]()
    except Exception:
        return result(
            "UNKNOWN",
            "Security check could not complete.",
            "An unexpected read-only diagnostic error occurred.",
        )
