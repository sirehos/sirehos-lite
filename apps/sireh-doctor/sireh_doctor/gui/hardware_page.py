"""Graphical hardware discovery page for Sireh Doctor."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sireh_doctor.diagnostics.hardware import collect
from sireh_doctor.diagnostics.hardware_health import (
    assess,
    summarize_findings,
)
from sireh_doctor.diagnostics.hardware_checks import (
    finding_check_id,
    run_check,
)
from datetime import datetime


def display(value):
    """Never present missing information as a successful reading."""
    if value is None or value == "":
        return "UNKNOWN"
    return str(value)


def gib(value):
    """Convert a Linux /proc/meminfo kB reading into GiB."""
    try:
        return f"{int(value.split()[0]) / 1048576:.2f} GiB"
    except (AttributeError, ValueError, IndexError):
        return "UNKNOWN"



def create_finding_card(finding, on_run=None, checked_at=None):
    """Create a read-only diagnostic finding card."""

    component = finding.get("component", "Hardware")
    check = finding.get("check", "Assessment")
    status = finding.get("status", "UNKNOWN")
    summary = finding.get("summary", "No assessment available.")
    recommendation = finding.get(
        "recommendation", "No recommendation available."
    )

    colors = {
        "PASS": ("#e4f3e9", "#176747"),
        "WARN": ("#fff1d6", "#956000"),
        "FAIL": ("#fce5e5", "#a92e2e"),
        "INFO": ("#e3effa", "#245f88"),
        "UNKNOWN": ("#e9edeb", "#596960"),
    }

    background, foreground = colors.get(
        status, colors["UNKNOWN"]
    )

    card = QFrame()
    card.setObjectName("findingCard")
    card.setStyleSheet("""
        QFrame#findingCard {
            background: #ffffff;
            border: 1px solid #dce7df;
            border-radius: 9px;
        }
    """)

    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 13, 16, 13)
    card_layout.setSpacing(8)

    header = QWidget()
    header_layout = QGridLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setColumnStretch(0, 1)

    title = QLabel(f"{component} — {check}")
    title.setWordWrap(True)
    title.setStyleSheet(
        "color: #193e30; font-size: 13px; font-weight: bold;"
    )

    badge = QLabel(status)
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(
        f"background: {background}; color: {foreground}; "
        "border-radius: 5px; padding: 5px 9px; "
        "font-size: 11px; font-weight: bold;"
    )

    header_layout.addWidget(title, 0, 0)
    header_layout.addWidget(badge, 0, 1)

    observation = QLabel(summary)
    observation.setWordWrap(True)
    observation.setTextInteractionFlags(Qt.TextSelectableByMouse)
    observation.setStyleSheet(
        "color: #365347; font-size: 12px;"
    )

    advice_title = QLabel("RECOMMENDATION")
    advice_title.setStyleSheet(
        "color: #63796d; font-size: 10px; font-weight: bold;"
    )

    advice = QLabel(recommendation)
    advice.setWordWrap(True)
    advice.setTextInteractionFlags(Qt.TextSelectableByMouse)
    advice.setStyleSheet(
        "color: #365347; font-size: 12px;"
    )

    card_layout.addWidget(header)
    card_layout.addWidget(observation)
    card_layout.addWidget(advice_title)
    card_layout.addWidget(advice)

    timestamp_text = (
        checked_at.strftime("%d %b %Y, %H:%M:%S %Z")
        if checked_at is not None
        else "Not yet checked"
    )

    timestamp_label = QLabel(
        f"Last checked: {timestamp_text}"
    )
    timestamp_label.setObjectName("lastCheckedLabel")
    timestamp_label.setStyleSheet(
        "color: #63796d; font-size: 11px;"
    )
    card_layout.addWidget(timestamp_label)

    run_button = QPushButton("Run Check")
    run_button.setObjectName("runCheckButton")
    run_button.setEnabled(on_run is not None)
    if on_run is not None:
        run_button.clicked.connect(on_run)
        run_button.setToolTip(
            "Run this read-only diagnostic again."
        )
    else:
        run_button.setToolTip(
            "Individual diagnostic execution is not yet connected."
        )
    run_button.setStyleSheet("""
        QPushButton#runCheckButton {
            background: #267b57;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 7px 13px;
            font-weight: bold;
        }
        QPushButton#runCheckButton:disabled {
            background: #dce6df;
            color: #718579;
        }
        QPushButton#runCheckButton:hover:enabled {
            background: #1d6245;
        }
    """)

    card_layout.addWidget(
        run_button, alignment=Qt.AlignLeft
    )

    return card


class HardwarePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(12)

        heading = QLabel("Hardware Doctor")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        description = QLabel(
            "SD-02  |  Read-only hardware discovery"
        )
        description.setObjectName("description")
        layout.addWidget(description)

        scope = QLabel(
            "Inspecting the currently running Linux system. "
            "This is not an inspection of an attached Windows disk."
        )
        scope.setWordWrap(True)
        scope.setStyleSheet("color: #536b60;")
        layout.addWidget(scope)

        self.refresh_button = QPushButton("Run All Checks")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background: #267b57;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d6245;
            }
        """)
        controls = QHBoxLayout()
        controls.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Clear All Results")
        self.clear_button.setObjectName("clearHardwareResults")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_results)
        controls.addWidget(self.clear_button)
        controls.addStretch()

        layout.addLayout(controls)

        # Summary of implemented diagnostic checks only.
        self.summary_cards = {}
        summary_row = QGridLayout()
        summary_row.setSpacing(8)

        card_colors = {
            "PASS": "#23764d",
            "WARN": "#a66b12",
            "FAIL": "#b13d3d",
            "INFO": "#326f98",
            "UNKNOWN": "#65746c",
        }

        for column, status in enumerate(card_colors):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #eaf0ec; "
                "border-radius: 8px; }"
            )

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 10, 6, 10)

            number = QLabel("0")
            number.setAlignment(Qt.AlignCenter)
            number.setStyleSheet(
                f"color: {card_colors[status]}; "
                "font-size: 24px; font-weight: bold;"
            )

            label = QLabel(status)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "color: #53665b; font-size: 10px; "
                "font-weight: bold;"
            )

            card_layout.addWidget(number)
            card_layout.addWidget(label)

            summary_row.addWidget(card, 0, column)
            self.summary_cards[status] = number

        layout.addLayout(summary_row)

        self.summary_note = QLabel(
            "Summary of implemented checks only — "
            "not a complete hardware-health certification."
        )
        self.summary_note.setWordWrap(True)
        self.summary_note.setStyleSheet(
            "color: #687b70; font-size: 11px;"
        )
        layout.addWidget(self.summary_note)


        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(1, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        self.refresh_button.clicked.connect(self.refresh)
        self.refresh()

    def clear_results(self):
        """Clear displayed assessments while retaining diagnostic controls."""
        if not hasattr(self, "latest_findings"):
            return

        cleared = []
        for finding in self.latest_findings:
            item = dict(finding)
            item["status"] = "UNKNOWN"
            item["summary"] = "NOT CHECKED — Run this check to view results."
            item["recommendation"] = "No recommendation until checked."
            cleared.append(item)

        self.latest_findings = cleared
        self.check_timestamps = {}
        self.last_check_time = None
        self.last_check_id = None

        for number in self.summary_cards.values():
            number.setText("0")

        for check_id, old_card in list(self.finding_cards.items()):
            index = self.grid.indexOf(old_card)
            if index < 0:
                continue

            row, column, row_span, column_span = (
                self.grid.getItemPosition(index)
            )

            finding = next(
                (
                    item for item in cleared
                    if finding_check_id(item) == check_id
                ),
                None,
            )
            if finding is None:
                continue

            new_card = create_finding_card(
                finding,
                on_run=lambda checked=False, cid=check_id:
                    self.rerun_card(cid),
                checked_at=None,
            )

            self.grid.removeWidget(old_card)
            old_card.hide()
            old_card.deleteLater()
            self.grid.addWidget(
                new_card, row, column, row_span, column_span
            )
            self.finding_cards[check_id] = new_card

    def run_individual_check(self, check_id):
        """Execute one read-only assessment and store its result."""

        data = collect()
        finding = run_check(check_id, data)

        updated = False

        for index, existing in enumerate(self.latest_findings):
            if finding_check_id(existing) == check_id:
                self.latest_findings[index] = finding
                updated = True
                break

        if not updated:
            raise ValueError(
                f"No existing diagnostic card for {check_id}"
            )

        self.latest_hardware_data = data

        self.last_check_time = datetime.now().astimezone()
        self.last_check_id = check_id
        self.check_timestamps[check_id] = self.last_check_time

        summary = summarize_findings(self.latest_findings)
        counts = summary["counts"]

        for status, number in self.summary_cards.items():
            number.setText(str(counts.get(status, 0)))

        return finding

    def rerun_card(self, check_id):
        """Refresh one finding card without rebuilding the page."""

        old_card = self.finding_cards.get(check_id)
        if old_card is None:
            raise ValueError(
                f"No visible diagnostic card for {check_id}"
            )

        try:
            finding = self.run_individual_check(check_id)
        except Exception:
            QMessageBox.warning(
                self,
                "Diagnostic could not complete",
                "The selected hardware check encountered "
                "an unexpected error.\\n\\n"
                "The previous result and timestamp have "
                "been preserved. Please retry the check.",
            )
            return

        index = self.grid.indexOf(old_card)
        if index < 0:
            raise ValueError(
                f"Diagnostic card is missing from grid: {check_id}"
            )

        row, column, row_span, column_span = (
            self.grid.getItemPosition(index)
        )

        new_card = create_finding_card(
            finding,
            on_run=lambda checked=False, cid=check_id:
                self.rerun_card(cid),
            checked_at=self.check_timestamps.get(check_id),
        )

        self.grid.removeWidget(old_card)
        old_card.hide()
        old_card.deleteLater()

        self.grid.addWidget(
            new_card, row, column, row_span, column_span
        )

        self.finding_cards[check_id] = new_card

    def refresh(self):
        try:
            data = collect()
            assessment = assess(data)
        except Exception:
            QMessageBox.warning(
                self,
                "Full hardware check could not complete",
                "Hardware information could not be collected "
                "or assessed.\\n\\n"
                "Existing diagnostic results and timestamps "
                "have been preserved. Please retry.",
            )
            return

        completed_at = datetime.now().astimezone()
        new_timestamps = {
            finding_check_id(finding): completed_at
            for finding in assessment.get("findings", [])
            if finding_check_id(finding) is not None
        }

        summary = assessment.get("summary", {})
        counts = summary.get("counts", {})

        staging = QWidget()
        staging_grid = QGridLayout(staging)
        staging_grid.setSpacing(12)
        staging_grid.setColumnStretch(1, 1)
        new_cards = {}

        try:
            self._populate_hardware_grid(
                staging_grid,
                new_cards,
                new_timestamps,
                data,
                assessment,
            )
        except Exception:
            staging.deleteLater()
            QMessageBox.warning(
                self,
                "Full hardware check could not complete",
                "The diagnostic interface could not be rebuilt.\\n\\n"
                "Existing results and timestamps have been preserved. "
                "Please retry.",
            )
            return

        old_widgets = []
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                old_widgets.append(widget)

        staged_widgets = []

        while staging_grid.count():
            row, column, row_span, column_span = (
                staging_grid.getItemPosition(0)
            )
            item = staging_grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                staged_widgets.append((
                    widget, row, column, row_span, column_span
                ))

        for widget, row, column, row_span, column_span in staged_widgets:
            self.grid.addWidget(
                widget, row, column, row_span, column_span
            )

        for widget in old_widgets:
            widget.hide()
            widget.deleteLater()

        self.finding_cards = new_cards
        self.check_timestamps = new_timestamps
        self.latest_hardware_data = data
        self.latest_findings = list(
            assessment.get("findings", [])
        )

        for status, number in self.summary_cards.items():
            number.setText(str(counts.get(status, 0)))

        staging.deleteLater()

    def _populate_hardware_grid(
        self, target_grid, new_cards, new_timestamps,
        data, assessment,
    ):
        cpu = data["cpu"]
        memory = data["memory"]
        firmware = data["firmware"]
        temperature = data.get("temperature", {})
        fan = data.get("fan", {})
        power = data.get("power", {})

        rows = [
            ("SYSTEM", ""),
            ("Manufacturer", firmware.get("manufacturer")),
            ("Model", firmware.get("product")),
            ("Motherboard", firmware.get("board")),
            ("PROCESSOR", ""),
            ("CPU", cpu.get("model")),
            ("Architecture", cpu.get("architecture")),
            ("Logical processors", cpu.get("logical_processors")),
            ("MEMORY", ""),
            ("Total RAM", gib(memory.get("total"))),
            ("Available RAM", gib(memory.get("available"))),
            ("Swap capacity", gib(memory.get("swap_total"))),
            ("FIRMWARE", ""),
            ("BIOS vendor", firmware.get("bios_vendor")),
            ("BIOS version", firmware.get("bios_version")),
            ("BIOS date", firmware.get("bios_date")),
        ]

        rows.append(("CPU TEMPERATURE", ""))

        if temperature.get("status") == "AVAILABLE":
            package = temperature.get("package_c")

            rows.append((
                "CPU package",
                f"{package:.1f} °C"
                if isinstance(package, (int, float))
                else "UNKNOWN"
            ))

            for core in temperature.get("cores_c", []):
                value = core.get("temperature_c")
                rows.append((
                    core.get("label", "CPU core"),
                    f"{value:.1f} °C"
                    if isinstance(value, (int, float))
                    else "UNKNOWN"
                ))
        else:
            rows.append(("Sensor status", "UNKNOWN"))

        rows.append(("COOLING FAN", ""))

        fans = fan.get("fans", [])

        if fans:
            for index, item in enumerate(fans, start=1):
                rpm = item.get("rpm")
                rows.append((
                    f"Fan {index} ({item.get('source') or 'UNKNOWN'})",
                    f"{rpm:,} RPM"
                    if isinstance(rpm, int)
                    else "UNKNOWN"
                ))
        else:
            rows.append(("Fan speed", "UNKNOWN"))

        rows.append(("BATTERY & POWER", ""))

        supplies = power.get("supplies", [])

        adapters = [
            item for item in supplies
            if item.get("type") == "Mains"
        ]

        if adapters:
            for adapter in adapters:
                online = adapter.get("online")
                state = (
                    "Connected" if online == "1"
                    else "Disconnected" if online == "0"
                    else "UNKNOWN"
                )
                rows.append((
                    f"AC adapter ({adapter.get('name', 'AC')})",
                    state
                ))
        else:
            rows.append(("AC adapter", "UNKNOWN"))

        batteries = [
            item for item in supplies
            if item.get("type") == "Battery"
        ]

        if not batteries:
            rows.append(("Battery", "NOT DETECTED"))

        for battery in batteries:
            name = battery.get("name", "Battery")
            health = battery.get("health_percent")
            charge = battery.get("capacity")

            rows.append((
                f"{name} status",
                battery.get("status") or "UNKNOWN"
            ))

            rows.append((
                f"{name} charge",
                f"{charge}%" if charge is not None else "UNKNOWN"
            ))

            rows.append((
                f"{name} capacity health",
                f"{health:.1f}% of design capacity"
                if isinstance(health, (int, float))
                else "UNKNOWN"
            ))

        rows.append((
            "Battery health meaning",
            "Full-charge capacity compared with original design "
            "capacity; not the current charge level."
        ))

        rows.append(("HARDWARE HEALTH FINDINGS", ""))

        for finding in assessment.get("findings", []):
            rows.append(("__FINDING_CARD__", finding))

        rows.append((
            "Assessment scope",
            "Advisory findings based on available hardware "
            "measurements. Not a certified hardware safety test."
        ))

        for row, (label, value) in enumerate(rows):

            if label == "__FINDING_CARD__":
                check_id = finding_check_id(value)

                if check_id is not None:
                    card = create_finding_card(
                        value,
                        on_run=lambda checked=False, cid=check_id:
                            self.rerun_card(cid),
                        checked_at=new_timestamps.get(check_id),
                    )
                    new_cards[check_id] = card
                else:
                    card = create_finding_card(value)

                target_grid.addWidget(card, row, 0, 1, 2)
                continue

            if not value and label in (
                "SYSTEM", "PROCESSOR", "MEMORY", "FIRMWARE",
                "CPU TEMPERATURE", "COOLING FAN",
                "BATTERY & POWER",
                "HARDWARE HEALTH FINDINGS"
            ):
                title = QLabel(label)
                title.setStyleSheet(
                    "color: #176747; font-weight: bold; "
                    "padding-top: 12px;"
                )
                target_grid.addWidget(title, row, 0, 1, 2)
                continue

            name = QLabel(label)
            name.setStyleSheet("color: #5b6e64;")
            value_label = QLabel(display(value))
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )
            value_label.setStyleSheet(
                "color: #193e30; font-weight: bold;"
            )

            target_grid.addWidget(name, row, 0)
            target_grid.addWidget(value_label, row, 1)

        target_grid.setRowStretch(len(rows), 1)
