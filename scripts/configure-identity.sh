#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"
CONFIG="$PROJECT_DIR/config/identity"

echo "=== CONFIGURE SIREH SYSTEM IDENTITY ==="

for FILE in os-release issue issue.net motd; do
    if [ ! -s "$CONFIG/$FILE" ]; then
        echo "[FAIL] Missing identity source: $FILE"
        exit 1
    fi
done

for FILE in os-release issue issue.net motd; do
    TARGET="$ROOTFS/etc/$FILE"

    if [ -L "$TARGET" ]; then
        echo "[INFO] Resolving symbolic link: $FILE"

        LINK="$(readlink "$TARGET")"

        if [[ "$LINK" = /* ]]; then
            TARGET="$ROOTFS$LINK"
        else
            echo "[STOP] Relative symbolic link requires review: $FILE"
            exit 1
        fi
    fi

    sudo install -m 644 "$CONFIG/$FILE" "$TARGET"

    if sudo cmp -s "$CONFIG/$FILE" "$TARGET"; then
        echo "[PASS] $FILE"
    else
        echo "[FAIL] $FILE"
        exit 1
    fi
done

echo "=== SIREH SYSTEM IDENTITY COMPLETE ==="
