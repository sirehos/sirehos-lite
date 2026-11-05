"""Read-only storage discovery interface for Sireh Doctor."""

from datetime import datetime
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sireh_doctor.gui.storage_smart_worker import SmartWorker
from sireh_doctor.diagnostics.storage_pci_names import (
    resolve_pci_name,
)
from sireh_doctor.diagnostics.storage_inventory import (
    collect_storage_inventory,
)


def display(value):
    """Display missing measurements without inventing values."""
    if value is None or value == "":
        return "UNKNOWN"
    return str(value)


def capacity(value):
    """Convert a byte count to decimal GB."""
    if isinstance(value, int) and not isinstance(value, bool):
        if value >= 0:
            return f"{value / 1_000_000_000:.2f} GB"
    return "UNKNOWN"


def information_card(title, rows):
    """Create a selectable, read-only storage information card."""
    card = QFrame()
    card.setObjectName("storageInformationCard")
    card.setStyleSheet("""
        QFrame#storageInformationCard {
            background: white;
            border: 1px solid #dce7df;
            border-radius: 10px;
        }
    """)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(17, 15, 17, 15)
    layout.setSpacing(10)

    heading = QLabel(title)
    heading.setWordWrap(True)
    heading.setStyleSheet(
        "color: #176747; font-size: 15px; font-weight: bold;"
    )
    layout.addWidget(heading)

    details = QGridLayout()
    details.setSpacing(9)
    details.setColumnStretch(1, 1)

    for index, (name, value) in enumerate(rows):
        label = QLabel(name)
        label.setStyleSheet("color: #65776c; font-size: 12px;")

        reading = QLabel(display(value))
        reading.setWordWrap(True)
        reading.setTextInteractionFlags(Qt.TextSelectableByMouse)
        reading.setStyleSheet(
            "color: #193e30; font-size: 12px; font-weight: bold;"
        )

        details.addWidget(label, index, 0)
        details.addWidget(reading, index, 1)

    layout.addLayout(details)
    return card


class StoragePage(QWidget):
    """Display discovered disks and controller metadata."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(12)

        heading = QLabel("Storage Doctor")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        description = QLabel(
            "SD-03  |  Read-only storage discovery"
        )
        description.setObjectName("description")
        layout.addWidget(description)

        scope = QLabel(
            "Inspecting storage visible to the running Linux system. "
            "Controller discovery does not establish disk health."
        )
        scope.setWordWrap(True)
        scope.setStyleSheet("color: #536b60;")
        layout.addWidget(scope)

        self.refresh_button = QPushButton("Scan Storage")
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
        layout.addWidget(
            self.refresh_button, alignment=Qt.AlignLeft
        )

        self.status_label = QLabel("Storage scan not yet completed.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #536b60; font-size: 12px;"
        )
        layout.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setAlignment(Qt.AlignTop)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        self.smart_workers = {}
        self.smart_results = {}
        self.smart_labels = {}
        self.smart_buttons = {}
        self.visible_devices = set()
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self):
        """Refresh read-only inventory without running SMART."""
        if any(
            worker.isRunning()
            for worker in self.smart_workers.values()
        ):
            return

        try:
            inventory = collect_storage_inventory()
        except Exception:
            self.status_label.setText(
                "Storage discovery encountered an unexpected error."
            )
            return

        devices = inventory.get("devices", [])

        if not isinstance(devices, list):
            devices = []

        cards = []

        # Rebuild widget references for the current inventory.
        # Completed results remain cached for unchanged devices.
        self.smart_labels.clear()
        self.smart_buttons.clear()
        self.visible_devices.clear()

        for device in devices:
            if not isinstance(device, dict):
                continue

            name = display(device.get("name"))
            controller = device.get("controller") or {}
            pci = device.get("pci") or {}
            classification = device.get("classification") or {}

            pci_address = (
                pci.get("pci_address")
                or controller.get("pci_address")
            )
            identity = resolve_pci_name(pci_address)

            description = identity.get("description")
            revision = None
            if isinstance(description, str):
                match = re.search(
                    r"\(rev ([0-9a-fA-F]+)\)$", description
                )
                if match:
                    revision = match.group(1)


            disk_card = information_card(
                f"Physical Disk — {name}",
                [
                    ("Device", device.get("path")),
                    ("Model", device.get("model")),
                    ("Capacity", capacity(device.get("size_bytes"))),
                    ("Transport", device.get("transport")),
                    ("Removable", device.get("removable")),
                    ("Rotational", device.get("rotational")),
                    ("SMART health", "NOT YET ASSESSED"),
                ],
            )

            device_path = device.get("path")
            if isinstance(device_path, str) and device_path:
                health_button = QPushButton("Check Disk Health")
                health_button.setCursor(Qt.PointingHandCursor)
                health_button.clicked.connect(
                    lambda checked=False, path=device_path:
                    self.check_disk_health(path)
                )
                disk_card.layout().addWidget(health_button)
                self.smart_buttons[device_path] = health_button

                health_label = QLabel("SMART: NOT YET ASSESSED")
                health_label.setWordWrap(True)
                health_label.setTextInteractionFlags(
                    Qt.TextSelectableByMouse
                )
                disk_card.layout().addWidget(health_label)
                self.smart_labels[device_path] = health_label
                self.visible_devices.add(device_path)

                cached = self.smart_results.get(device_path)
                if cached is not None:
                    self._display_smart_result(
                        device_path, cached
                    )

            cards.append(disk_card)

            cards.append(information_card(
                f"Storage Controller — {name}",
                [
                    ("Controller name", description),
                    ("Controller type",
                     classification.get("controller_type")),
                    ("PCI address", pci_address),
                    ("PCI class", pci.get("class_code")),
                    ("PCI revision", revision),
                    ("Vendor ID", pci.get("vendor_id")),
                    ("Device ID", pci.get("device_id")),
                    ("Subsystem", identity.get("subsystem")),
                    ("Linux driver", pci.get("driver")
                     or identity.get("kernel_driver")),
                    ("Kernel modules",
                     identity.get("kernel_modules")),
                    ("Physical disk visibility",
                     classification.get("physical_disk_visibility")),
                ],
            ))

        if not cards:
            cards.append(information_card(
                "Storage Discovery",
                [
                    ("Status", inventory.get("status")),
                    ("Details", inventory.get("error")
                     or "No physical disks were identified."),
                ],
            ))

        old_widgets = []

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                old_widgets.append(widget)

        for index, card in enumerate(cards):
            self.grid.addWidget(
                card, index // 2, index % 2
            )

        for widget in old_widgets:
            widget.hide()
            widget.deleteLater()

        completed = datetime.now().astimezone()
        self.status_label.setText(
            f"Discovery: {display(inventory.get('status'))}  |  "
            f"Disks: {len(devices)}  |  "
            f"Last scanned: {completed:%d %b %Y, %H:%M:%S %Z}"
        )

    def check_disk_health(self, device_path):
        """Start a non-privileged, read-only SMART query."""
        worker = self.smart_workers.get(device_path)
        if worker is not None and worker.isRunning():
            return

        button = self.smart_buttons.get(device_path)
        label = self.smart_labels.get(device_path)

        if button is not None:
            button.setEnabled(False)
        if label is not None:
            label.setText("SMART: CHECKING...")

        worker = SmartWorker(device_path, self)
        self.smart_workers[device_path] = worker
        self.refresh_button.setEnabled(False)

        worker.completed.connect(self.on_smart_completed)
        worker.finished.connect(
            lambda path=device_path, task=worker:
            self.on_smart_finished(path, task)
        )
        worker.start()

    def on_smart_completed(self, result):
        """Display SMART evidence without fabricating health."""
        if not isinstance(result, dict):
            return

        path = result.get("device")
        collection = result.get("collection") or {}
        assessment = result.get("assessment") or {}

        self.smart_results[path] = result
        self._display_smart_result(path, result)

    def _display_smart_result(self, path, result):
        """Render a readable, conservative SMART report."""
        collection = result.get("collection") or {}
        assessment = result.get("assessment") or {}

        label = self.smart_labels.get(path)
        if label is None:
            return

        status = assessment.get("status", "UNKNOWN")
        summary = assessment.get("summary") or ""
        recommendation = assessment.get("recommendation") or ""
        metrics = assessment.get("metrics") or {}

        lines = ["SMART: " + str(status)]

        collection_status = collection.get("status")
        collection_error = collection.get("error")

        if collection_status == "PERMISSION_REQUIRED":
            lines.append("Administrator permission required")
        elif collection_error:
            lines.append("Collection: " + str(collection_error))

        if summary:
            lines.append(str(summary))

        if recommendation:
            lines.append(str(recommendation))

        metric_names = {
            "overall_smart_passed": "Overall SMART passed",
            "temperature_c": "Temperature C",
            "power_on_hours": "Power On Hours",
            "nvme_critical_warning": "NVMe critical warning",
            "nvme_media_errors": "NVMe media errors",
            "nvme_percentage_used": "NVMe endurance used (%)",
            "nvme_available_spare_percent": "NVMe available spare (%)",
            "nvme_spare_threshold_percent": "NVMe spare threshold (%)",
            "ata_reallocated_sectors": "Reallocated sectors",
            "ata_pending_sectors": "Pending sectors",
            "ata_uncorrectable_sectors": "Uncorrectable sectors",
        }

        if isinstance(metrics, dict) and metrics:
            lines.append("Measurements:")

            for key, value in sorted(metrics.items()):
                name = metric_names.get(
                    key, key.replace("_", " ").title()
                )
                lines.append(name + ": " + str(value))

        if status in ("PASS", "WARN", "FAIL"):
            lines.append(
                "SMART is not a guarantee against future disk failure."
            )

        label.setText("\n".join(lines))

    def on_smart_finished(self, device_path, worker):
        """Release the worker after its thread finishes."""
        button = self.smart_buttons.get(device_path)
        if button is not None:
            button.setEnabled(True)

        if self.smart_workers.get(device_path) is worker:
            self.smart_workers.pop(device_path, None)

        if not any(
            task.isRunning()
            for task in self.smart_workers.values()
        ):
            self.refresh_button.setEnabled(True)

        worker.deleteLater()
