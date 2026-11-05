"""Conservative interpretation of collected SMART health data."""


def _result(status, summary, recommendation, metrics=None):
    return {
        "status": status,
        "summary": summary,
        "recommendation": recommendation,
        "metrics": metrics if metrics is not None else {},
    }


def _nonnegative_integer(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def assess_smart(collection):
    """Interpret SMART evidence without claiming unsupported health."""
    if not isinstance(collection, dict):
        return _result(
            "UNKNOWN",
            "SMART collection result is invalid.",
            "Repeat SMART data collection.",
        )

    status = collection.get("status")

    if status != "AVAILABLE":
        return _result(
            "UNKNOWN",
            "SMART health could not be assessed.",
            collection.get("error")
            or "SMART data is unavailable for this device.",
        )

    data = collection.get("data")

    if not isinstance(data, dict):
        return _result(
            "UNKNOWN",
            "SMART data is missing or malformed.",
            "Repeat SMART data collection.",
        )

    metrics = {}
    evidence = []

    smart_status = data.get("smart_status")

    if isinstance(smart_status, dict):
        passed = smart_status.get("passed")

        if type(passed) is bool:
            metrics["overall_smart_passed"] = passed
            evidence.append(("FAIL" if not passed else "PASS",
                             "SMART overall assessment"))

    nvme = data.get("nvme_smart_health_information_log")

    if isinstance(nvme, dict):
        critical_warning = nvme.get("critical_warning")

        if _nonnegative_integer(critical_warning):
            metrics["nvme_critical_warning"] = critical_warning

            if critical_warning != 0:
                evidence.append(
                    ("FAIL", "NVMe critical warning is nonzero")
                )
            else:
                evidence.append(
                    ("PASS", "NVMe critical warning is zero")
                )

        media_errors = nvme.get("media_errors")

        if _nonnegative_integer(media_errors):
            metrics["nvme_media_errors"] = media_errors

            if media_errors > 0:
                evidence.append(
                    ("WARN", "NVMe media errors reported")
                )

        percentage_used = nvme.get("percentage_used")

        if _nonnegative_integer(percentage_used):
            metrics["nvme_percentage_used"] = percentage_used

            if percentage_used >= 100:
                evidence.append(
                    ("WARN", "NVMe endurance estimate reached 100%")
                )

    # ATA SMART raw attributes: interpret only established sector
    # counters. Other raw attributes may be vendor-specific.
    ata = data.get("ata_smart_attributes")

    if isinstance(ata, dict):
        table = ata.get("table")

        if isinstance(table, list):
            counters = {
                5: ("ata_reallocated_sectors",
                    "Reallocated sectors reported"),
                197: ("ata_pending_sectors",
                      "Pending sectors reported"),
                198: ("ata_uncorrectable_sectors",
                      "Uncorrectable sectors reported"),
            }

            for attribute in table:
                if not isinstance(attribute, dict):
                    continue

                attribute_id = attribute.get("id")

                if (
                    not _nonnegative_integer(attribute_id)
                    or attribute_id not in counters
                ):
                    continue

                raw = attribute.get("raw")

                if not isinstance(raw, dict):
                    continue

                value = raw.get("value")

                if not _nonnegative_integer(value):
                    continue

                key, warning = counters[attribute_id]
                metrics[key] = value

                if value > 0:
                    evidence.append(("WARN", warning))

    # Report measurements separately from health conclusions.
    # SMART temperature is conventionally reported in Celsius.
    temperature = data.get("temperature")

    if isinstance(temperature, dict):
        current = temperature.get("current")

        if (
            isinstance(current, (int, float))
            and not isinstance(current, bool)
            and -50 <= current <= 150
        ):
            metrics["temperature_c"] = current

    power_on_time = data.get("power_on_time")

    if isinstance(power_on_time, dict):
        hours = power_on_time.get("hours")

        if _nonnegative_integer(hours):
            metrics["power_on_hours"] = hours

    if isinstance(nvme, dict):
        kelvin = nvme.get("temperature")

        if _nonnegative_integer(kelvin) and 223 <= kelvin <= 423:
            metrics["temperature_c"] = kelvin - 273.15

        nvme_hours = nvme.get("power_on_hours")

        if _nonnegative_integer(nvme_hours):
            metrics["power_on_hours"] = nvme_hours

        spare = nvme.get("available_spare")

        if _nonnegative_integer(spare) and spare <= 100:
            metrics["nvme_available_spare_percent"] = spare

        threshold = nvme.get("available_spare_threshold")

        if _nonnegative_integer(threshold) and threshold <= 100:
            metrics["nvme_spare_threshold_percent"] = threshold

    if any(level == "FAIL" for level, _ in evidence):
        return _result(
            "FAIL",
            "SMART reports a critical health indicator.",
            "Back up important data and investigate the device.",
            metrics,
        )

    if any(level == "WARN" for level, _ in evidence):
        return _result(
            "WARN",
            "SMART reports an indicator requiring investigation.",
            "Review device history, backups and vendor diagnostics.",
            metrics,
        )

    if any(level == "PASS" for level, _ in evidence):
        return _result(
            "PASS",
            "Available SMART overall indicators report no failure.",
            "This is not a guarantee against future disk failure.",
            metrics,
        )

    return _result(
        "UNKNOWN",
        "No supported SMART health indicators were available.",
        "Check device-specific SMART capabilities.",
        metrics,
    )
