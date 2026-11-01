#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"

SOURCE="$PROJECT_DIR/config/plymouth/sireh-benih"
EMBLEM="$PROJECT_DIR/assets/branding/SirehOS_Lite_Emblem.png"
TARGET="$ROOTFS/usr/share/plymouth/themes/sireh-benih"

echo "=== CONFIGURE SIREH PLYMOUTH ==="

for FILE in sireh-benih.plymouth sireh-benih.script; do
    if [ ! -s "$SOURCE/$FILE" ]; then
        echo "[FAIL] Missing source: $FILE"
        exit 1
    fi
done

if [ ! -s "$EMBLEM" ]; then
    echo "[FAIL] Sireh emblem missing"
    exit 1
fi

if [ ! -x "$ROOTFS/usr/bin/plymouth" ]; then
    echo "[FAIL] Plymouth not installed in rootfs"
    exit 1
fi

sudo install -d -m 755 "$TARGET"

sudo install -m 644 "$EMBLEM" \
    "$TARGET/emblem.png"

for FILE in sireh-benih.plymouth sireh-benih.script; do
    sudo install -m 644 "$SOURCE/$FILE" "$TARGET/$FILE"
done

sudo chroot "$ROOTFS" update-alternatives \
    --install \
    /usr/share/plymouth/themes/default.plymouth \
    default.plymouth \
    /usr/share/plymouth/themes/sireh-benih/sireh-benih.plymouth \
    100

sudo chroot "$ROOTFS" update-alternatives \
    --set default.plymouth \
    /usr/share/plymouth/themes/sireh-benih/sireh-benih.plymouth

echo
echo "=== VERIFY PLYMOUTH ==="

sudo chroot "$ROOTFS" update-alternatives \
    --query default.plymouth | grep -E 'Status:|Value:'

for FILE in emblem.png sireh-benih.plymouth sireh-benih.script; do
    if [ -s "$TARGET/$FILE" ]; then
        echo "[PASS] $FILE"
    else
        echo "[FAIL] $FILE"
        exit 1
    fi
done

echo "=== SIREH PLYMOUTH CONFIGURATION COMPLETE ==="
