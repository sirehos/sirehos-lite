"""SD-01: sequential, read-only master diagnostic audit."""

from datetime import datetime
from sireh_doctor.diagnostics import (
    hardware, hardware_health, storage_inventory,
    os_boot, crash_detective, security_doctor,
)
from sireh_doctor.diagnostics.health_report import normalize_status

AREAS = (
    ("Hardware Doctor", "hardware"),
    ("Storage Doctor", "storage"),
    ("OS & Boot Doctor", "osboot"),
    ("Crash Detective", "crash"),
    ("Security Doctor", "security"),
)

def timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def outcome(status, summary):
    return {
        "status": normalize_status(status),
        "summary": str(summary)[:500],
        "collected_at": timestamp(),
    }

def tasks():
    """Yield individual registered checks in execution order."""
    yield ("hardware", "hardware", "Hardware assessment")
    yield ("storage", "inventory", "Storage discovery")

    for check in os_boot.CHECKS:
        yield ("osboot", check, os_boot.CHECKS[check][0])

    for check in crash_detective.CHECKS:
        yield ("crash", check, crash_detective.CHECKS[check])

    for check in security_doctor.CHECKS:
        yield ("security", check, security_doctor.CHECKS[check])

def run_task(area, check):
    """Reuse existing engines; never execute repair operations."""
    if area == "hardware":
        data = hardware.collect()
        assessment = hardware_health.assess(data)
        findings = assessment.get("findings", [])
        results = {}
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            key = str(
                finding.get("check")
                or finding.get("component")
                or "Hardware finding"
            )
            if key in results:
                key += " ({})".format(index + 1)
            results[key] = outcome(
                finding.get("status"),
                finding.get("summary", "No summary available."),
            )
        return results or {
            "hardware": outcome(
                "UNKNOWN", "No hardware findings available."
            )
        }

    if area == "storage":
        inventory = storage_inventory.collect_storage_inventory()
        devices = inventory.get("devices", [])
        if inventory.get("status") != "AVAILABLE":
            return {
                "inventory": outcome(
                    "UNKNOWN",
                    inventory.get("error")
                    or "Storage discovery unavailable.",
                )
            }
        return {
            "inventory": outcome(
                "UNKNOWN",
                "{} disk(s) discovered. SMART health has not "
                "been assessed by this master audit.".format(
                    len(devices) if isinstance(devices, list) else 0
                ),
            )
        }

    runners = {
        "osboot": os_boot.run_check,
        "crash": crash_detective.run_check,
        "security": security_doctor.run_check,
    }
    result = runners[area](check)
    if not isinstance(result, dict):
        return {check: outcome("UNKNOWN", "Invalid diagnostic result.")}

    result = dict(result)
    result["status"] = normalize_status(result.get("status"))
    result["collected_at"] = timestamp()
    return {check: result}

def summarize(results):
    counts = {
        "FAIL": 0, "WARN": 0, "PASS": 0, "UNKNOWN": 0
    }
    areas = {}
    for name, key in AREAS:
        findings = results.get(key, {})
        statuses = [
            normalize_status(value.get("status"))
            for value in findings.values()
            if isinstance(value, dict)
        ]
        for status in statuses:
            counts[status] += 1
        areas[name] = (
            "FAIL" if "FAIL" in statuses else
            "WARN" if "WARN" in statuses else
            "UNKNOWN" if "UNKNOWN" in statuses else
            "PASS" if statuses else "NOT ASSESSED"
        )
    return counts, areas
