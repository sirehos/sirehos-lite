#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"
LOGDIR="$PROJECT/build/benih-1.0/logs"

RELEASE="noble"
ARCH="amd64"
MIRROR="http://archive.ubuntu.com/ubuntu"

echo "======================================"
echo " Sireh OS Lite 1.0 - Benih"
echo " Ubuntu RootFS Bootstrap"
echo "======================================"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[ERROR] Run with sudo."
    exit 1
fi

if [[ ! -d "$PROJECT/.git" ]]; then
    echo "[ERROR] Project repository missing."
    exit 1
fi

EXPECTED="$PROJECT/build/benih-1.0/rootfs"

if [[ "$(realpath -e "$ROOTFS")" != "$EXPECTED" ]]; then
    echo "[ERROR] Unexpected rootfs path."
    exit 1
fi

if [[ -L "$ROOTFS" ]]; then
    echo "[ERROR] RootFS must not be a symlink."
    exit 1
fi

if [[ -n "$(find "$ROOTFS" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "[ERROR] RootFS is not empty."
    exit 1
fi

if findmnt -rn -o TARGET | grep -Fxq "$ROOTFS"; then
    echo "[ERROR] RootFS is a mount point."
    exit 1
fi

if findmnt -rn -o TARGET | grep -Fq "$ROOTFS/"; then
    echo "[ERROR] Nested mounts detected."
    exit 1
fi

mkdir -p "$LOGDIR"

LOGFILE="$LOGDIR/debootstrap-$(date +%Y%m%d_%H%M%S).log"

echo "Release : $RELEASE"
echo "Arch    : $ARCH"
echo "RootFS  : $ROOTFS"
echo "Log     : $LOGFILE"

debootstrap \
    --arch="$ARCH" \
    --variant=minbase \
    "$RELEASE" \
    "$ROOTFS" \
    "$MIRROR" 2>&1 | tee "$LOGFILE"

echo
echo "[PASS] Ubuntu root filesystem created."
