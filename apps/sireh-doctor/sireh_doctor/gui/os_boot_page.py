"""SD-04: OS & Boot Doctor interactive GUI."""
from datetime import datetime

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from sireh_doctor.diagnostics.os_boot import CHECKS, run_check


class CheckWorker(QObject):
    completed = pyqtSignal(str, dict, str)
    finished = pyqtSignal()

    def __init__(self, check_ids):
        super().__init__()
        self.check_ids = list(check_ids)

    def run(self):
        try:
            for check_id in self.check_ids:
                outcome = run_check(check_id)
                checked_at = datetime.now().astimezone().strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )
                self.completed.emit(check_id, outcome, checked_at)
        finally:
            self.finished.emit()


class OSBootPage(QWidget):
    def __init__(self):
        super().__init__()
        self.results = {}
        self.checked_at = {}
        self.cards = {}
        self.buttons = {}
        self.thread = None
        self.worker = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(13)

        title = QLabel("OS & Boot Doctor")
        title.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "SD-04 | Operating system and boot diagnostics | Read-only"
        )
        subtitle.setStyleSheet("color: #64776c;")
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        self.run_all_button = QPushButton("Run All Boot Checks")
        self.run_all_button.setObjectName("runAllBootChecks")
        self.run_all_button.clicked.connect(
            lambda: self.start_checks(list(CHECKS))
        )
        controls.addWidget(self.run_all_button)

        self.progress = QLabel("Ready — no checks performed")
        controls.addWidget(self.progress, 1)
        layout.addLayout(controls)

        grid = QGridLayout()
        grid.setSpacing(12)

        descriptions = {
            "os": "Running OS and accessible installed systems",
            "firmware": "UEFI / BIOS and Secure Boot state",
            "boot_partitions": "EFI and BIOS boot partition evidence",
            "bootloaders": "EFI entries and accessible bootloader files",
            "boot_config": "Accessible OS boot configuration files",
            "diagnose": "Potential boot blockers and limitations",
        }

        for index, (check_id, (button_label, _)) in enumerate(
            CHECKS.items()
        ):
            card = QFrame()
            card.setObjectName("bootCard")
            card.setStyleSheet(
                "QFrame#bootCard { background: white;"
                "border: 1px solid #dce7df; border-radius: 9px; }"
                "QLabel { border: none; }"
            )
            column = QVBoxLayout(card)

            heading = QLabel(
                "F{:02d} — {}".format(index + 1, button_label)
            )
            heading.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #153d30;"
            )
            column.addWidget(heading)

            description = QLabel(descriptions[check_id])
            description.setWordWrap(True)
            description.setStyleSheet("color: #64776c;")
            column.addWidget(description)

            status = QLabel("NOT CHECKED")
            status.setStyleSheet("font-weight: bold; color: #64776c;")
            column.addWidget(status)

            timestamp = QLabel("Last checked: Never")
            timestamp.setStyleSheet(
                "font-size: 11px; color: #64776c;"
            )
            column.addWidget(timestamp)

            details = QLabel("Run this check to view results.")
            details.setWordWrap(True)
            details.setTextInteractionFlags(
                details.textInteractionFlags()
                | Qt.TextSelectableByMouse
            )
            column.addWidget(details)

            button = QPushButton(button_label)
            button.clicked.connect(
                lambda checked=False, key=check_id:
                self.start_checks([key])
            )
            column.addWidget(button)

            self.cards[check_id] = (status, timestamp, details)
            self.buttons[check_id] = button
            grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(grid)

        assessment = QFrame()
        assessment.setStyleSheet(
            "background: white; border: 1px solid #dce7df;"
            "border-radius: 9px;"
        )
        assessment_layout = QVBoxLayout(assessment)
        assessment_layout.addWidget(QLabel("F07 — Boot Assessment"))

        self.assessment_status = QLabel(
            "UNKNOWN — No boot checks performed"
        )
        self.assessment_status.setWordWrap(True)
        assessment_layout.addWidget(self.assessment_status)

        self.assessment_details = QLabel(
            "Assessment uses only completed checks. "
            "Unverified conditions remain UNKNOWN."
        )
        self.assessment_details.setWordWrap(True)
        assessment_layout.addWidget(self.assessment_details)

        self.assessment_time = QLabel("Last updated: Never")
        assessment_layout.addWidget(self.assessment_time)
        layout.addWidget(assessment)

        future = QFrame()
        future.setStyleSheet(
            "background: #eef5ef; border-radius: 9px;"
        )
        future_layout = QVBoxLayout(future)
        future_layout.addWidget(
            QLabel("Coming in Tunas 1.1 — Advanced Boot Diagnostics")
        )
        for item in (
            "Advanced Windows BCD Analysis",
            "Advanced Linux Boot Dependency Analysis",
            "Secure Boot Signature Verification",
            "Deep Boot Failure Root-Cause Analysis",
        ):
            button = QPushButton(item + " — Coming Soon")
            button.setEnabled(False)
            future_layout.addWidget(button)
        layout.addWidget(future)
        layout.addStretch()

    def start_checks(self, check_ids):
        if self.thread is not None:
            return

        self.progress.setText(
            "Running {} check(s)...".format(len(check_ids))
        )
        self.run_all_button.setEnabled(False)
        for button in self.buttons.values():
            button.setEnabled(False)

        thread = QThread(self)
        worker = CheckWorker(check_ids)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.completed.connect(self.receive_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.finish_checks)
        thread.finished.connect(thread.deleteLater)

        self.thread = thread
        self.worker = worker
        thread.start()

    def receive_result(self, check_id, outcome, timestamp):
        self.results[check_id] = outcome
        self.checked_at[check_id] = timestamp

        status_label, time_label, details_label = self.cards[check_id]
        status = outcome.get("status", "UNKNOWN")
        status_label.setText(
            "{} — {}".format(status, outcome.get("summary", ""))
        )
        colors = {
            "PASS": "#23764b",
            "WARN": "#a46a12",
            "FAIL": "#b23838",
            "UNKNOWN": "#64776c",
        }
        status_label.setStyleSheet(
            "font-weight: bold; color: {};".format(
                colors.get(status, "#64776c")
            )
        )
        time_label.setText("Last checked: " + timestamp)
        details_label.setText(
            "\n".join(str(x) for x in outcome.get("details", []))
            or "No additional details"
        )
        self.update_assessment()

    def update_assessment(self):
        total = len(CHECKS)
        done = len(self.results)
        statuses = [
            item.get("status", "UNKNOWN")
            for item in self.results.values()
        ]

        if "FAIL" in statuses:
            status = "FAIL"
        elif "WARN" in statuses:
            status = "WARN"
        elif done < total or "UNKNOWN" in statuses:
            status = "UNKNOWN"
        else:
            status = "PASS"

        self.assessment_status.setText(
            "{} — {}/{} checks completed".format(
                status, done, total
            )
        )
        self.assessment_details.setText(
            "Assessment reflects collected evidence only; "
            "it does not certify that an installed OS will boot. "
            "Individual results may have different check times."
        )
        self.assessment_time.setText(
            "Last updated: "
            + datetime.now().astimezone().strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
        )

    def finish_checks(self):
        self.thread = None
        self.worker = None
        self.run_all_button.setEnabled(True)
        for button in self.buttons.values():
            button.setEnabled(True)
        self.progress.setText(
            "Ready — {} of {} checks completed".format(
                len(self.results), len(CHECKS)
            )
        )
