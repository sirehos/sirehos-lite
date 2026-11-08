"""SD-10: Health Report GUI — Benih 1.0."""

from pathlib import Path

from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QScrollArea,
    QTextEdit, QVBoxLayout, QWidget,
)

from sireh_doctor.diagnostics.health_report import (
    build_report, render_report,
)


class HealthReportPage(QWidget):
    """Consolidated reporting from existing diagnostic evidence."""

    def __init__(self, snapshot_provider=None):
        super().__init__()
        self.snapshot_provider = snapshot_provider or (lambda: {})
        self.report = None

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

        heading = QLabel("Health Report")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        body.addWidget(heading)

        subtitle = QLabel(
            "SD-10 | Consolidated Diagnostics | Export & Print"
        )
        subtitle.setStyleSheet("color: #64776c;")
        body.addWidget(subtitle)

        prerequisite = QLabel("\n".join([
            "BEFORE GENERATING YOUR HEALTH REPORT",
            "",
            "Complete the relevant checks in Hardware Doctor, "
            "Storage Doctor, OS & Boot Doctor, Crash Detective "
            "and Security Doctor.",
            "",
            "Data Rescue provides optional read-only drive discovery.",
            "",
            "Return here and select Generate / Refresh Report. "
            "Incomplete checks will remain NOT ASSESSED.",
        ]))
        prerequisite.setWordWrap(True)
        prerequisite.setStyleSheet(
            "background: #fff5dc; color: #594513; "
            "border: 1px solid #d6b76a; "
            "border-radius: 7px; padding: 13px;"
        )
        body.addWidget(prerequisite)

        # Two responsive action rows prevent clipping on laptops.
        buttons = QHBoxLayout()
        secondary_buttons = QHBoxLayout()

        self.generate_button = QPushButton(
            "Generate / Refresh Report"
        )
        self.generate_button.setStyleSheet(
            "background: #176a4d; color: white; "
            "padding: 8px 12px; font-weight: bold;"
        )
        self.generate_button.clicked.connect(self.generate)
        buttons.addWidget(self.generate_button)

        self.copy_button = QPushButton("Copy Report")
        self.copy_button.clicked.connect(self.copy_report)
        buttons.addWidget(self.copy_button)

        self.save_button = QPushButton("Save TXT / MD")
        self.save_button.clicked.connect(self.save_report)
        buttons.addWidget(self.save_button)

        self.print_button = QPushButton("Print / PDF")
        self.print_button.clicked.connect(self.print_report)
        secondary_buttons.addWidget(self.print_button)

        self.clear_button = QPushButton("Clear All Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setToolTip(
            "Clears Health Report only, not other diagnostic tabs."
        )
        secondary_buttons.addWidget(self.clear_button)

        body.addLayout(buttons)
        body.addLayout(secondary_buttons)

        self.status = QLabel(
            "NOT ASSESSED — Generate a report after running "
            "the relevant diagnostic checks."
        )
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            "background: #eef5ef; color: #153d30; "
            "border: 1px solid #dce7df; "
            "border-radius: 6px; padding: 12px;"
        )
        body.addWidget(self.status)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(300)
        self.preview.setPlaceholderText(
            "The consolidated diagnostic report will appear here."
        )
        body.addWidget(self.preview)

        coming_soon = QLabel("\n".join([
            "COMING SOON | Advanced Reporting",
            "",
            "Historical report comparisons, scheduled reports "
            "and additional advanced formats are planned for "
            "future releases.",
            "",
            "TXT, Markdown and PDF export are available in Benih 1.0.",
        ]))
        coming_soon.setWordWrap(True)
        coming_soon.setStyleSheet(
            "background: #edf2f5; color: #465966; "
            "border: 1px solid #d6e0e5; "
            "border-radius: 7px; padding: 12px;"
        )
        body.addWidget(coming_soon)
        body.addSpacing(12)

        self._set_actions(False)

    def _set_actions(self, enabled):
        self.copy_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        # Print stays clickable so users receive an explanation.
        self.print_button.setEnabled(True)

    def clear_results(self):
        self.report = None
        self.preview.clear()
        self._set_actions(False)
        self.status.setText(
            "Health Report cleared. Other diagnostic results "
            "remain unchanged.\n"
            "Select Generate / Refresh Report when ready."
        )

    def generate(self):
        try:
            report = build_report(self.snapshot_provider())
            content = render_report(report)
        except Exception:
            self.report = None
            self.preview.clear()
            self._set_actions(False)
            QMessageBox.warning(
                self,
                "Report unavailable",
                "Existing diagnostic results could not "
                "be interpreted. Please retry."
            )
            return

        self.report = report
        self.preview.setPlainText(content)
        self.status.setText("\n".join([
            f"Diagnostic areas assessed: "
            f"{report['assessed']} of {report['total']}",
            f"FAIL: {report['counts']['FAIL']} | "
            f"WARN: {report['counts']['WARN']} | "
            f"UNKNOWN: {report['counts']['UNKNOWN']} | "
            f"PASS: {report['counts']['PASS']}",
            "Not assessed: "
            + (", ".join(report["unassessed"]) or "None"),
        ]))
        self._set_actions(True)

    def copy_report(self):
        if self.report is None:
            QMessageBox.information(
                self, "Report not generated",
                "Generate the report before copying."
            )
            return
        QApplication.clipboard().setText(
            render_report(self.report)
        )
        self.status.setText("Report copied to clipboard.")

    def save_report(self):
        if self.report is None:
            QMessageBox.information(
                self, "Report not generated",
                "Generate the report before exporting."
            )
            return

        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Health Report",
            "SirehDoctor_HealthReport.txt",
            "Text (*.txt);;Markdown (*.md)"
        )
        if not filename:
            return

        path = Path(filename).expanduser()
        if path.suffix.lower() not in (".txt", ".md"):
            path = path.with_suffix(
                ".md" if "Markdown" in selected_filter else ".txt"
            )

        if path.exists():
            answer = QMessageBox.question(
                self, "Confirm overwrite",
                f"Replace existing file?\n{path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                return

        try:
            content = render_report(
                self.report,
                markdown=path.suffix.lower() == ".md"
            )
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self, "Export failed", str(exc)
            )
            return

        self.status.setText(f"Report saved:\n{path}")

    def print_report(self):
        if self.report is None:
            QMessageBox.information(
                self, "Report not generated",
                "Please generate your Health Report "
                "before printing or saving as PDF."
            )
            return

        choice = QMessageBox(
            QMessageBox.Question,
            "Print / PDF",
            "Choose how to output your Health Report.",
            QMessageBox.NoButton,
            self
        )
        pdf_button = choice.addButton(
            "Save PDF", QMessageBox.AcceptRole
        )
        print_button = choice.addButton(
            "Print", QMessageBox.ActionRole
        )
        choice.addButton("Cancel", QMessageBox.RejectRole)
        choice.exec_()

        selected = choice.clickedButton()
        if selected not in (pdf_button, print_button):
            self.status.setText("Print / PDF cancelled.")
            return

        document = QTextDocument()
        document.setPlainText(render_report(self.report))

        if selected == pdf_button:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Health Report as PDF",
                "SirehDoctor_HealthReport.pdf",
                "PDF (*.pdf)"
            )
            if not filename:
                self.status.setText("PDF export cancelled.")
                return

            path = Path(filename).expanduser()
            if path.suffix.lower() != ".pdf":
                path = path.with_suffix(".pdf")

            if path.exists():
                answer = QMessageBox.question(
                    self, "Confirm overwrite",
                    f"Replace existing PDF?\n{path}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if answer != QMessageBox.Yes:
                    return

            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(str(path))
                document.print_(printer)
                if not path.is_file() or path.stat().st_size == 0:
                    raise OSError("PDF was not created.")
            except Exception as exc:
                QMessageBox.warning(
                    self, "PDF export failed",
                    "Could not create the PDF.\n\n" + str(exc)
                )
                return

            self.status.setText(f"PDF saved:\n{path}")
            return

        if not QPrinterInfo.availablePrinters():
            QMessageBox.information(
                self, "Printing unavailable",
                "No configured printer was found.\n\n"
                "Use Save PDF instead, or export as TXT / Markdown."
            )
            self.status.setText(
                "Printing unavailable: no configured printer."
            )
            return

        try:
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec_() != QPrintDialog.Accepted:
                self.status.setText("Printing cancelled.")
                return
            document.print_(printer)
            self.status.setText(
                "Report submitted to the printing system. "
                "Check the printer for completion."
            )
        except Exception as exc:
            QMessageBox.warning(
                self, "Printing failed",
                "Unable to submit the report.\n\n" + str(exc)
            )
