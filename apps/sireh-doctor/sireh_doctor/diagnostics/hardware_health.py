import math

"""Evidence-based hardware health findings for Sireh Doctor."""

import json

from sireh_doctor.diagnostics.hardware import collect


def assess_battery(battery):
    """Assess reported capacity retention, not battery safety."""

    name = battery.get("name", "Battery")
    health = battery.get("health_percent")

    finding = {
        "component": name,
        "check": "Battery capacity retention",
        "status": "UNKNOWN",
        "measured_percent": health,
        "summary": "",
        "recommendation": "",
    }

    if (
        not isinstance(health, (int, float))
        or isinstance(health, bool)
        or not 0 <= health <= 120
    ):
        finding["summary"] = (
            "Battery capacity health could not be determined."
        )
        finding["recommendation"] = (
            "Check whether the battery exposes full-charge "
            "and design-capacity measurements."
        )
        return finding

    if health >= 80:
        finding["status"] = "PASS"
        finding["summary"] = (
            f"Reported capacity retention is {health:.1f}%."
        )
        finding["recommendation"] = (
            "No capacity-related action indicated by this check."
        )

    elif health >= 60:
        finding["status"] = "WARN"
        finding["summary"] = (
            f"Reported capacity has reduced to {health:.1f}% "
            "of its original design capacity."
        )
        finding["recommendation"] = (
            "Expect potentially shorter battery runtime. "
            "Consider replacement if runtime is insufficient."
        )

    else:
        finding["status"] = "WARN"
        finding["summary"] = (
            f"Reported capacity is substantially reduced "
            f"to {health:.1f}% of design capacity."
        )
        finding["recommendation"] = (
            "Review battery runtime and replacement options. "
            "This result alone does not establish a safety fault."
        )

    return finding



def assess_cpu_thermal(data):
    """Assess thermal headroom using reported hardware limits."""
    evidence = data.get("thermal_evidence", {})
    current = evidence.get("package_c")
    critical = evidence.get("critical_c")
    alarm = evidence.get("critical_alarm")

    finding = {
        "component": "CPU",
        "check": "Thermal headroom",
        "status": "UNKNOWN",
        "summary": "Thermal limits or temperature unavailable.",
        "recommendation": "Check CPU sensor availability.",
    }

    if alarm is True:
        finding.update({
            "status": "FAIL",
            "summary": "CPU critical-temperature alarm is asserted.",
            "recommendation": (
                "Reduce workload and investigate cooling immediately."
            ),
        })
        return finding

    if (
        not isinstance(current, (int, float))
        or isinstance(current, bool)
        or not math.isfinite(current)
        or not isinstance(critical, (int, float))
        or isinstance(critical, bool)
        or not math.isfinite(critical)
        or critical <= 0
    ):
        return finding

    headroom = critical - current

    if headroom <= 0:
        status = "FAIL"
        advice = "Investigate cooling and reduce CPU workload."
    elif headroom < 20:
        status = "WARN"
        advice = "Monitor temperatures and check cooling under load."
    else:
        status = "PASS"
        advice = (
            "No immediate thermal-limit concern in this snapshot. "
            "This is not a sustained-load test."
        )

    finding.update({
        "status": status,
        "summary": (
            f"CPU temperature {current:.1f}°C; "
            f"critical limit {critical:.1f}°C; "
            f"headroom {headroom:.1f}°C."
        ),
        "recommendation": advice,
    })

    return finding


def assess_cpu_throttling(data):
    """Interpret reported counters without claiming current throttling."""
    evidence = data.get("thermal_evidence", {})
    counters = evidence.get("throttle_counts", {})

    values = [
        count
        for cpu in counters.values()
        for count in cpu.values()
        if (
            isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 0
        )
    ]

    if not values:
        status = "UNKNOWN"
        summary = "Thermal throttling counters unavailable."
        advice = "Cannot determine throttling history."
    elif any(count > 0 for count in values):
        status = "WARN"
        summary = (
            "One or more thermal throttling counters are nonzero. "
            "These may represent earlier events."
        )
        advice = (
            "Compare counter values over time to identify "
            "new throttling events."
        )
    else:
        status = "PASS"
        summary = (
            "All available thermal throttling counters are zero."
        )
        advice = (
            "No throttling events reported by these counters "
            "in the current snapshot."
        )

    return {
        "component": "CPU",
        "check": "Thermal throttling",
        "status": status,
        "summary": summary,
        "recommendation": advice,
    }


def assess_memory(data):
    """Assess current available memory, not physical RAM integrity."""

    memory = data.get("memory", {})

    def parse_kb(value):
        try:
            return int(value.split()[0])
        except (AttributeError, ValueError, IndexError):
            return None

    total = parse_kb(memory.get("total"))
    available = parse_kb(memory.get("available"))

    finding = {
        "component": "Memory",
        "check": "Available RAM",
        "status": "UNKNOWN",
        "summary": "Memory availability could not be determined.",
        "recommendation": (
            "Check whether Linux exposes MemTotal and MemAvailable."
        ),
    }

    if (
        total is None or available is None
        or total <= 0 or available < 0 or available > total
    ):
        return finding

    percent = available / total * 100

    if percent >= 20:
        status = "PASS"
        advice = (
            "No immediate memory-availability concern in this "
            "snapshot. This does not test RAM hardware integrity."
        )
    elif percent >= 10:
        status = "WARN"
        advice = (
            "Available memory is reduced. Review application "
            "memory consumption if the system is slow."
        )
    else:
        status = "WARN"
        advice = (
            "Very little memory is available. Investigate "
            "memory pressure and running applications."
        )

    finding.update({
        "status": status,
        "summary": (
            f"Available RAM is {percent:.1f}% of total memory."
        ),
        "recommendation": advice,
    })

    return finding


def assess_cooling_fan(data):
    """Assess fan rotation without assuming a fixed RPM requirement."""

    fans = data.get("fan", {}).get("fans", [])

    finding = {
        "component": "Cooling Fan",
        "check": "Fan rotation",
        "status": "UNKNOWN",
        "summary": "Fan rotation could not be confirmed.",
        "recommendation": (
            "Check sensor availability. Some systems use "
            "fan-stop modes or do not expose fan RPM."
        ),
    }

    valid = [
        fan.get("rpm")
        for fan in fans
        if isinstance(fan.get("rpm"), int)
        and not isinstance(fan.get("rpm"), bool)
        and fan.get("rpm") >= 0
    ]

    if not valid:
        return finding

    rotating = [rpm for rpm in valid if rpm > 0]

    if rotating:
        finding.update({
            "status": "PASS",
            "summary": (
                f"Fan rotation detected; highest reported "
                f"speed {max(rotating):,} RPM."
            ),
            "recommendation": (
                "Fan rotation is confirmed. Cooling effectiveness "
                "requires temperature and throttling correlation."
            ),
        })
    else:
        finding.update({
            "status": "UNKNOWN",
            "summary": (
                "All available fan sensors currently report 0 RPM."
            ),
            "recommendation": (
                "This may be normal fan-stop behaviour. "
                "Investigate only alongside thermal evidence."
            ),
        })

    return finding


def assess_ac_power(data):
    """Report external power availability, not adapter electrical health."""

    supplies = data.get("power", {}).get("supplies", [])

    adapters = [
        item for item in supplies
        if item.get("type") == "Mains"
    ]

    finding = {
        "component": "AC Power",
        "check": "External power connection",
        "status": "UNKNOWN",
        "summary": "External power connection could not be determined.",
        "recommendation": (
            "The system may not expose an AC adapter sensor. "
            "This does not indicate an adapter failure."
        ),
    }

    readings = [
        str(item.get("online"))
        for item in adapters
        if str(item.get("online")) in ("0", "1")
    ]

    if not readings:
        return finding

    if "1" in readings:
        finding.update({
            "status": "PASS",
            "summary": "External power adapter is connected.",
            "recommendation": (
                "External power is detected. This check does not "
                "verify adapter voltage stability or wattage."
            ),
        })
    else:
        finding.update({
            "status": "INFO",
            "summary": "External power is not currently connected.",
            "recommendation": (
                "This is normal when intentionally operating "
                "on battery power."
            ),
        })

    return finding


def summarize_findings(findings):
    """Count diagnostic results without inventing an overall score."""

    counts = {
        "PASS": 0,
        "WARN": 0,
        "FAIL": 0,
        "INFO": 0,
        "UNKNOWN": 0,
    }

    for finding in findings:
        status = finding.get("status", "UNKNOWN")

        if status not in counts:
            status = "UNKNOWN"

        counts[status] += 1

    return {
        "total_checks": len(findings),
        "counts": counts,
        "scope": "IMPLEMENTED_CHECKS_ONLY",
        "overall_health_certified": False,
    }

def assess(data):
    """Return findings derived from collected hardware evidence."""

    findings = [
        assess_cpu_thermal(data),
        assess_cpu_throttling(data),
        assess_memory(data),
        assess_cooling_fan(data),
        assess_ac_power(data),
    ]

    for supply in data.get("power", {}).get("supplies", []):
        if supply.get("type") == "Battery":
            findings.append(assess_battery(supply))

    if not findings:
        findings.append({
            "component": "Battery",
            "check": "Battery capacity retention",
            "status": "UNKNOWN",
            "measured_percent": None,
            "summary": "No battery was detected.",
            "recommendation": (
                "This may be normal for desktop systems."
            ),
        })

    return {
        "scope": "CURRENT_RUNNING_LINUX",
        "assessment": "ADVISORY",
        "summary": summarize_findings(findings),
        "findings": findings,
    }


if __name__ == "__main__":
    print(json.dumps(assess(collect()), indent=2))
