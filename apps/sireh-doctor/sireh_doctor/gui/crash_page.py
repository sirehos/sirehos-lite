"""Crash Detective graphical interface for Sireh Doctor."""
from datetime import datetime

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from sireh_doctor.diagnostics.crash_detective import CHECKS, run_check


class CrashWorker(QObject):
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
                        "summary": "Crash check could not complete.",
                        "details": "An unexpected diagnostic error occurred.",
                    }

                timestamp = datetime.now().astimezone().strftime(
                    "%d %b %Y, %H:%M:%S %Z"
                )
                self.completed.emit(check_id, outcome, timestamp)
        finally:
            self.finished.emit()


class CrashPage(QWidget):
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

        heading = QLabel("Crash Detective")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        layout.addWidget(heading)

        subtitle = QLabel(
            "SD-05 | Historical crash evidence investigation | Read-only"
        )
        subtitle.setStyleSheet("color: #64776c;")
        layout.addWidget(subtitle)

        scope = QLabel(
            "Investigates accessible crash evidence. "
            "The running Linux session and installed operating systems "
            "are not assumed to share the same crash history."
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

        descriptions = {
            "previous_boot": "Crash evidence from accessible previous Linux boot logs",
            "kernel": "Kernel panic, Oops, watchdog and hardware crash signatures",
            "services": "Service processes terminated by crash signals or core dumps",
            "applications": "Accessible application crash reports and core dump metadata",
            "windows": "Windows crash dumps on already-mounted Windows volumes",
        }

        actions = {
            "previous_boot": "Check Previous Boot",
            "kernel": "Check Kernel Logs",
            "services": "Check Service Crashes",
            "applications": "Check Application Crashes",
            "windows": "Check Windows Crashes",
        }

        grid = QGridLayout()
        grid.setSpacing(12)

        for index, (check_id, title) in enumerate(CHECKS.items()):
            card = QFrame()
            card.setObjectName("crashCard")
            card.setStyleSheet(
                "QFrame#crashCard { background: white;"
                "border: 1px solid #dce7df; border-radius: 9px; }"
                "QLabel { border: none; }"
            )
            column = QVBoxLayout(card)

            name = QLabel(title)
            name.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #153d30;"
            )
            column.addWidget(name)

            description = QLabel(descriptions[check_id])
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

            details = QLabel("Run this check to investigate crash evidence.")
            details.setWordWrap(True)
            details.setTextInteractionFlags(Qt.TextSelectableByMouse)
            column.addWidget(details)

            button = QPushButton(actions[check_id])
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

        assessment_heading = QLabel("Crash Assessment")
        assessment_heading.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #153d30;"
        )
        assessment_layout.addWidget(assessment_heading)

        self.assessment_status = QLabel(
            "UNKNOWN — No crash checks performed"
        )
        assessment_layout.addWidget(self.assessment_status)

        self.assessment_details = QLabel(
            "No conclusion can be drawn before examining crash evidence."
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
            QLabel("Coming in Tunas 1.1 — Advanced Crash Analysis")
        )

        for feature in (
            "Windows BSOD Minidump Decoding",
            "Linux Core Dump Stack Analysis",
            "Cross-Boot Crash Timeline Correlation",
            "Advanced Crash Root-Cause Investigation",
        ):
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
            details.setText(
                "Run this check to investigate crash evidence."
            )

        self.assessment_status.setText(
            "UNKNOWN — No crash checks performed"
        )
        self.assessment_details.setText(
            "No conclusion can be drawn before examining crash evidence."
        )
        self.assessment_time.setText("Last updated: Never")
        self.progress.setText("Ready — no checks performed")

    def start_checks(self, check_ids):
        if self.thread is not None:
            return

        self.progress.setText(
            "Investigating {} crash evidence source(s)...".format(
                len(check_ids)
            )
        )
        self.run_all_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        for button in self.buttons.values():
            button.setEnabled(False)

        thread = QThread(self)
        worker = CrashWorker(check_ids)
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

        colors = {
            "PASS": "#176747",
            "WARN": "#956000",
            "FAIL": "#a92e2e",
            "INFO": "#245f88",
            "UNKNOWN": "#64776c",
        }

        status_label.setText(status)
        status_label.setStyleSheet(
            "font-weight: bold; color: {};".format(
                colors.get(status, "#64776c")
            )
        )
        time_label.setText("Last checked: " + timestamp)

        summary = outcome.get("summary", "No summary available.")
        evidence = outcome.get("details", "")
        details_label.setText(
            summary + ("\n\n" + evidence if evidence else "")
        )

        self.update_assessment()

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

        if status in ("WARN", "FAIL") and completed < total:
            assessment_text = (
                "{} — Crash evidence found | "
                "Investigation incomplete ({}/{})"
            ).format(status, completed, total)
        else:
            assessment_text = (
                "{} — {} of {} checks completed"
            ).format(status, completed, total)

        self.assessment_status.setText(assessment_text)

        if status in ("WARN", "FAIL"):
            message = (
                "Potential crash evidence detected. Review the individual "
                "findings and verify their source before drawing conclusions."
            )
        elif status == "UNKNOWN":
            message = (
                "Investigation incomplete or evidence unavailable. "
                "Absence of accessible records does not prove stability."
            )
        else:
            message = (
                "No recognized crash evidence found in inspected sources. "
                "This is not proof that the system has never crashed."
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
