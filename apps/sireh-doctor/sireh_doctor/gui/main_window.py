"""Main graphical interface for Sireh Doctor."""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sireh_doctor.gui.hardware_page import HardwarePage
from sireh_doctor.gui.storage_page import StoragePage
from sireh_doctor.gui.os_boot_page import OSBootPage
from sireh_doctor.gui.crash_page import CrashPage


FEATURES = [
    "Full Health Check",
    "Hardware Doctor",
    "Storage Doctor",
    "OS & Boot Doctor",
    "Crash Detective",
    "Security Doctor",
    "Data Rescue",
    "Repair Advisor",
    "Command Clinic",
    "Health Report",
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sireh Doctor | Benih 1.0")

        logo_path = (
            Path(__file__).resolve().parents[4]
            / "assets/branding/SirehOS_Lite_Emblem.png"
        )

        if logo_path.is_file():
            self.setWindowIcon(QIcon(str(logo_path)))


        help_menu = self.menuBar().addMenu("Help")

        guide_action = help_menu.addAction("How to use Sireh Doctor")
        guide_action.triggered.connect(self.show_help)

        about_action = help_menu.addAction("About Sireh Doctor")
        about_action.triggered.connect(self.show_about)

        self.resize(1050, 700)
        self.setMinimumSize(800, 550)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(255)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 25, 18, 20)

        logo = QLabel()
        logo.setObjectName("sirehLogo")
        logo.setAlignment(Qt.AlignCenter)

        if logo_path.is_file():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(
                        110, 105,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )

        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(10)

        brand = QLabel("Sireh Doctor")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        subtitle = QLabel("BENIH 1.0  |  DIAGNOSTICS")
        subtitle.setObjectName("subtitle")
        sidebar_layout.addWidget(subtitle)

        sidebar_layout.addSpacing(25)

        self.navigation = QListWidget()
        self.navigation.addItems(FEATURES)
        self.navigation.setSpacing(5)
        sidebar_layout.addWidget(self.navigation)

        footer = QLabel("Sireh OS Lite\nOffline-first diagnostics")
        footer.setObjectName("footer")
        sidebar_layout.addWidget(footer)

        layout.addWidget(sidebar)

        self.pages = QStackedWidget()

        for index, feature in enumerate(FEATURES, start=1):
            if feature == "Hardware Doctor":
                self.pages.addWidget(HardwarePage())
                continue

            if feature == "Storage Doctor":
                self.pages.addWidget(StoragePage())
                continue

            if feature == "OS & Boot Doctor":
                self.pages.addWidget(OSBootPage())
                continue

            if feature == "Crash Detective":
                self.pages.addWidget(CrashPage())
                continue

            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(45, 40, 45, 40)

            heading = QLabel(feature)
            heading.setObjectName("heading")
            page_layout.addWidget(heading)

            description = QLabel(
                f"SD-{index:02d}  |  Diagnostic module"
            )
            description.setObjectName("description")
            page_layout.addWidget(description)

            page_layout.addSpacing(35)

            status = QLabel(
                "Diagnostic engine not yet implemented.\n\n"
                "This page is part of the GUI development foundation."
            )
            status.setObjectName("status")
            status.setWordWrap(True)
            status.setAlignment(Qt.AlignCenter)
            page_layout.addWidget(status)

            page_layout.addStretch()

            self.pages.addWidget(page)

        layout.addWidget(self.pages, 1)

        self.navigation.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )
        self.navigation.setCurrentRow(0)

        self.setStyleSheet("""
            QMainWindow, QStackedWidget {
                background: #f5f8f6;
            }

            #sidebar {
                background: #153d30;
            }

            #brand {
                color: white;
                font-size: 25px;
                font-weight: bold;
            }

            #subtitle {
                color: #a8c9b5;
                font-size: 10px;
                letter-spacing: 1px;
            }

            QListWidget {
                background: transparent;
                border: none;
                color: #e4f0e9;
                font-size: 13px;
                outline: none;
            }

            QListWidget::item {
                padding: 12px 9px;
                border-radius: 6px;
            }

            QListWidget::item:selected {
                background: #2e7754;
                color: white;
            }

            QListWidget::item:hover:!selected {
                background: #245340;
            }

            #footer {
                color: #b0c9bb;
                font-size: 11px;
                padding-top: 15px;
            }

            #heading {
                color: #153d30;
                font-size: 29px;
                font-weight: bold;
            }

            #description {
                color: #64776c;
                font-size: 13px;
            }

            #status {
                background: white;
                border: 1px solid #dce7df;
                border-radius: 12px;
                color: #64776c;
                font-size: 15px;
                padding: 35px;
            }
        """)



    def show_help(self):
        QMessageBox.information(
            self,
            "Sireh Doctor - Getting Started",
            """SIREH DOCTOR - GETTING STARTED

GRAPHICAL MODE
Launch Sireh Doctor from the application menu
once desktop integration is complete.

Current development launch:
cd apps/sireh-doctor
python3 -m sireh_doctor.main

TERMINAL MODE
sireh help - Show available CLI commands
sireh info - Show system information

PLANNED
sireh doctor --gui - GUI shortcut
(not implemented yet)"""
        )

    def show_about(self):
        QMessageBox.about(
            self,
            "About Sireh Doctor",
            """Sireh Doctor
Sireh OS Lite 1.0 Benih

Offline-first infrastructure diagnostics.
Independent open-source development."""
        )
