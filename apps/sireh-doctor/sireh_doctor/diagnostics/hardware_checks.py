"""Dispatch individual read-only hardware assessments."""

from sireh_doctor.diagnostics.hardware_health import (
    assess_cpu_thermal,
    assess_cpu_throttling,
    assess_memory,
    assess_cooling_fan,
    assess_ac_power,
    assess_battery,
)


CHECKS = {
    "cpu_thermal": assess_cpu_thermal,
    "cpu_throttling": assess_cpu_throttling,
    "memory": assess_memory,
    "cooling_fan": assess_cooling_fan,
    "ac_power": assess_ac_power,
}


def run_check(check_id, data):
    """Assess one check using supplied hardware evidence.

    Battery IDs use the form battery:BAT0 or battery:BAT1.
    No hardware settings are changed.
    """

    if check_id in CHECKS:
        return CHECKS[check_id](data)

    if check_id.startswith("battery:"):
        name = check_id.partition(":")[2]

        if not name:
            raise ValueError("Battery name must not be empty")

        supplies = data.get("power", {}).get("supplies", [])

        for supply in supplies:
            if (
                supply.get("type") == "Battery"
                and supply.get("name") == name
            ):
                return assess_battery(supply)

        return {
            "component": name,
            "check": "Battery capacity retention",
            "status": "UNKNOWN",
            "measured_percent": None,
            "summary": (
                "The selected battery was not detected "
                "in the latest hardware evidence."
            ),
            "recommendation": (
                "Check battery detection before interpreting "
                "capacity health."
            ),
        }

    raise ValueError(f"Unsupported hardware check: {check_id}")


def finding_check_id(finding):
    """Identify the dispatcher check for a diagnostic finding."""

    component = finding.get("component")
    check = finding.get("check")

    if check == "Battery capacity retention":
        if (
            isinstance(component, str)
            and component.startswith("BAT")
            and component[3:].isdigit()
        ):
            return f"battery:{component}"
        return None

    for check_id, function in CHECKS.items():
        if check_id == "cpu_thermal":
            expected = ("CPU", "Thermal headroom")
        elif check_id == "cpu_throttling":
            expected = ("CPU", "Thermal throttling")
        elif check_id == "memory":
            expected = ("Memory", "Available RAM")
        elif check_id == "cooling_fan":
            expected = ("Cooling Fan", "Fan rotation")
        elif check_id == "ac_power":
            expected = ("AC Power", "External power connection")
        else:
            continue

        if (component, check) == expected:
            return check_id

    return None
