"""SD-01: interactive Full Health Check interface."""

from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QPlainTextEdit,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from sireh_doctor.diagnostics.full_health import (
    AREAS, tasks, run_task, outcome, summarize,
)


class AuditWorker(QThread):
    started_check = pyqtSignal(str, str, int, int)
    completed_check = pyqtSignal(str, str, object)
    audit_done = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        queue = list(tasks())
        for index, (area, check, label) in enumerate(queue, 1):
            if self.cancel_event.is_set():
                break

            self.started_check.emit(
                area, label, index, len(queue)
            )
            try:
                results = run_task(area, check)
            except Exception as exc:
                results = {
                    check: outcome(
                        "UNKNOWN",
                        "Check could not complete: "
                        + type(exc).__name__,
                    )
                }
            self.completed_check.emit(area, check, results)

            # Allow queued GUI result/cancel handling before the next check.
            # Event.wait() returns immediately if cancellation is requested.
            if self.cancel_event.wait(0.15):
                break

        self.audit_done.emit(self.cancel_event.is_set())


class FullHealthPage(QWidget):
    """Master audit; never performs repairs or recovery writes."""

    navigate = pyqtSignal(str)
    results_changed = pyqtSignal()
    audit_finished = pyqtSignal(bool)
    audit_result_ready = pyqtSignal(str, str, object)

    def __init__(self):
        super().__init__()
        self.results = {}
        self.worker = None
        self.completed = 0
        self.total = len(list(tasks()))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        body = QVBoxLayout(content)
        body.setSpacing(12)

        heading = QLabel("Full Health Check")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        body.addWidget(heading)

        subtitle = QLabel(
            "SD-01 | Guided master audit | Read-only diagnostics"
        )
        subtitle.setStyleSheet("color: #64776c;")
        body.addWidget(subtitle)

        self.notice = QLabel(
            "HOW FULL HEALTH CHECK WORKS\n\n"
            "AUTOMATIC — Run Full Health Audit checks Hardware, "
            "storage discovery, OS & Boot, Crash Detective and "
            "Security Doctor. Completed OS, crash and security "
            "results also appear in their respective tabs.\n\n"
            "MANUAL — SMART disk health requires Check Disk Health "
            "in Storage Doctor. Data Rescue provides separate "
            "read-only drive discovery. Neither is triggered by "
            "the master audit.\n\n"
            "AFTER THE AUDIT — Health Report and Repair Advisor "
            "are prepared automatically after a completed audit, "
            "using cached results only. Open either tab to review "
            "the output or manually refresh it.\n\n"
            "SAFETY — No repairs, recovery writes or configuration "
            "changes are performed. UNKNOWN does not mean PASS."
        )
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet(
            "background: #fff5dc; color: #594513; "
            "border: 1px solid #d6b76a; border-radius: 6px; "
            "padding: 12px;"
        )
        body.addWidget(self.notice)

        first = QHBoxLayout()
        self.run_button = QPushButton("Run Full Health Audit")
        self.run_button.setStyleSheet(
            "background: #176a4d; color: white; "
            "padding: 9px; font-weight: bold;"
        )
        self.run_button.clicked.connect(self.start_audit)
        first.addWidget(self.run_button)

        self.cancel_button = QPushButton("Cancel Scan")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_audit)
        first.addWidget(self.cancel_button)
        body.addLayout(first)

        second = QHBoxLayout()
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_results)
        second.addWidget(self.clear_button)

        self.report_button = QPushButton("View Health Report")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(
            lambda: self.navigate.emit("Health Report")
        )
        second.addWidget(self.report_button)

        self.advisor_button = QPushButton("Repair Advisor")
        self.advisor_button.setEnabled(False)
        self.advisor_button.clicked.connect(
            lambda: self.navigate.emit("Repair Advisor")
        )
        second.addWidget(self.advisor_button)
        body.addLayout(second)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.total)
        self.progress.setValue(0)
        body.addWidget(self.progress)

        self.progress_label = QLabel("No master audit performed.")
        self.progress_label.setWordWrap(True)
        body.addWidget(self.progress_label)

        dashboard = QGridLayout()
        self.metrics = {}
        for index, (status, title) in enumerate((
            ("FAIL", "Critical"),
            ("WARN", "Warnings"),
            ("PASS", "Passed"),
            ("UNKNOWN", "Unknown"),
        )):
            card = QLabel(title + "\n0")
            card.setAlignment(
                __import__("PyQt5.QtCore", fromlist=["Qt"]).Qt.AlignCenter
            )
            card.setStyleSheet(
                "background: #eaf0ec; border-radius: 7px; "
                "padding: 12px; color: #153d30; "
                "font-weight: bold;"
            )
            dashboard.addWidget(card, index // 2, index % 2)
            self.metrics[status] = (card, title)
        body.addLayout(dashboard)

        section = QLabel("Diagnostic areas")
        section.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #153d30;"
        )
        body.addWidget(section)

        self.area_buttons = {}
        for name, key in AREAS:
            button = QPushButton(name.replace("&", "&&") + "  |  NOT ASSESSED")
            button.setToolTip(
                "Open " + name + " for detailed diagnostics."
            )
            button.clicked.connect(
                lambda checked=False, target=name:
                self.navigate.emit(target)
            )
            body.addWidget(button)
            self.area_buttons[name] = button

        self.findings = QPlainTextEdit()
        self.findings.setReadOnly(True)
        self.findings.setPlainText(
            "Findings will appear after diagnostic checks complete."
        )
        self.findings.setMinimumHeight(360)
        self.findings.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.findings.setStyleSheet(
            "background: white; border: 1px solid #dce7df; "
            "padding: 12px; border-radius: 6px;"
        )
        body.addWidget(self.findings)

        handoff = QLabel(
            "NEXT STEPS\n\n"
            "After the audit, open Health Report to generate "
            "an exportable summary or Repair Advisor for "
            "evidence-based troubleshooting. Both use cached "
            "results and perform no new scans."
        )
        handoff.setWordWrap(True)
        body.addWidget(handoff)

        coming = QLabel(
            "COMING SOON | Advanced Master Diagnostics\n\n"
            "Automatic privileged SMART assessment, offline "
            "Windows-wide health certification, guided repair "
            "and recovery operations are not enabled in "
            "Benih 1.0."
        )
        coming.setWordWrap(True)
        coming.setStyleSheet(
            "background: #f0f2f1; color: #596b61; "
            "border: 1px solid #dce7df; border-radius: 6px; "
            "padding: 12px;"
        )
        body.addWidget(coming)

        self.future_button = QPushButton(
            "Advanced Repair / Recovery — Coming Soon"
        )
        self.future_button.setEnabled(False)
        body.addWidget(self.future_button)
        body.addStretch()

    def start_audit(self):
        if self.worker is not None:
            return

        if self.results:
            answer = QMessageBox.question(
                self,
                "Run Full Health Audit again?",
                "A previous master audit exists. Running again "
                "will replace its displayed results.\n\n"
                "Previously synchronized results in individual "
                "diagnostic tabs will remain until updated or "
                "cleared in those tabs.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self.results = {}
        self.completed = 0
        self.progress.setValue(0)
        self.refresh_dashboard()
        self.results_changed.emit()

        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        self.report_button.setEnabled(False)
        self.advisor_button.setEnabled(False)

        self.notice.setText(
            "AUDIT RUNNING\n\n"
            "Read-only checks are running in the background. "
            "Cancel stops before the next check and preserves "
            "results already collected."
        )

        worker = AuditWorker(self)
        self.worker = worker
        worker.started_check.connect(self.show_current)
        worker.completed_check.connect(self.receive_result)
        worker.audit_done.connect(self.finish_audit)
        worker.finished.connect(self.worker_finished)
        worker.start()

    def show_current(self, area, label, index, total):
        self.progress_label.setText(
            "Checking {} — {} ({} of {})".format(
                area, label, index, total
            )
        )

    def receive_result(self, area, check, results):
        if not isinstance(results, dict):
            return
        self.results.setdefault(area, {}).update(results)
        self.audit_result_ready.emit(area, check, results)
        self.completed += 1
        self.progress.setValue(self.completed)
        self.refresh_dashboard()
        self.results_changed.emit()

    def refresh_dashboard(self):
        counts, areas = summarize(self.results)

        for status, (card, title) in self.metrics.items():
            card.setText(
                "{}\n{}".format(title, counts.get(status, 0))
            )

        for name, status in areas.items():
            self.area_buttons[name].setText(
                "{}  |  {}".format(name.replace("&", "&&"), status)
            )

        lines = []
        for name, key in AREAS:
            for check, finding in self.results.get(key, {}).items():
                if not isinstance(finding, dict):
                    continue
                lines.append(
                    "[{}] {} — {}\n{}".format(
                        finding.get("status", "UNKNOWN"),
                        name,
                        check.replace("_", " ").title(),
                        finding.get("summary", ""),
                    )
                )

        self.findings.setPlainText(
            "\n\n".join(lines)
            or "No completed diagnostic findings available."
        )

    def cancel_audit(self):
        if self.worker is None:
            return
        self.worker.cancel()
        self.cancel_button.setEnabled(False)
        self.notice.setText(
            "CANCELLATION REQUESTED\n\n"
            "The active check will finish before scanning stops. "
            "Completed evidence will be preserved."
        )

    def finish_audit(self, cancelled):
        self.cancel_button.setEnabled(False)
        if cancelled:
            self.notice.setText(
                "AUDIT CANCELLED\n\n"
                "Completed results have been preserved. "
                "Unfinished diagnostic areas remain NOT ASSESSED."
            )
        else:
            self.notice.setText(
                "AUDIT COMPLETE\n\n"
                "Review the findings below. UNKNOWN does not "
                "mean PASS. Open Health Report or Repair Advisor "
                "for the next step."
            )
        self.progress_label.setText(
            "{} — {} of {} checks completed.".format(
                "Cancelled" if cancelled else "Complete",
                self.completed,
                self.total,
            )
        )
        self.report_button.setEnabled(bool(self.results))
        self.advisor_button.setEnabled(bool(self.results))
        self.audit_finished.emit(cancelled)

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        self.run_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def clear_results(self):
        if self.worker is not None:
            QMessageBox.information(
                self, "Audit in progress",
                "Cancel the scan and wait for the active check "
                "to finish before clearing the audit."
            )
            return

        if self.results:
            answer = QMessageBox.question(
                self,
                "Clear master audit results?",
                "Clear the Full Health Check results?\n\n"
                "This does not clear results already stored in "
                "Hardware, Storage, OS & Boot, Crash or Security "
                "Doctor.\n\n"
                "Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self.results = {}
        self.completed = 0
        self.progress.setValue(0)
        self.progress_label.setText(
            "No master audit performed."
        )
        self.notice.setText(
            "AUDIT CLEARED\n\n"
            "The Full Health Check display has been reset. "
            "Results previously collected in other diagnostic "
            "tabs remain unchanged."
        )
        self.report_button.setEnabled(False)
        self.advisor_button.setEnabled(False)
        self.refresh_dashboard()
        self.results_changed.emit()
