"""Permanent B015 regression tests for Security Doctor."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QPlainTextEdit

from sireh_doctor.diagnostics import security_doctor as engine
from sireh_doctor.gui.security_page import (
    SecurityPage, SecurityWorker, DESCRIPTIONS, FUTURE_FEATURES,
)


class SecurityEngineTests(unittest.TestCase):

    def test_eight_registered_checks(self):
        self.assertEqual(len(engine.CHECKS), 8)

    def test_every_check_has_runner(self):
        self.assertEqual(set(engine.CHECKS), set(engine.RUNNERS))

    def test_descriptions_match_checks(self):
        self.assertEqual(set(DESCRIPTIONS), set(engine.CHECKS))

    def test_result_contract(self):
        for check_id in engine.CHECKS:
            with self.subTest(check_id=check_id):
                with patch.dict(engine.RUNNERS, {
                    check_id: lambda: {
                        "status": "INFO",
                        "summary": "Test evidence",
                        "details": "Target: Running Linux session",
                    }
                }):
                    outcome = engine.run_check(check_id)
                self.assertIsInstance(outcome, dict)
                self.assertEqual(outcome["status"], "INFO")
                self.assertTrue(outcome["summary"])
                self.assertTrue(outcome["details"])

    def test_worker_handles_collector_exception(self):
        worker = SecurityWorker(["access_control"])
        received = []
        worker.completed.connect(
            lambda key, outcome, timestamp:
            received.append((key, outcome, timestamp))
        )
        with patch(
            "sireh_doctor.gui.security_page.run_check",
            side_effect=RuntimeError("simulated failure"),
        ):
            worker.run()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][1]["status"], "UNKNOWN")
        self.assertTrue(received[0][2])


class SecurityGuiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = SecurityPage()

    def tearDown(self):
        self.page.close()

    def test_eight_cards_and_buttons(self):
        self.assertEqual(len(self.page.cards), 8)
        self.assertEqual(len(self.page.buttons), 8)

    def test_all_cards_use_readonly_evidence_viewers(self):
        for status, timestamp, viewer in self.page.cards.values():
            self.assertIsInstance(viewer, QPlainTextEdit)
            self.assertTrue(viewer.isReadOnly())

    def test_evidence_wraps_and_preserves_long_lines(self):
        viewer = next(iter(self.page.cards.values()))[2]
        sample = "LONG-LINE-" * 200
        viewer.setPlainText(sample)
        self.assertEqual(viewer.toPlainText(), sample)
        self.assertEqual(
            viewer.lineWrapMode(), QPlainTextEdit.WidgetWidth
        )

    def test_future_previews_disabled(self):
        self.assertEqual(len(FUTURE_FEATURES), 4)
        buttons = self.page.findChildren(
            __import__("PyQt5.QtWidgets", fromlist=["QPushButton"]).QPushButton
        )
        for feature in FUTURE_FEATURES:
            matches = [b for b in buttons if feature in b.text()]
            self.assertEqual(len(matches), 1)
            self.assertFalse(matches[0].isEnabled())

    def test_initial_assessment_unknown(self):
        self.assertIn("UNKNOWN", self.page.assessment_status.text())
        self.assertFalse(self.page.results)

    def test_individual_result_updates_card(self):
        key = next(iter(engine.CHECKS))
        outcome = {
            "status": "INFO",
            "summary": "Evidence collected",
            "details": "Target: Running Linux session",
        }
        self.page.receive_result(key, outcome, "TEST TIME")
        status, timestamp, viewer = self.page.cards[key]
        self.assertEqual(status.text(), "INFO")
        self.assertIn("TEST TIME", timestamp.text())
        self.assertIn("Evidence collected", viewer.toPlainText())
        self.assertEqual(len(self.page.results), 1)

    def test_partial_execution_not_certified(self):
        key = next(iter(engine.CHECKS))
        self.page.receive_result(key, {
            "status": "INFO",
            "summary": "Evidence collected",
            "details": "Test evidence",
        }, "TEST TIME")
        text = self.page.assessment_status.text()
        self.assertIn("1 of 8 checks executed", text)
        self.assertIn("UNKNOWN", text)
        self.assertNotIn("Security assessment: PASS", text)

    def test_complete_with_unknown_remains_unknown(self):
        for key in engine.CHECKS:
            self.page.receive_result(key, {
                "status": "UNKNOWN" if key == "remote_access" else "INFO",
                "summary": "Evidence inspected",
                "details": "Test evidence",
            }, "TEST TIME")
        text = self.page.assessment_status.text()
        self.assertIn("COMPLETE", text)
        self.assertIn("Security assessment: UNKNOWN", text)

    def test_complete_info_is_not_pass(self):
        for key in engine.CHECKS:
            self.page.receive_result(key, {
                "status": "INFO",
                "summary": "Evidence inspected",
                "details": "Test evidence",
            }, "TEST TIME")
        text = self.page.assessment_status.text()
        self.assertIn("Security assessment: INFO", text)
        self.assertNotIn("Security assessment: PASS", text)

    def test_warning_takes_priority(self):
        for key in engine.CHECKS:
            self.page.receive_result(key, {
                "status": "WARN" if key == "file_permissions" else "INFO",
                "summary": "Evidence inspected",
                "details": "Test evidence",
            }, "TEST TIME")
        self.assertIn(
            "Security assessment: WARN",
            self.page.assessment_status.text(),
        )

    def test_clear_resets_all_results(self):
        key = next(iter(engine.CHECKS))
        self.page.receive_result(key, {
            "status": "INFO",
            "summary": "Evidence inspected",
            "details": "Test evidence",
        }, "TEST TIME")
        self.page.clear_results()
        self.assertFalse(self.page.results)
        self.assertFalse(self.page.checked_at)
        self.assertTrue(all(
            labels[0].text() == "NOT CHECKED"
            for labels in self.page.cards.values()
        ))
        self.assertIn(
            "No security checks performed",
            self.page.assessment_status.text(),
        )


if __name__ == "__main__":
    unittest.main()
