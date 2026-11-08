"""Security Doctor graphical interface for SirehOS Lite Benih 1.0."""

from datetime import datetime

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QPlainTextEdit,
)

from sireh_doctor.diagnostics.security_doctor import CHECKS, run_check


DESCRIPTIONS = {
    "access_control": "AppArmor and SELinux access-control evidence",
    "firewall": "Local firewall configuration and listening sockets",
    "privileged_accounts": "UID 0 accounts, administrative groups and sudo evidence",
    "file_permissions": "Selected sensitive Linux file and directory permissions",
    "remote_access": "SSH configuration and legacy remote-access listeners",
    "boot_encryption": "Firmware boot mode, Secure Boot and encryption metadata",
    "patch_evidence": "Local OS, kernel and package-index evidence",
    "industrial_media": "Attached USB devices and selected local service ports",
}

FUTURE_FEATURES = (
    "OT Asset Security Profiler",
    "Offline Vulnerability Intelligence",
    "Suspicious Persistence Investigator",
    "Security Evidence & Compliance Report",
)

STATUS_COLORS = {
    "PASS": "#176747",
    "WARN": "#956000",
    "FAIL": "#a92e2e",
    "INFO": "#245f88",
    "UNKNOWN": "#64776c",
}


class SecurityWorker(QObject):
    completed = pyqtSignal(str, dict, str)
    finished = pyqtSignal()

    def __init__(self, check_ids):
        super().__init__()
        self.check_ids = list(check_ids)

    def run(self):
        try:
            for check_id in self.check_ids:
                try:
                    outcome = run_check(check_id)
                except Exception:
                    outcome = {
                        "status": "UNKNOWN",
                        "summary": "Security check could not complete.",
                        "details": "An unexpected diagnostic error occurred.",
                    }

                timestamp = datetime.now().astimezone().strftime(
                    "%d %b %Y, %H:%M:%S %Z"
                )
                self.completed.emit(check_id, outcome, timestamp)
        finally:
            self.finished.emit()


class SecurityPage(QWidget):
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

        heading = QLabel("Security Doctor")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        layout.addWidget(heading)

        subtitle = QLabel(
            "SD-06 | Local security evidence inspection | Read-only"
        )
        subtitle.setStyleSheet("color: #64776c;")
        layout.addWidget(subtitle)

        scope = QLabel(
            "Inspects the running Linux session only. "
            "Mounted offline operating systems are not automatically "
            "assessed. No network scanning, authentication attempts, "
            "repairs or configuration changes are performed."
        )
        scope.setWordWrap(True)
        scope.setStyleSheet("color: #536b60;")
        layout.addWidget(scope)

        controls = QHBoxLayout()

        self.run_all_button = QPushButton("Run All Checks")
        self.run_all_button.clicked.connect(
            lambda: self.start_checks(list(CHECKS))
        )
        controls.addWidget(self.run_all_button)

        self.clear_button = QPushButton("Clear All Results")
        self.clear_button.clicked.connect(self.clear_results)
        controls.addWidget(self.clear_button)

        self.progress = QLabel("Ready — no checks performed")
        controls.addWidget(self.progress, 1)
        layout.addLayout(controls)

        grid = QGridLayout()
        grid.setSpacing(12)

        for index, (check_id, title) in enumerate(CHECKS.items()):
            card = QFrame()
            card.setObjectName("securityCard")
            card.setStyleSheet(
                "QFrame#securityCard { background: white;"
                "border: 1px solid #dce7df; border-radius: 9px; }"
                "QLabel { border: none; }"
            )

            column = QVBoxLayout(card)

            name = QLabel(title)
            name.setWordWrap(True)
            name.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #153d30;"
            )
            column.addWidget(name)

            description = QLabel(DESCRIPTIONS[check_id])
            description.setWordWrap(True)
            description.setStyleSheet("color: #64776c;")
            column.addWidget(description)

            status = QLabel("NOT CHECKED")
            status.setStyleSheet(
                "font-weight: bold; color: #64776c;"
            )
            column.addWidget(status)

            timestamp = QLabel("Last checked: Never")
            timestamp.setStyleSheet(
                "font-size: 11px; color: #64776c;"
            )
            column.addWidget(timestamp)

            details = QPlainTextEdit()
            details.setReadOnly(True)
            details.setPlainText(
                "Run this check to inspect local security evidence."
            )
            details.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            details.setFixedHeight(220)
            details.setStyleSheet(
                "QPlainTextEdit { background: #f8faf8;"
                "border: 1px solid #e2eae3;"
                "border-radius: 5px;"
                "color: #253b31;"
                "padding: 5px; }"
            )
            column.addWidget(details)

            button = QPushButton("Run Security Check")
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

        assessment_heading = QLabel("Security Assessment")
        assessment_heading.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #153d30;"
        )
        assessment_layout.addWidget(assessment_heading)

        self.assessment_status = QLabel(
            "UNKNOWN — No security checks performed"
        )
        assessment_layout.addWidget(self.assessment_status)

        self.assessment_details = QLabel(
            "No security conclusion can be drawn before collecting "
            "evidence. INFO does not mean secure or compliant."
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

        future_heading = QLabel(
            "Coming in Tunas 1.1 — Advanced Security Investigation"
        )
        future_heading.setWordWrap(True)
        future_layout.addWidget(future_heading)

        for feature in FUTURE_FEATURES:
            button = QPushButton(feature + " — Coming Soon")
            button.setEnabled(False)
            future_layout.addWidget(button)

        layout.addWidget(future)
        layout.addStretch()

    def clear_results(self):
        if self.thread is not None:
            return

        self.results.clear()
        self.checked_at.clear()

        for status, timestamp, details in self.cards.values():
            status.setText("NOT CHECKED")
            status.setStyleSheet(
                "font-weight: bold; color: #64776c;"
            )
            timestamp.setText("Last checked: Never")
            details.setPlainText(
                "Run this check to inspect local security evidence."
            )

        self.assessment_status.setText(
            "UNKNOWN — No security checks performed"
        )
        self.assessment_details.setText(
            "No security conclusion can be drawn before collecting "
            "evidence. INFO does not mean secure or compliant."
        )
        self.assessment_time.setText("Last updated: Never")
        self.progress.setText("Ready — no checks performed")

    def start_checks(self, check_ids):
        if self.thread is not None:
            return

        check_ids = list(check_ids)

        if not check_ids or any(key not in CHECKS for key in check_ids):
            return

        self.progress.setText(
            "Inspecting {} security area(s)...".format(len(check_ids))
        )
        self.run_all_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        for button in self.buttons.values():
            button.setEnabled(False)

        thread = QThread(self)
        worker = SecurityWorker(check_ids)
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

        status_label.setText(status)
        status_label.setStyleSheet(
            "font-weight: bold; color: {};".format(
                STATUS_COLORS.get(status, "#64776c")
            )
        )
        time_label.setText("Last checked: " + timestamp)

        summary = outcome.get("summary", "No summary available.")
        evidence = outcome.get("details", "")
        details_label.setPlainText(
            summary + ("\n\n" + evidence if evidence else "")
        )

        self.update_assessment()
        self.progress.setText(
            "Ready — {} of {} checks completed".format(
                len(self.results), len(CHECKS)
            )
        )

    def update_assessment(self):
        completed = len(self.results)
        total = len(CHECKS)

        statuses = [
            item.get("status", "UNKNOWN")
            for item in self.results.values()
        ]

        if "FAIL" in statuses:
            status = "FAIL"
        elif "WARN" in statuses:
            status = "WARN"
        elif completed < total or "UNKNOWN" in statuses:
            status = "UNKNOWN"
        else:
            status = "INFO"

        execution = (
            "COMPLETE" if completed == total else "PARTIAL"
        )
        self.assessment_status.setText(
            "{} — {} | Security assessment: {}".format(
                execution,
                "{} of {} checks executed".format(completed, total),
                status,
            )
        )

        if status == "FAIL":
            message = (
                "One or more checks reported a significant finding. "
                "Review the evidence before taking any action."
            )
        elif status == "WARN":
            message = (
                "Potential security concerns were observed. "
                "Review each finding; this is not proof of compromise."
            )
        elif status == "UNKNOWN":
            message = (
                "Security evidence is incomplete or unavailable. "
                "Unchecked areas and inaccessible configuration "
                "must not be treated as secure."
            )
        else:
            message = (
                "Local security metadata was collected. "
                "INFO does not establish that this system is secure, "
                "patched or compliant."
            )

        self.assessment_details.setText(message)
        self.assessment_time.setText(
            "Last updated: "
            + datetime.now().astimezone().strftime(
                "%d %b %Y, %H:%M:%S %Z"
            )
        )

    def finish_checks(self):
        self.thread = None
        self.worker = None

        self.run_all_button.setEnabled(True)
        self.clear_button.setEnabled(True)

        for button in self.buttons.values():
            button.setEnabled(True)

        self.progress.setText(
            "Ready — {} of {} checks completed".format(
                len(self.results), len(CHECKS)
            )
        )
