#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOTFS="$PROJECT_DIR/build/benih-1.0/rootfs"
CONFIG="$PROJECT_DIR/config/desktop"
WALLPAPER="SirehOS_Lite_V1.0_Benih.png"

echo "=== CONFIGURE SIREH DESKTOP ==="

SOURCES=(
    "$CONFIG/pcmanfm-settings.conf"
    "$CONFIG/openbox-rc.xml"
    "$CONFIG/lxqt-panel.conf"
    "$CONFIG/lightdm-gtk-greeter.conf"
    "$CONFIG/Sireh-Terminal.desktop"
    "$PROJECT_DIR/assets/wallpapers/$WALLPAPER"
)

for FILE in "${SOURCES[@]}"; do
    if [ ! -s "$FILE" ]; then
        echo "[FAIL] Missing source: $FILE"
        exit 1
    fi
done

sudo install -D -m 644 \
    "$CONFIG/pcmanfm-settings.conf" \
    "$ROOTFS/usr/share/pcmanfm-qt/lxqt/settings.conf"

sudo install -D -m 644 \
    "$CONFIG/pcmanfm-settings.conf" \
    "$ROOTFS/etc/skel/.config/pcmanfm-qt/lxqt/settings.conf"

sudo install -D -m 644 \
    "$CONFIG/openbox-rc.xml" \
    "$ROOTFS/etc/xdg/openbox/rc.xml"

sudo install -D -m 644 \
    "$CONFIG/lxqt-panel.conf" \
    "$ROOTFS/etc/xdg/lxqt/panel.conf"

sudo install -D -m 644 \
    "$CONFIG/lightdm-gtk-greeter.conf" \
    "$ROOTFS/etc/lightdm/lightdm-gtk-greeter.conf"

sudo install -D -m 644 \
    "$CONFIG/Sireh-Terminal.desktop" \
    "$ROOTFS/usr/share/applications/Sireh-Terminal.desktop"

sudo install -D -m 755 \
    "$CONFIG/Sireh-Terminal.desktop" \
    "$ROOTFS/etc/skel/Desktop/Sireh-Terminal.desktop"

sudo install -D -m 644 \
    "$PROJECT_DIR/assets/wallpapers/$WALLPAPER" \
    "$ROOTFS/usr/share/backgrounds/sirehos/$WALLPAPER"

echo
echo "=== VERIFY INSTALLED FILES ==="

for FILE in \
    "$ROOTFS/usr/share/pcmanfm-qt/lxqt/settings.conf" \
    "$ROOTFS/etc/xdg/openbox/rc.xml" \
    "$ROOTFS/etc/xdg/lxqt/panel.conf" \
    "$ROOTFS/etc/lightdm/lightdm-gtk-greeter.conf" \
    "$ROOTFS/etc/skel/Desktop/Sireh-Terminal.desktop" \
    "$ROOTFS/usr/share/backgrounds/sirehos/$WALLPAPER"
do
    if [ -s "$FILE" ]; then
        echo "[PASS] ${FILE#$ROOTFS/}"
    else
        echo "[FAIL] $FILE"
        exit 1
    fi
done

echo "=== SIREH DESKTOP CONFIGURATION COMPLETE ==="
