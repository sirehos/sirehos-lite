#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE="$PROJECT_DIR/src/sireh-core/sireh"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"
TARGET="$ROOTFS/usr/local/bin/sireh"

echo "=== CONFIGURE SIREH CORE ==="

if [ ! -f "$SOURCE" ]; then
    echo "[FAIL] Sireh Core source missing"
    exit 1
fi

if [ ! -d "$ROOTFS/usr/local/bin" ]; then
    echo "[FAIL] Rootfs installation directory missing"
    exit 1
fi

python3 - "$SOURCE" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
compile(source.read_bytes(), str(source), "exec")
print("[PASS] Python syntax verified")
PY

sudo install -m 755 "$SOURCE" "$TARGET"

if ! sudo cmp -s "$SOURCE" "$TARGET"; then
    echo "[FAIL] Installed file differs from source"
    exit 1
fi

echo "[PASS] Sireh Core installed"

sudo chroot "$ROOTFS" \
    /usr/local/bin/sireh --version

echo "=== SIREH CORE CONFIGURATION COMPLETE ==="
