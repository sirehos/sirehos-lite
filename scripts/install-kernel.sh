#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"
LOGDIR="$PROJECT/build/benih-1.0/logs"
LOGFILE="$LOGDIR/kernel-install.log"

echo "======================================"
echo " Sireh OS Lite 1.0 - Benih"
echo " Kernel and Casper Installation"
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

if ! grep -Fxq 'VERSION_CODENAME=noble' \
    "$ROOTFS/etc/os-release"; then
    echo "[ERROR] Expected Ubuntu Noble rootfs."
    exit 1
fi

if [[ ! -x "$ROOTFS/usr/sbin/policy-rc.d" ]]; then
    echo "[ERROR] Service-start policy missing."
    exit 1
fi

if findmnt -rn -o TARGET |
   grep -Fq "$ROOTFS/"; then
    echo "[ERROR] Nested rootfs mounts detected."
    exit 1
fi

mkdir -p "$LOGDIR"

echo "[INFO] Installing Ubuntu kernel and Casper."
echo "[INFO] Log: $LOGFILE"

if [[ ! -d "$ROOTFS/proc" ||
      ! -d "$ROOTFS/sys" ||
      ! -d "$ROOTFS/dev" ]]; then
    echo "[ERROR] Required rootfs directories missing."
    exit 1
fi

chroot "$ROOTFS" \
    /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive \
    /usr/bin/apt-get \
    -y \
    --no-install-recommends \
    install \
    linux-image-generic \
    initramfs-tools \
    casper \
    2>&1 | tee "$LOGFILE"

echo "[PASS] Kernel installation command completed."
