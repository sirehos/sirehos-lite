#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"
HOOK_DIR="$ROOTFS/usr/share/initramfs-tools/scripts/casper-bottom"

echo "=== CONFIGURE SIREH CASPER HOOKS ==="

if [ ! -d "$HOOK_DIR" ]; then
    echo "[FAIL] Casper hook directory missing"
    exit 1
fi

DISABLE=(
    31disable_update_notifier
    41apt_cdrom
    53disable_unattended_upgrades
)

KEEP=(
    19keyboard
    25adduser
)

for NAME in "${DISABLE[@]}"; do
    FILE="$HOOK_DIR/$NAME"

    if [ ! -f "$FILE" ]; then
        echo "[FAIL] Required Casper hook missing: $NAME"
        exit 1
    fi
done

for NAME in "${KEEP[@]}"; do
    FILE="$HOOK_DIR/$NAME"

    if [ ! -x "$FILE" ]; then
        echo "[FAIL] Essential hook unavailable: $NAME"
        exit 1
    fi
done

for NAME in "${DISABLE[@]}"; do
    FILE="$HOOK_DIR/$NAME"

    sudo chmod a-x "$FILE"

    if [ ! -x "$FILE" ]; then
        echo "[PASS] Disabled: $NAME"
    else
        echo "[FAIL] Still executable: $NAME"
        exit 1
    fi
done

for NAME in "${KEEP[@]}"; do
    echo "[PASS] Preserved: $NAME"
done

echo "=== CASPER CONFIGURATION COMPLETE ==="
