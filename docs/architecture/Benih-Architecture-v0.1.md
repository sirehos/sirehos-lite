# Sireh OS Lite 1.0 - Benih
## Architecture Baseline v0.1

Status: Draft
Base: Ubuntu 24.04 LTS (Noble)
Architecture: amd64

## 1. Purpose

Sireh OS Lite is an independent, lightweight,
USB-bootable Linux distribution designed for
infrastructure diagnostics, monitoring and automation.

## 2. Design Principles

- CLI-first
- Optional lightweight desktop
- Offline-first
- Read-only diagnostics by default
- Minimal dependencies
- Reproducible builds
- No proprietary employer code or configuration

## 3. Proposed OS Components

Base filesystem: debootstrap
Live boot: casper
Compression: SquashFS
Bootloader: GRUB (BIOS and UEFI)
Virtualization: QEMU/KVM

## 4. Sireh Core

Shared framework providing:

- CLI conventions
- Configuration management
- Logging
- Hardware and system discovery
- Structured diagnostic output
- Safe execution controls

## 5. Core Applications

OneScan
TimeShift
EvidencePack
PathFinder

## 6. Build Pipeline

Ubuntu package repositories
    |
    v
debootstrap root filesystem
    |
    v
Sireh Core and applications
    |
    v
Live-boot integration
    |
    v
SquashFS compression
    |
    v
GRUB ISO creation
    |
    v
QEMU/KVM validation
    |
    v
USB boot testing

## 7. Future Decisions

- Lightweight desktop selection
- Persistence design
- ISO signing and release process
- Hardware compatibility targets
- Security update policy
- Build reproducibility validation

## 8. Development Policy

Builds and tests must not modify the
Linux Mint host boot configuration.

No production credentials, employer
scripts, or proprietary configurations
are permitted in this repository.
