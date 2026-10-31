#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"

if (( EUID != 0 )); then
    echo "ERROR: Run this script using sudo." >&2
    exit 1
fi

if [[ ! -d "$ROOTFS/etc" || ! -d "$ROOTFS/usr/lib/systemd/system" ]]; then
    echo "ERROR: Benih rootfs not found." >&2
    exit 1
fi

if [[ -L "$ROOTFS" || "$(realpath "$ROOTFS")" != "$ROOTFS" ]]; then
    echo "ERROR: Unexpected rootfs path." >&2
    exit 1
fi

if ! grep -q '^VERSION_CODENAME=noble$' "$ROOTFS/etc/os-release"; then
    echo "ERROR: Expected Ubuntu Noble rootfs." >&2
    exit 1
fi

if [[ ! -x "$ROOTFS/usr/sbin/casper-getty" ||
      ! -x "$ROOTFS/usr/sbin/casper-login" ]]; then
    echo "ERROR: Casper console tools missing." >&2
    exit 1
fi

echo "=== Configuring Sireh OS Lite 1.0 Benih ==="

cat > "$ROOTFS/etc/casper.conf" <<'EOF'
export USERNAME="sireh"
export USERFULLNAME="Sireh OS Live User"
export HOST="sireh-benih"
export BUILD_SYSTEM="Ubuntu"
export FLAVOUR="Sireh"
EOF

printf 'sireh-benih\n' > "$ROOTFS/etc/hostname"

ln -sfn /usr/lib/systemd/system/multi-user.target \
    "$ROOTFS/etc/systemd/system/default.target"

OVERRIDE="$ROOTFS/etc/systemd/system/getty@tty1.service.d"
mkdir -p "$OVERRIDE"

cat > "$OVERRIDE/override.conf" <<'EOF'
[Unit]
ConditionKernelCommandLine=boot=casper

[Service]
ExecStart=
ExecStart=-/usr/sbin/casper-getty --noclear tty1 linux
EOF

echo "=== Configuration Complete ==="
echo "Username: sireh"
echo "Hostname: sireh-benih"
echo "Boot target: multi-user.target"
echo "Console: tty1 Casper autologin"
echo
echo "NOTE: Initramfs regeneration is still required."
