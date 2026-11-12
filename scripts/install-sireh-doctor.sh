#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"
SOURCE="$PROJECT_DIR/apps/sireh-doctor/sireh_doctor"
BRANDING="$PROJECT_DIR/assets/branding/SirehOS_Lite_Emblem.png"

APP_PARENT="$ROOTFS/opt/sirehos/sireh-doctor"
APP_TARGET="$APP_PARENT/sireh_doctor"
BRAND_TARGET="$ROOTFS/opt/sirehos/assets/branding"
LAUNCHER="$ROOTFS/usr/local/bin/sireh-doctor"
DESKTOP="$ROOTFS/usr/share/applications/sireh-doctor.desktop"

echo "=== B021: Sireh Doctor Installer ==="

if [[ ! -d "$ROOTFS" || -L "$ROOTFS" ]]; then
    echo "ERROR: Invalid rootfs" >&2
    exit 1
fi

if [[ "$(stat -c %u "$ROOTFS")" != "$EUID" ]]; then
    echo "ERROR: Run as the rootfs owner, without sudo." >&2
    exit 1
fi

for required in \
    "$ROOTFS/etc/os-release" \
    "$SOURCE/main.py" \
    "$SOURCE/gui/main_window.py" \
    "$BRANDING"; do
    [[ -f "$required" && ! -L "$required" ]] || {
        echo "ERROR: Missing or unsafe source: $required" >&2
        exit 1
    }
done

for path in \
    "$ROOTFS/opt" \
    "$ROOTFS/opt/sirehos" \
    "$ROOTFS/opt/sirehos/sireh-doctor" \
    "$ROOTFS/opt/sirehos/assets" \
    "$ROOTFS/opt/sirehos/assets/branding" \
    "$ROOTFS/usr/local" \
    "$ROOTFS/usr/local/bin" \
    "$ROOTFS/usr/share" \
    "$ROOTFS/usr/share/applications"; do
    if [[ -L "$path" ]]; then
        echo "ERROR: Symlink in destination path: $path" >&2
        exit 1
    fi
done

for path in "$APP_PARENT" "$BRAND_TARGET" "$LAUNCHER" "$DESKTOP"; do
    if [[ -e "$path" || -L "$path" ]]; then
        echo "ERROR: Destination already exists: $path" >&2
        exit 1
    fi
done

if find "$SOURCE" -type l -print -quit | grep -q .; then
    echo "ERROR: Source symlink detected" >&2
    exit 1
fi

if [[ "${1:-}" != "--install" ]]; then
    echo "DRY RUN: preflight passed."
    echo "Application: $APP_TARGET"
    echo "Branding: $BRAND_TARGET"
    echo "Launcher: $LAUNCHER"
    echo "Desktop: $DESKTOP"
    echo "SMART helper: DISABLED"
    exit 0
fi

STAGE="$(mktemp -d)"
CREATED=()
CREATED_PARENTS=()

cleanup() {
    result=$?
    if [[ "$result" -ne 0 ]]; then
        echo "ERROR: Installation failed; removing created paths." >&2
        for ((i=${#CREATED[@]}-1; i>=0; i--)); do
            rm -rf -- "${CREATED[$i]}"
        done
    fi
    rm -rf -- "$STAGE"
    if [[ "$result" -ne 0 ]]; then
        for dir in "${CREATED_PARENTS[@]}"; do
            rmdir -- "$dir" 2>/dev/null || true
        done
    fi
}
trap cleanup EXIT

mkdir -p "$STAGE/app/sireh_doctor" "$STAGE/branding"

while IFS= read -r -d '' file; do
    relative="${file#"$SOURCE"/}"
    destination="$STAGE/app/sireh_doctor/$relative"
    install -d -m 0755 "$(dirname "$destination")"
    install -m 0644 "$file" "$destination"
done < <(find "$SOURCE" -type f -name '*.py' -print0)

install -m 0644 "$BRANDING" \
    "$STAGE/branding/SirehOS_Lite_Emblem.png"

python3 -m compileall -q "$STAGE/app/sireh_doctor"
find "$STAGE/app" -type d -name __pycache__ -prune -exec rm -rf -- {} +

cat > "$STAGE/launcher" <<'LAUNCHER_EOF'
#!/bin/sh
set -eu
unset PYTHONPATH PYTHONHOME
cd /opt/sirehos/sireh-doctor
exec /usr/bin/python3 -m sireh_doctor.main "$@"
LAUNCHER_EOF

chmod 0755 "$STAGE/launcher"
sh -n "$STAGE/launcher"

cat > "$STAGE/desktop" <<'DESKTOP_EOF'
[Desktop Entry]
Type=Application
Name=Sireh Doctor
Comment=Read-only system health and diagnostics
Exec=/usr/local/bin/sireh-doctor
Icon=/opt/sirehos/assets/branding/SirehOS_Lite_Emblem.png
Terminal=false
Categories=System;Utility;
StartupNotify=true
DESKTOP_EOF

# Publish only after staging and validation.
for dir in "$ROOTFS/opt/sirehos" "$ROOTFS/opt/sirehos/assets"; do
    if [[ -L "$dir" || ( -e "$dir" && ! -d "$dir" ) ]]; then
        echo "ERROR: Unsafe installation parent: $dir" >&2
        exit 1
    fi

    if [[ ! -d "$dir" ]]; then
        mkdir -- "$dir"
        chmod 0755 "$dir"
        CREATED_PARENTS=("$dir" "${CREATED_PARENTS[@]}")
    fi
done

mv -- "$STAGE/app" "$APP_PARENT"
CREATED+=("$APP_PARENT")

mv -- "$STAGE/branding" "$BRAND_TARGET"
CREATED+=("$BRAND_TARGET")

CREATED+=("$LAUNCHER")
install -m 0755 "$STAGE/launcher" "$LAUNCHER"

CREATED+=("$DESKTOP")
install -m 0644 "$STAGE/desktop" "$DESKTOP"

echo "PASS: Sireh Doctor installed into Benih rootfs."
echo "SMART helper remains disabled."
