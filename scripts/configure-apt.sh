#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"

echo "======================================"
echo " Sireh OS Lite 1.0 - Benih"
echo " Ubuntu APT Repository Configuration"
echo "======================================"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[ERROR] Run with sudo."
    exit 1
fi

if [[ -L "$ROOTFS" ]] ||
   [[ "$(realpath -e "$ROOTFS")" != "$ROOTFS" ]]; then
    echo "[ERROR] Unsafe rootfs path."
    exit 1
fi

if [[ ! -f "$ROOTFS/etc/os-release" ]]; then
    echo "[ERROR] Ubuntu rootfs missing."
    exit 1
fi

if ! grep -Fxq 'VERSION_CODENAME=noble' \
    "$ROOTFS/etc/os-release"; then
    echo "[ERROR] Expected Ubuntu Noble."
    exit 1
fi

if [[ ! -f "$ROOTFS/usr/share/keyrings/ubuntu-archive-keyring.gpg" ]]; then
    echo "[ERROR] Ubuntu archive keyring missing."
    exit 1
fi

if findmnt -rn -o TARGET |
   grep -Fq "$ROOTFS/"; then
    echo "[ERROR] Nested mounts detected."
    exit 1
fi

cat > "$ROOTFS/etc/apt/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu noble main universe
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu noble-updates main universe
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu noble-security main universe
SOURCES

echo "[PASS] Ubuntu repositories configured."
