"""Data Rescue graphical interface for Sireh Doctor Benih 1.0.

Read-only discovery interface. Recovery copying remains disabled.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sireh_doctor.diagnostics.data_rescue import discover_rescue_drives
from sireh_doctor.diagnostics.data_rescue_safety import (
    read_mountinfo,
    evaluate_rescue_source_by_identity,
)


class DataRescuePage(QWidget):
    """Beginner-friendly rescue discovery and safety overview."""

    def __init__(self):
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        self.layout_content = QVBoxLayout(content)
        self.layout_content.setSpacing(13)

        heading = QLabel("Data Rescue")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        self.layout_content.addWidget(heading)

        subtitle = QLabel(
            "SD-07 | Windows & Linux file rescue | Safety-first"
        )
        subtitle.setStyleSheet("color: #64776c;")
        self.layout_content.addWidget(subtitle)

        introduction = QLabel(
            "Can't boot into Windows or Linux? Need to recover "
            "important files? Sireh Doctor helps identify storage "
            "devices, inspect accessible filesystems and prepare "
            "safe recovery to a separate drive. The guided process "
            "prioritizes protecting your original data. Encrypted, "
            "damaged or unsafe filesystems may require additional steps."
        )
        introduction.setWordWrap(True)
        introduction.setStyleSheet(
            "color: #344f42; font-size: 13px;"
        )
        self.layout_content.addWidget(introduction)

        self.status = self._card(
            "Recovery safety status",
            "Discovery only. No drives will be mounted, repaired, "
            "unlocked or modified. Real-device file copying is "
            "not yet enabled."
        )
        self.layout_content.addWidget(self.status)

        controls = QHBoxLayout()

        self.refresh_button = QPushButton("Discover Drives")
        self.refresh_button.setStyleSheet(
            "QPushButton { background: #176747; color: white; "
            "border: none; border-radius: 6px; padding: 10px 16px; "
            "font-weight: bold; }"
            "QPushButton:hover { background: #215f45; }"
        )
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Clear Results")
        self.clear_button.setToolTip(
            "Clear displayed discovery results without changing any drive."
        )
        self.clear_button.clicked.connect(self.clear_results)
        controls.addWidget(self.clear_button)

        self.copy_button = QPushButton("Start Recovery")
        self.copy_button.setEnabled(False)
        self.copy_button.setToolTip(
            "Coming soon: recovery remains disabled until controlled safety testing "
            "and user confirmation are completed."
        )
        controls.addWidget(self.copy_button)
        controls.addStretch()

        self.layout_content.addLayout(controls)

        selection_title = QLabel("Choose a recovery source")
        selection_title.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #153d30;"
        )
        self.layout_content.addWidget(selection_title)

        self.source_selector = QComboBox()
        self.source_selector.addItem(
            "Discover drives to choose a partition", None
        )
        self.source_selector.setEnabled(False)
        self.source_selector.currentIndexChanged.connect(
            self.assess_selected_source
        )
        self.layout_content.addWidget(self.source_selector)

        self.source_assessment = QLabel(
            "No source selected. Recovery browsing is disabled."
        )
        self.source_assessment.setWordWrap(True)
        self.source_assessment.setStyleSheet(
            "background: white; border: 1px solid #dce7df; "
            "border-radius: 6px; padding: 12px; color: #344f42;"
        )
        self.layout_content.addWidget(self.source_assessment)

        section = QLabel("Detected storage devices")
        section.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #153d30;"
        )
        self.layout_content.addWidget(section)

        self.devices_container = QWidget()
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setContentsMargins(0, 0, 0, 0)
        self.devices_layout.setSpacing(9)
        self.layout_content.addWidget(self.devices_container)

        workflow = self._card(
            "Guided recovery workflow",
            "1. Discover drives and partitions\n"
            "2. Verify source read-only safety\n"
            "3. Browse accessible files and preview recovery size\n"
            "4. Select a separate physical destination drive\n"
            "5. Confirm, copy and verify recovered files\n\n"
            "Safety assessment is available now. File browsing, destination "
            "selection and copying await controlled safety testing."
        )
        self.layout_content.addWidget(workflow)

        future = self._card(
            "COMING SOON | Safety Testing Pending",
            "Available now: Windows/Linux drive discovery, filesystem "
            "identification, partition selection and source safety "
            "assessment.\n\n"
            "Disabled pending safety validation: file browsing, "
            "destination selection and Start Recovery.\n\n"
            "Future enhancements: evidence reports, resume support, "
            "advanced disk imaging and deleted-file investigation."
        )
        self.layout_content.addWidget(future)

        self.layout_content.addStretch()

        self._show_message(
            "Select Discover Drives to inspect local storage metadata."
        )

    @staticmethod
    def _card(title, body):
        card = QFrame()
        card.setObjectName("dataRescueCard")
        card.setStyleSheet(
            "QFrame#dataRescueCard { background: white; "
            "border: 1px solid #dce7df; border-radius: 10px; }"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 14, 17, 14)

        heading = QLabel(title)
        heading.setStyleSheet(
            "color: #176747; font-size: 15px; font-weight: bold;"
        )
        layout.addWidget(heading)

        description = QLabel(body)
        description.setWordWrap(True)
        description.setTextInteractionFlags(Qt.TextSelectableByMouse)
        description.setStyleSheet(
            "color: #344f42; font-size: 12px;"
        )
        layout.addWidget(description)

        return card

    def _clear_devices(self):
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_message(self, message):
        self.devices_layout.addWidget(
            self._card("Discovery", message)
        )

    def clear_results(self):
        """Clear displayed results without touching storage devices."""
        self.source_selector.blockSignals(True)
        self.source_selector.clear()
        self.source_selector.addItem(
            "Discover drives to choose a partition", None
        )
        self.source_selector.setEnabled(False)
        self.source_selector.blockSignals(False)
        self.source_assessment.setText(
            "No source selected. Recovery browsing is disabled."
        )
        self._clear_devices()
        self._show_message(
            "Results cleared. Select Discover Drives to inspect "
            "local storage metadata."
        )
        self.copy_button.setEnabled(False)

    def assess_selected_source(self, index):
        """Explain source safety; never authorize file access."""
        device = self.source_selector.itemData(index)

        if not isinstance(device, dict):
            self.source_assessment.setText(
                "Select a partition to assess its recovery safety."
            )
            return

        path = str(device.get("path") or "Unknown partition")

        if device.get("encrypted"):
            reason = "Encrypted filesystem. Unlocking is unsupported."
        elif device.get("filesystem_class") != "SUPPORTED":
            reason = "Unknown or unsupported filesystem."
        else:
            try:
                mounts = read_mountinfo()
                result = evaluate_rescue_source_by_identity(
                    device, mounts
                )
                reason = str(
                    result.get("reason")
                    or "Source safety could not be established."
                )
            except Exception:
                reason = "Source safety could not be established."

        self.source_assessment.setText(
            f"Selected source: {path}\n"
            f"Safety assessment: {reason}\n"
            "File browsing and recovery remain disabled."
        )

    def refresh(self):
        """Refresh local block-device metadata without mounting."""

        self._clear_devices()
        self.refresh_button.setEnabled(False)

        try:
            result = discover_rescue_drives()
        except Exception:
            self._show_message(
                "Drive discovery unavailable. No storage access authorized."
            )
            return
        finally:
            self.refresh_button.setEnabled(True)

        if not isinstance(result, dict):
            self._show_message(
                "Invalid drive discovery response."
            )
            return

        if result.get("status") != "AVAILABLE":
            self._show_message(
                "Drive discovery unavailable: "
                + str(result.get("error") or "Unknown error")
            )
            return

        devices = result.get("devices")

        if not isinstance(devices, list):
            self._show_message(
                "Invalid device inventory returned."
            )
            return

        if not all(isinstance(device, dict) for device in devices):
            self._show_message(
                "Invalid device records returned."
            )
            return

        if not devices:
            self._show_message(
                "No storage devices were returned by discovery."
            )
            return

        try:
            mounts = read_mountinfo()
        except Exception:
            mounts = []

        self.source_selector.blockSignals(True)
        self.source_selector.clear()
        self.source_selector.addItem("Select a partition...", None)

        for device in devices:
            if device.get("type") == "part":
                self.source_selector.addItem(
                    str(device.get("path") or "Unknown partition"),
                    dict(device),
                )

        self.source_selector.setEnabled(
            self.source_selector.count() > 1
        )
        self.source_selector.blockSignals(False)
        self.source_assessment.setText(
            "Select a partition to assess its recovery safety."
        )

        for device in devices:
            path = str(device.get("path") or "Unknown device")
            filesystem = str(
                device.get("filesystem") or "Unknown"
            )
            classification = str(
                device.get("filesystem_class") or "Unknown"
            )
            mountpoints = device.get("mountpoints") or []
            if isinstance(mountpoints, (list, tuple)):
                mounted = ", ".join(
                    str(item) for item in mountpoints if item
                ) or "Not mounted"
            else:
                mounted = str(mountpoints)

            reason = str(
                device.get("eligibility_reason")
                or "Further safety verification required"
            )

            device_type = device.get("type")
            filesystem_class = device.get("filesystem_class")
            identity = device.get("maj:min")

            if device_type == "disk":
                reason = (
                    "Physical disk. Select a partition for inspection."
                )
            elif device.get("encrypted"):
                reason = (
                    "Encrypted filesystem. Unlocking is not supported."
                )
            elif filesystem_class != "SUPPORTED":
                reason = (
                    "Filesystem unknown or unsupported. "
                    "Inspection is unavailable."
                )
            elif device_type == "part":
                if isinstance(mounts, list):
                    try:
                        assessment = evaluate_rescue_source_by_identity(
                            device, mounts
                        )
                        reason = str(
                            assessment.get("reason")
                            or "Source safety could not be verified"
                        )
                    except Exception:
                        reason = "Source safety could not be verified"
                else:
                    reason = "Mount information unavailable"

            details = (
                f"Filesystem: {filesystem}\n"
                f"Classification: {classification}\n"
                f"Mounted at: {mounted}\n"
                f"Recovery status: NOT AUTHORIZED\n"
                f"Reason: {reason}"
            )

            self.devices_layout.addWidget(
                self._card(path, details)
            )
