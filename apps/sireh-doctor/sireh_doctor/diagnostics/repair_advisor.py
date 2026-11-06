"""Deterministic, read-only Repair Advisor evidence synthesis."""

SOURCES = (
    ("Hardware Doctor", "hardware"),
    ("Storage Doctor", "storage"),
    ("OS & Boot Doctor", "osboot"),
    ("Crash Detective", "crash"),
    ("Security Doctor", "security"),
    ("Data Rescue", "rescue"),
)

PRIORITY = {
    "CRITICAL": 0,
    "FAIL": 0,
    "WARN": 1,
    "WARNING": 1,
    "UNKNOWN": 2,
    "ERROR": 2,
    "INFO": 3,
    "PASS": 4,
    "OK": 4,
}

def _status(value):
    status = str(value or "UNKNOWN").strip().upper()
    return status if status in PRIORITY else "UNKNOWN"

def _text(value):
    if isinstance(value, (str, int, float, bool)):
        return str(value)[:1000]
    return ""

def _recommendation(source, check, status):
    if status in ("UNKNOWN", "ERROR"):
        return (
            "The available evidence is insufficient. Review the "
            "original diagnostic result before drawing conclusions.",
            "SAFE READ-ONLY REVIEW",
        )

    name = (source + " " + check).lower()

    if "storage" in name or "smart" in name:
        return (
            "Protect important data first. Review SMART evidence "
            "before considering filesystem or disk repairs.",
            "MANUAL / POTENTIALLY DISRUPTIVE",
        )

    if "boot" in name or "efi" in name:
        return (
            "Review boot and EFI evidence. Record the existing "
            "configuration before considering manual changes.",
            "SAFE READ-ONLY REVIEW; BOOT CHANGES REQUIRE SEPARATE APPROVAL",
        )

    if "security" in name:
        return (
            "Compare the finding with the expected security policy "
            "before changing any settings.",
            "MANUAL REVIEW",
        )

    if "crash" in name:
        return (
            "Review timestamps and crash details. Correlate with "
            "hardware and storage evidence.",
            "SAFE READ-ONLY REVIEW",
        )

    if "hardware" in name:
        return (
            "Review hardware evidence and manufacturer guidance "
            "before attempting physical intervention.",
            "SAFE READ-ONLY REVIEW",
        )

    return (
        "Review the original evidence before deciding on repairs.",
        "SAFE READ-ONLY REVIEW",
    )

def _normalize(source, check, result):
    if not isinstance(result, dict):
        return None

    if source == "Storage Doctor" and isinstance(
        result.get("assessment"), dict
    ):
        result = result["assessment"]

    status = _status(result.get("status"))

    if status in ("PASS", "OK"):
        return None

    advice, risk = _recommendation(source, str(check), status)

    summary = (
        _text(result.get("summary"))
        or _text(result.get("message"))
        or "No detailed diagnostic summary available."
    )

    return {
        "source": source,
        "check": str(check),
        "status": status,
        "summary": summary,
        "recommendation": advice,
        "source_recommendation": _text(
            result.get("recommendation")
        ),
        "risk": risk,
    }

def build_plan(snapshots):
    """Use cached diagnostic findings only; never execute checks."""
    snapshots = snapshots if isinstance(snapshots, dict) else {}

    findings = []
    unassessed = []
    assessed = 0

    for source, key in SOURCES:
        results = snapshots.get(key)

        if not isinstance(results, dict) or not results:
            unassessed.append(source)
            continue

        valid = [
            (check, value)
            for check, value in results.items()
            if isinstance(value, dict)
            and (
                "status" in value
                or isinstance(value.get("assessment"), dict)
            )
        ]

        if not valid:
            unassessed.append(source)
            continue

        assessed += 1

        for check, value in valid:
            finding = _normalize(source, check, value)
            if finding is not None:
                findings.append(finding)

    findings.sort(
        key=lambda item: (
            PRIORITY.get(item["status"], 2),
            item["source"],
            item["check"],
        )
    )

    return {
        "findings": findings,
        "assessed_sources": assessed,
        "unassessed_sources": unassessed,
        "total_sources": len(SOURCES),
    }
