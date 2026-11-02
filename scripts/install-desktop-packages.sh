#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"
MANIFEST="$PROJECT/config/packages/desktop.txt"

echo "======================================"
echo " Sireh OS Lite 1.0 - Benih"
echo " Desktop Package Installation"
echo "======================================"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[ERROR] Run with sudo."
    exit 1
fi

if [[ ! -d "$PROJECT/.git" ]]; then
    echo "[ERROR] Project repository missing."
    exit 1
fi

if [[ -L "$ROOTFS" || ! -f "$ROOTFS/etc/os-release" ]]; then
    echo "[ERROR] Invalid rootfs."
    exit 1
fi

if [[ "$(realpath -e "$ROOTFS")" != "$ROOTFS" ]]; then
    echo "[ERROR] Unexpected rootfs path."
    exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "[ERROR] Desktop package manifest missing."
    exit 1
fi

mapfile -t PACKAGES < <(
    grep -vE '^[[:space:]]*(#|$)' "$MANIFEST"
)

if [[ "${#PACKAGES[@]}" -eq 0 ]]; then
    echo "[ERROR] Empty package manifest."
    exit 1
fi

echo "Packages: ${#PACKAGES[@]}"
printf '  %s\n' "${PACKAGES[@]}"

echo
echo "Installing desktop packages..."

chroot "$ROOTFS" /usr/bin/apt-get update

chroot "$ROOTFS" /usr/bin/apt-get install \
    -y --no-install-recommends \
    "${PACKAGES[@]}"

echo
echo "Verifying installation..."

for package in "${PACKAGES[@]}"; do
    status="$(
        chroot "$ROOTFS" \
            dpkg-query -W -f='${Status}' "$package"
    )"

    if [[ "$status" != "install ok installed" ]]; then
        echo "[ERROR] Package verification failed: $package"
        exit 1
    fi

    echo "[PASS] $package"
done

echo
echo "[PASS] Desktop package installation complete."
