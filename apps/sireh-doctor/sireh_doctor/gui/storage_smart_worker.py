"""Background SMART collection for the Storage Doctor GUI."""

from PyQt5.QtCore import QThread, pyqtSignal

from sireh_doctor.diagnostics.storage_smart import collect_smart
from sireh_doctor.diagnostics.storage_smart_health import assess_smart


class SmartWorker(QThread):
    """Collect SMART evidence without blocking the Qt event loop."""

    completed = pyqtSignal(object)

    def __init__(self, device_path, parent=None):
        super().__init__(parent)
        self.device_path = device_path

    def run(self):
        try:
            collection = collect_smart(self.device_path)
            assessment = assess_smart(collection)

            self.completed.emit({
                "device": self.device_path,
                "collection": collection,
                "assessment": assessment,
            })
        except Exception:
            self.completed.emit({
                "device": self.device_path,
                "collection": {
                    "status": "UNKNOWN",
                    "error": "Unexpected SMART collection error",
                },
                "assessment": {
                    "status": "UNKNOWN",
                    "summary": "SMART health could not be assessed.",
                    "recommendation": (
                        "An unexpected diagnostic error occurred."
                    ),
                    "metrics": {},
                },
            })
