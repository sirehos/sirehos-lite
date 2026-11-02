# Sireh Doctor — Benih 1.0 Acceptance Criteria

Status: Development baseline
Platform: Sireh OS Lite 1.0 Benih
GUI: Python 3 / PyQt5
Operating model: Offline-first, read-only by default

## Core principles

1. Every feature must perform a real diagnostic function.
2. Never modify a target disk or operating system during diagnosis.
3. Distinguish observed facts, suspected causes and unknowns.
4. Explain findings in language understandable to beginners.
5. Allow engineers to inspect supporting technical evidence.
6. Handle missing hardware, permissions and tools gracefully.
7. Never report PASS merely because a check could not run.
8. Do not require internet access for core diagnostics.

## SD-01 — Full Health Check

- Detect the current machine and available diagnostic targets.
- Execute supported health checks.
- Summarize PASS, WARN, FAIL and UNKNOWN findings.
- Identify the most important issues and suggested next actions.

## SD-02 — Hardware Doctor

- Report CPU, RAM, motherboard and firmware information.
- Inspect available thermal, battery and hardware indicators.
- Highlight abnormal findings using defined thresholds.
- Clearly identify unavailable sensors.

## SD-03 — Storage Doctor

- Discover physical drives, partitions and filesystems.
- Read available SMART/NVMe health information.
- Assess capacity and reported storage errors.
- Avoid writing to or automatically mounting target drives.

## SD-04 — OS & Boot Doctor

- Identify accessible Windows and Linux installations.
- Inspect EFI and boot-related information read-only.
- Report missing or suspicious boot components.
- Distinguish confirmed errors from possible causes.

## SD-05 — Crash Detective

- Inspect available Linux crash and journal evidence.
- Identify accessible Windows offline crash evidence.
- Present event timelines where evidence permits.
- Explain limitations when logs cannot be decoded.

## SD-06 — Security Doctor

- Inspect supported firmware and boot-security indicators.
- Report available offline security and update evidence.
- Avoid claiming a system is vulnerability-free.
- Clearly explain when vulnerability assessment is incomplete.

## SD-07 — Data Rescue

- Discover accessible files and candidate recovery sources.
- Provide a safe, explicitly authorized copy/export workflow.
- Validate the destination before copying.
- Warn users when failing media requires specialist handling.

## SD-08 — Repair Advisor

- Recommend actions based on diagnostic evidence.
- Separate informational, low-risk and destructive actions.
- Explain risks and prerequisites.
- Do not automatically execute repairs.

## SD-09 — Command Clinic

- Explain supported diagnostic commands in plain English.
- Display command purpose, expected output and risk level.
- Execute only approved, read-only diagnostic commands.
- Protect sensitive information in displayed or exported output.

## SD-10 — Health Report

- Generate a human-readable diagnostic summary.
- Export structured JSON and readable HTML.
- Include timestamps, check results and supporting evidence.
- Warn about sensitive information before export.

## Release acceptance

- All ten sections provide functional, demonstrable capability.
- GUI remains responsive during diagnostics.
- Unsupported checks report UNKNOWN or NOT AVAILABLE.
- No unintended writes to examined target systems.
- Reports reflect actual collected evidence.
- Core functionality works offline.
- Tested in QEMU and on suitable physical hardware.
