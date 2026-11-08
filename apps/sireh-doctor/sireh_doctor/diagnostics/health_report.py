"""SD-10: deterministic reporting from existing diagnostic evidence."""

from datetime import datetime, timezone

SOURCES = (
    ("Hardware Doctor", "hardware"),
    ("Storage Doctor", "storage"),
    ("OS & Boot Doctor", "osboot"),
    ("Crash Detective", "crash"),
    ("Security Doctor", "security"),
)

PRIORITY = {
    "FAIL": 0, "WARN": 1, "UNKNOWN": 2, "PASS": 3,
}

def normalize_status(value):
    value = str(value or "UNKNOWN").strip().upper()
    return {
        "CRITICAL": "FAIL", "ERROR": "UNKNOWN",
        "WARNING": "WARN", "OK": "PASS",
        "INFO": "UNKNOWN",
    }.get(value, value if value in PRIORITY else "UNKNOWN")

def safe_text(value):
    if isinstance(value, (str, int, float, bool)):
        return str(value).replace("\x00", "")[:1500]
    return ""

def build_report(snapshots, generated_at=None):
    """Read cached results only. Never execute diagnostics."""
    snapshots = snapshots if isinstance(snapshots, dict) else {}
    generated_at = generated_at or datetime.now(
        timezone.utc
    ).astimezone().isoformat(timespec="seconds")

    sections = []
    all_findings = []

    for name, key in SOURCES:
        raw = snapshots.get(key)
        findings = []

        if isinstance(raw, dict):
            for check, value in raw.items():
                if not isinstance(value, dict):
                    continue

                assessment = value.get("assessment")
                item = (
                    assessment
                    if isinstance(assessment, dict)
                    else value
                )

                if "status" not in item:
                    continue

                status = normalize_status(item.get("status"))
                summary = (
                    safe_text(item.get("summary"))
                    or safe_text(item.get("message"))
                    or "No additional explanation provided."
                )

                finding = {
                    "source": name,
                    "check": str(check)[:150],
                    "status": status,
                    "summary": summary,
                    "collected_at": (
                        safe_text(item.get("collected_at"))
                        or safe_text(item.get("timestamp"))
                        or "Not recorded"
                    ),
                }
                findings.append(finding)
                all_findings.append(finding)

        if not findings:
            overall = "NOT ASSESSED"
        else:
            overall = min(
                (f["status"] for f in findings),
                key=lambda s: PRIORITY[s],
            )

        sections.append({
            "name": name,
            "status": overall,
            "findings": findings,
        })

    sections.append({
        "name": "Data Rescue",
        "status": "NOT ASSESSED",
        "findings": [],
        "note": (
            "Discovery-only preview. Drive inventory does not "
            "establish recovery success or overall drive health."
        ),
    })

    counts = {
        status: sum(
            f["status"] == status for f in all_findings
        )
        for status in ("FAIL", "WARN", "UNKNOWN", "PASS")
    }
    assessed = sum(
        section["status"] != "NOT ASSESSED"
        for section in sections
    )
    unassessed = [
        section["name"] for section in sections
        if section["status"] == "NOT ASSESSED"
    ]

    if counts["FAIL"]:
        headline = (
            f"{counts['FAIL']} failing diagnostic finding(s) "
            "require attention."
        )
    elif counts["WARN"]:
        headline = (
            f"{counts['WARN']} warning finding(s) "
            "require review."
        )
    elif counts["UNKNOWN"]:
        headline = (
            "Available evidence includes inconclusive findings."
        )
    elif assessed:
        headline = (
            "No failures or warnings were reported by the "
            "completed checks."
        )
    else:
        headline = "No diagnostic checks have been assessed."

    summary = (
        f"{headline} {assessed} of {len(sections)} diagnostic "
        f"areas assessed. {len(unassessed)} area(s) remain "
        "not assessed. This report reflects cached evidence "
        "only, not a new scan or a complete health guarantee."
    )

    return {
        "generated_at": generated_at,
        "sections": sections,
        "findings": sorted(
            all_findings,
            key=lambda f: (
                PRIORITY[f["status"]],
                f["source"],
                f["check"],
            ),
        ),
        "counts": counts,
        "assessed": assessed,
        "total": len(sections),
        "unassessed": unassessed,
        "summary": summary,
    }

def render_report(report, markdown=False):
    """Produce portable UTF-8 text or Markdown."""
    lines = []
    if markdown:
        lines.extend(["# Sireh Doctor — Health Report", ""])
    else:
        lines.extend(["SIREH DOCTOR — HEALTH REPORT", "=" * 40])

    lines.extend([
        f"Generated: {report['generated_at']}",
        "Diagnostic collection times: shown where available; "
        "otherwise not recorded.",
        "",
        "EXECUTIVE SUMMARY",
        report["summary"],
        "",
        "SYSTEM SCORECARD",
    ])

    for section in report["sections"]:
        lines.append(
            f"[{section['status']}] {section['name']} "
            f"({len(section['findings'])} recorded checks)"
        )
        if section.get("note"):
            lines.append(f"  {section['note']}")

    lines.extend(["", "DETAILED FINDINGS"])

    if not report["findings"]:
        lines.append("No completed diagnostic findings available.")

    for item in report["findings"]:
        lines.extend([
            "",
            f"[{item['status']}] "
            f"{item['source']} — {item['check']}",
            f"Evidence: {item['summary']}",
            f"Collection time: {item['collected_at']}",
        ])

    lines.extend([
        "",
        "LIMITATIONS AND SAFETY",
        "Report generated from existing in-memory results.",
        "No diagnostic commands, repairs, mounts, or disk "
        "modifications were performed by Health Report.",
        "NOT ASSESSED and UNKNOWN must not be interpreted "
        "as PASS.",
        "Explicit export writes only to the destination "
        "selected by the user.",
        "",
    ])

    return "\n".join(lines)
