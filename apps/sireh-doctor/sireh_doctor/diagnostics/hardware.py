"""Read-only hardware discovery for the running Linux system."""

from pathlib import Path
import json
import platform


def read_text(path):
    try:
        return Path(path).read_text(
            encoding="utf-8", errors="replace"
        ).strip()
    except (OSError, PermissionError):
        return None


def cpu_info():
    result = {
        "architecture": platform.machine(),
        "model": None,
        "logical_processors": None,
    }

    cpuinfo = read_text("/proc/cpuinfo")

    if cpuinfo:
        for line in cpuinfo.splitlines():
            if line.startswith("model name"):
                result["model"] = line.split(":", 1)[1].strip()
                break

        result["logical_processors"] = sum(
            1 for line in cpuinfo.splitlines()
            if line.startswith("processor") and ":" in line
        )

    return result


def memory_info():
    meminfo = read_text("/proc/meminfo")

    if not meminfo:
        return {"status": "UNKNOWN"}

    values = {}

    for line in meminfo.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = value.strip()

    return {
        "total": values.get("MemTotal"),
        "available": values.get("MemAvailable"),
        "swap_total": values.get("SwapTotal"),
    }


def firmware_info():
    base = "/sys/class/dmi/id"

    fields = {
        "manufacturer": "sys_vendor",
        "product": "product_name",
        "board": "board_name",
        "bios_vendor": "bios_vendor",
        "bios_version": "bios_version",
        "bios_date": "bios_date",
    }

    return {
        name: read_text(f"{base}/{filename}")
        for name, filename in fields.items()
    }



def temperature_info():
    """Read CPU temperatures from Linux hwmon, without modifying hardware."""
    result = {
        "status": "UNKNOWN",
        "source": None,
        "package_c": None,
        "cores_c": [],
    }

    for device in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
        if read_text(device / "name") != "coretemp":
            continue

        result["source"] = "coretemp"

        for sensor in sorted(device.glob("temp*_input")):
            raw = read_text(sensor)

            try:
                celsius = int(raw) / 1000.0
            except (TypeError, ValueError):
                continue

            # Reject missing or implausible sensor readings.
            if not (-20 <= celsius <= 125):
                continue

            label_path = sensor.with_name(
                sensor.name.replace("_input", "_label")
            )
            label = read_text(label_path) or sensor.stem

            if label.lower().startswith("package"):
                result["package_c"] = celsius
            elif label.lower().startswith("core"):
                result["cores_c"].append({
                    "label": label,
                    "temperature_c": celsius,
                })

        if result["package_c"] is not None or result["cores_c"]:
            result["status"] = "AVAILABLE"

        break

    return result


def read_integer(path):
    """Return an integer or None when a sysfs value is unavailable."""
    value = read_text(path)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fan_info():
    """Discover reported fan speeds without changing fan controls."""
    fans = []

    for device in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
        driver = read_text(device / "name")

        for sensor in sorted(device.glob("fan*_input")):
            rpm = read_integer(sensor)

            if rpm is None or rpm < 0:
                continue

            fans.append({
                "source": driver or "UNKNOWN",
                "sensor": sensor.name,
                "rpm": rpm,
            })

    return {
        "status": "AVAILABLE" if fans else "UNKNOWN",
        "fans": fans,
    }


def power_info():
    """Read AC and battery information from Linux power_supply."""
    supplies = []
    base = Path("/sys/class/power_supply")

    fields = (
        "type", "status", "online", "capacity",
        "energy_full", "energy_full_design", "energy_now",
        "charge_full", "charge_full_design", "charge_now",
        "power_now", "current_now", "voltage_now",
    )

    for device in sorted(base.iterdir()) if base.is_dir() else []:
        if not device.is_dir():
            continue

        item = {"name": device.name}

        for field in fields:
            value = read_text(device / field)
            if value is not None:
                item[field] = value

        if item.get("type") == "Battery":
            full = read_integer(device / "energy_full")
            design = read_integer(device / "energy_full_design")

            if full is None or design is None:
                full = read_integer(device / "charge_full")
                design = read_integer(device / "charge_full_design")

            item["health_percent"] = (
                round(full / design * 100, 1)
                if full is not None and design is not None
                and full >= 0 and design > 0
                else None
            )

        supplies.append(item)

    return {
        "status": "AVAILABLE" if supplies else "UNKNOWN",
        "supplies": supplies,
    }


def thermal_evidence():
    """Read CPU critical limits, alarms and throttling counters."""
    result = {
        "package_c": None,
        "critical_c": None,
        "critical_alarm": None,
        "throttle_counts": {},
    }

    for device in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
        if read_text(device / "name") != "coretemp":
            continue

        for sensor in sorted(device.glob("temp*_input")):
            prefix = sensor.name.removesuffix("_input")
            label = read_text(device / f"{prefix}_label") or ""

            if not label.lower().startswith("package"):
                continue

            current = read_integer(sensor)
            critical = read_integer(device / f"{prefix}_crit")
            alarm = read_integer(device / f"{prefix}_crit_alarm")

            if current is not None:
                result["package_c"] = current / 1000

            if critical is not None and critical > 0:
                result["critical_c"] = critical / 1000

            if alarm in (0, 1):
                result["critical_alarm"] = bool(alarm)

            break

        break

    cpu_base = Path("/sys/devices/system/cpu")

    for cpu in sorted(cpu_base.glob("cpu[0-9]*")):
        throttle_dir = cpu / "thermal_throttle"

        if not throttle_dir.is_dir():
            continue

        counters = {}

        for name in ("core_throttle_count", "package_throttle_count"):
            count = read_integer(throttle_dir / name)

            if count is not None:
                counters[name] = count

        if counters:
            result["throttle_counts"][cpu.name] = counters

    return result

def collect():
    return {
        "scope": "CURRENT_RUNNING_LINUX",
        "cpu": cpu_info(),
        "memory": memory_info(),
        "firmware": firmware_info(),
        "temperature": temperature_info(),
        "fan": fan_info(),
        "power": power_info(),
        "thermal_evidence": thermal_evidence(),
    }


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
