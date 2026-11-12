#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build/benih-1.0"
ROOTFS="$BUILD_DIR/rootfs"
ISO_DIR="$BUILD_DIR/iso-beta4"
OUTPUT="$BUILD_DIR/SirehOS-Lite-1.0-Benih-Beta4.iso"

KERNEL_VERSION="6.8.0-147-generic"

if [[ -e "$OUTPUT" || -L "$OUTPUT" ]]; then
    echo "ERROR: Beta ISO already exists. Refusing overwrite."
    exit 1
fi

test -f "$ROOTFS/opt/sirehos/sireh-doctor/sireh_doctor/main.py" || {
    echo "ERROR: Sireh Doctor is missing from rootfs."
    exit 1
}

echo "=== SIREH OS LITE 1.0 BENIH ==="
echo "Beta 4 ISO Build — Sireh Doctor Integrated"

for tool in mksquashfs grub-mkrescue xorriso; do
    command -v "$tool" >/dev/null || {
        echo "ERROR: Missing $tool"
        exit 1
    }
done

for file in \
    "$ROOTFS/boot/vmlinuz-$KERNEL_VERSION" \
    "$ROOTFS/boot/initrd.img-$KERNEL_VERSION"; do
    test -s "$file" || {
        echo "ERROR: Missing $file"
        exit 1
    }
done

echo
echo "=== PREPARE ISO STAGING ==="

mkdir -p "$ISO_DIR/boot/grub" "$ISO_DIR/casper" "$ISO_DIR/.disk"

cp "$PROJECT_DIR/config/boot/grub.cfg" \
   "$ISO_DIR/boot/grub/grub.cfg"

sudo cp "$ROOTFS/boot/vmlinuz-$KERNEL_VERSION" \
   "$ISO_DIR/casper/vmlinuz"

sudo cp "$ROOTFS/boot/initrd.img-$KERNEL_VERSION" \
   "$ISO_DIR/casper/initrd"

sudo chmod 644 \
   "$ISO_DIR/casper/vmlinuz" \
   "$ISO_DIR/casper/initrd"

printf '%s\n' \
    "Sireh OS Lite 1.0 Benih Beta" \
    > "$ISO_DIR/.disk/info"

echo
echo "=== BUILD SQUASHFS ==="

sudo mksquashfs "$ROOTFS" \
    "$ISO_DIR/casper/filesystem.squashfs" \
    -noappend \
    -comp xz \
    -processors 4 \
    -b 1M \
    -e boot

echo
echo "=== GENERATE CASPER MD5 CHECKSUMS ==="

(
    cd "$ISO_DIR"

    find . -type f \
        ! -name 'md5sum.txt' \
        ! -path './boot.catalog' \
        -print0 |
        sort -z |
        xargs -0 -r md5sum > md5sum.txt
)

test -s "$ISO_DIR/md5sum.txt" || {
    echo "[FAIL] Casper checksum manifest is missing or empty"
    exit 1
}

echo "[PASS] Casper checksum manifest generated"

echo
echo "=== GENERATE BOOTABLE ISO ==="

grub-mkrescue \
    -o "$OUTPUT" \
    "$ISO_DIR" \
    -- \
    -volid SIREH_BENIH_GUI

echo
echo "=== BUILD RESULT ==="

ls -lh "$OUTPUT"

sha256sum "$OUTPUT"

echo
echo "=== BOOT METADATA ==="

xorriso -indev "$OUTPUT" \
    -report_el_torito plain 2>&1 | tail -n 15

echo
echo "BUILD COMPLETE"
