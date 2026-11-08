"""Sireh Doctor SD-08: read-only Repair Advisor interface."""

from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)
from sireh_doctor.diagnostics.repair_advisor import build_plan


class RepairAdvisorPage(QWidget):
    """Advisory-only evidence synthesis; no commands are executed."""

    def __init__(self, snapshot_provider=None):
        super().__init__()
        self.snapshot_provider = snapshot_provider or (lambda: {})
        self.plan = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        self.body = QVBoxLayout(content)
        self.body.setSpacing(12)

        title = QLabel("Repair Advisor")
        title.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        self.body.addWidget(title)

        subtitle = QLabel(
            "SD-08 | Windows & Linux | Evidence-based troubleshooting"
        )
        subtitle.setStyleSheet("color: #64776c;")
        self.body.addWidget(subtitle)

        self.body.addWidget(self._card(
            "Safety-first advisory",
            "Recommendations are based only on existing diagnostic "
            "results. No new scans, repairs, commands or disk writes "
            "are performed. Advice is not proof of a diagnosis."
        ))

        instructions = [
            "STEP 1 — Run checks in the relevant Doctor tabs:",
            "",
            "• Hardware Doctor — hardware health",
            "• Storage Doctor — drive discovery and SMART health",
            "• OS & Boot Doctor — operating system and boot evidence",
            "• Crash Detective — crash and failure evidence",
            "• Security Doctor — security configuration",
            "• Data Rescue — read-only drive discovery only",
            "",
            "STEP 2 — Return here and click Analyze Existing Results.",
            "STEP 3 — Review findings and recommended next steps.",
            "STEP 4 — Copy the troubleshooting plan if needed.",
            "",
            "You do not need to run every tab. Choose checks relevant "
            "to your problem. Unrun checks remain NOT ASSESSED.",
            "Repair Advisor never performs repairs.",
        ]

        self.body.addWidget(self._card(
            "BEFORE USING REPAIR ADVISOR | How It Works",
            chr(10).join(instructions)
        ))

        buttons = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze Existing Results")
        self.analyze_button.clicked.connect(self.analyze)
        self.analyze_button.setStyleSheet(
            "background: #176a4d; color: white; "
            "padding: 8px 14px; font-weight: bold;"
        )
        buttons.addWidget(self.analyze_button)

        self.copy_button = QPushButton("Copy Troubleshooting Plan")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_plan)
        buttons.addWidget(self.copy_button)

        self.clear_button = QPushButton("Clear All Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setToolTip(
            "Clears Repair Advisor only; other diagnostic tabs are unchanged."
        )
        buttons.addWidget(self.clear_button)
        buttons.addStretch()
        self.body.addLayout(buttons)

        self.summary = self._card(
            "Assessment status",
            "Not assessed. Run diagnostic checks in the relevant tabs, "
            "then select Analyze Existing Results."
        )
        self.body.addWidget(self.summary)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.body.addWidget(self.results_container)

        self.body.addWidget(self._card(
            "COMING SOON | Advanced Repair Features",
            "Disabled pending controlled safety validation:\n"
            "• Automated filesystem repairs and disk modifications\n"
            "• Windows BCD and Linux GRUB rebuilding\n"
            "• Registry changes and partition operations\n"
            "• Privileged command execution and one-click repairs\n"
            "• Automated cross-device recovery actions\n\n"
            "Benih 1.0 provides guidance only, never automatic repair."
        ))
        self.body.addStretch()

    def _card(self, heading, description):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: white; border: 1px solid #dce7df; "
            "border-radius: 7px; }"
            "QLabel { border: none; }"
        )
        layout = QVBoxLayout(frame)
        heading_label = QLabel(heading)
        heading_label.setStyleSheet(
            "font-weight: bold; color: #176a4d; font-size: 14px;"
        )
        layout.addWidget(heading_label)
        text = QLabel(description)
        text.setWordWrap(True)
        text.setTextInteractionFlags(text.textInteractionFlags())
        text.setStyleSheet("color: #344f42;")
        layout.addWidget(text)
        return frame

    def _clear_findings(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _friendly_check(check):
        """Present internal check identifiers in readable form."""
        text = str(check).replace("_", " ").strip()
        return text[:1].upper() + text[1:] if text else "Unnamed check"

    @staticmethod
    def _finding_groups(findings):
        """Separate observed concerns from inconclusive evidence."""
        concerns = [
            item for item in findings
            if item.get("status") in ("FAIL", "CRITICAL", "WARN", "WARNING")
        ]
        inconclusive = [
            item for item in findings
            if item.get("status") in ("UNKNOWN", "ERROR")
        ]
        return concerns, inconclusive

    def analyze(self):
        try:
            snapshots = self.snapshot_provider()
            self.plan = build_plan(snapshots)
        except Exception as exc:
            self.clear_results()
            self.summary.layout().itemAt(1).widget().setText(
                "Assessment unavailable. Existing result data "
                "could not be interpreted."
            )
            return

        self._clear_findings()
        plan = self.plan
        findings = plan["findings"]

        concerns, inconclusive = self._finding_groups(findings)

        summary_text = chr(10).join([
            f"Diagnostic sources assessed: "
            f"{plan['assessed_sources']} of {plan['total_sources']}",
            f"Diagnostic sources not assessed: "
            f"{len(plan['unassessed_sources'])}",
            f"Observed warnings / failures: {len(concerns)}",
            f"Inconclusive findings requiring further checks: "
            f"{len(inconclusive)}",
            "Not assessed: "
            + (", ".join(plan["unassessed_sources"]) or "None"),
        ])
        self.summary.layout().itemAt(1).widget().setText(summary_text)

        for group_title, group_items in (
            ("OBSERVED WARNINGS / FAILURES", concerns),
            ("INCONCLUSIVE — FURTHER CHECKS REQUIRED", inconclusive),
        ):
            if not group_items:
                continue

            self.results_layout.addWidget(self._card(
                group_title,
                (
                    "These findings identify observed concerns."
                    if group_items is concerns
                    else "UNKNOWN means insufficient evidence, "
                         "not a confirmed fault or a PASS."
                )
            ))

            for index, finding in enumerate(group_items, 1):
                self.results_layout.addWidget(self._card(
                    f"{index}. [{finding['status']}] "
                    f"{finding['source']} — "
                    f"{self._friendly_check(finding['check'])}",
                f"Evidence: {finding['summary']}\n\n"
                f"Recommended next step: {finding['recommendation']}\n"
                f"Risk classification: {finding['risk']}"
                + (
                    f"\nOriginal diagnostic recommendation: "
                    f"{finding['source_recommendation']}"
                    if finding["source_recommendation"] else ""
                )
            ))

        if not findings:
            self.results_layout.addWidget(self._card(
                "No actionable findings in available results",
                "This does not establish that the system is healthy. "
                "Unrun or incomplete diagnostics remain unassessed."
            ))

        self.copy_button.setEnabled(True)

    def _plan_text(self):
        if self.plan is None:
            return ""
        lines = [
            "Sireh Doctor | Repair Advisor | Benih 1.0",
            "Advisory only — no automated repairs",
            "",
            f"Sources assessed: {self.plan['assessed_sources']} "
            f"of {self.plan['total_sources']}",
            "Not assessed: "
            + (", ".join(self.plan["unassessed_sources"]) or "None"),
            "",
        ]
        for index, item in enumerate(self.plan["findings"], 1):
            lines.extend([
                f"{index}. [{item['status']}] "
                f"{item['source']} / "
                f"{self._friendly_check(item['check'])}",
                f"Evidence: {item['summary']}",
                f"Next step: {item['recommendation']}",
                f"Risk: {item['risk']}",
                "",
            ])
        return "\n".join(lines)

    def copy_plan(self):
        if self.plan is None or self.plan["assessed_sources"] == 0:
            QMessageBox.information(
                self,
                "No Diagnostic Results",
                "No diagnostic results are available yet. "
                "Run checks in the relevant Doctor tabs, then "
                "select Analyze Existing Results."
            )
            return

        text = self._plan_text()
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

            if clipboard.text() != text:
                raise RuntimeError("Clipboard verification failed")

            QMessageBox.information(
                self,
                "Troubleshooting Plan Copied",
                "The troubleshooting plan was copied to your clipboard.\n\n"
                "You can paste it into a text editor, email or document."
            )
        except Exception:
            QMessageBox.warning(
                self,
                "Copy Failed",
                "The troubleshooting plan could not be copied "
                "to the clipboard."
            )

    def clear_results(self):
        self.plan = None
        self._clear_findings()
        self.copy_button.setEnabled(False)
        self.summary.layout().itemAt(1).widget().setText(
            "Results cleared. Other diagnostic tabs are unchanged. "
            "Select Analyze Existing Results to assess available evidence."
        )
