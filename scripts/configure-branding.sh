#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sarvesh/SHAN/SirehOS"
ROOTFS="$PROJECT/build/benih-1.0/rootfs"

if (( EUID != 0 )); then
    echo "ERROR: Run with sudo." >&2
    exit 1
fi

if [[ ! -d "$ROOTFS/etc" ||
      ! -f "$ROOTFS/usr/lib/os-release" ]]; then
    echo "ERROR: Benih rootfs not found." >&2
    exit 1
fi

if [[ -L "$ROOTFS" ||
      "$(realpath "$ROOTFS")" != "$ROOTFS" ]]; then
    echo "ERROR: Unexpected rootfs path." >&2
    exit 1
fi

if ! grep -q '^VERSION_CODENAME=noble$' \
    "$ROOTFS/usr/lib/os-release"; then
    echo "ERROR: Expected Ubuntu Noble base." >&2
    exit 1
fi

echo "=== Configuring Sireh OS Lite Branding ==="

# Replace the Ubuntu os-release symlink with a local override.
if [[ -L "$ROOTFS/etc/os-release" ]]; then
    rm "$ROOTFS/etc/os-release"
fi

cat > "$ROOTFS/etc/os-release" <<'EOF'
NAME="Sireh OS Lite"
PRETTY_NAME="Sireh OS Lite 1.0 (Benih)"
ID=sirehos
ID_LIKE="ubuntu debian"
VERSION_ID="1.0"
VERSION="1.0 (Benih)"
VERSION_CODENAME=benih
UBUNTU_CODENAME=noble
HOME_URL="https://sirehos.org"
SUPPORT_URL="https://github.com/sirehos/sirehos-lite"
BUG_REPORT_URL="https://github.com/sirehos/sirehos-lite/issues"
EOF

cat > "$ROOTFS/etc/issue" <<'EOF'
Sireh OS Lite 1.0 (Benih) - \n \l
Ubuntu 24.04 LTS-based | Built for the infra.

EOF

cat > "$ROOTFS/etc/motd" <<'EOF'

Welcome to Sireh OS Lite 1.0 - Benih
Infrastructure Swiss Army Knife

CLI-first | Live USB | Open Source
Built for the infra.

Based on Ubuntu 24.04 LTS
https://sirehos.org

EOF

chmod 644 \
    "$ROOTFS/etc/os-release" \
    "$ROOTFS/etc/issue" \
    "$ROOTFS/etc/motd"

echo "[PASS] Sireh OS identity configured"
echo "[PASS] Console banner configured"
echo "[PASS] Welcome message configured"

# Disable Ubuntu dynamic MOTD scripts.
# Keep the files installed for package compatibility.
for motd_script in 00-header 10-help-text 50-motd-news; do
    motd_path="$ROOTFS/etc/update-motd.d/$motd_script"

    if [[ ! -f "$motd_path" ]]; then
        echo "ERROR: Missing MOTD script: $motd_script" >&2
        exit 1
    fi

    chmod a-x "$motd_path"
done

echo "[PASS] Ubuntu dynamic MOTD disabled"
