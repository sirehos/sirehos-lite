#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "========================================"
echo " SIREH OS LITE 1.0 BENIH"
echo " System Configuration Pipeline"
echo "========================================"

STEPS=(
    configure-casper-hooks.sh
    configure-plymouth.sh
    configure-sireh-core.sh
    configure-desktop.sh
    configure-identity.sh
)

for STEP in "${STEPS[@]}"; do
    SCRIPT="$PROJECT_DIR/scripts/$STEP"

    if [ ! -x "$SCRIPT" ]; then
        echo "[FAIL] Missing executable: $STEP"
        exit 1
    fi
done

for STEP in "${STEPS[@]}"; do
    echo
    echo "=== RUNNING: $STEP ==="
    "$PROJECT_DIR/scripts/$STEP"
done

echo
echo "[PASS] Sireh system configuration completed"
