"""Sireh Doctor SD-09: offline Ubuntu command reference."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView,
)
from sireh_doctor.diagnostics.command_clinic import (
    COMMANDS, CATEGORIES, search_commands,
)

class CommandClinicPage(QWidget):
    """Search and copy Ubuntu command examples; never execute them."""

    def __init__(self):
        super().__init__()
        self.selected = None

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

        heading = QLabel("Command Clinic")
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #153d30;"
        )
        body.addWidget(heading)

        subtitle = QLabel(
            "SD-09 | Ubuntu Command Reference | Offline Learning"
        )
        subtitle.setStyleSheet("color: #64776c;")
        body.addWidget(subtitle)

        notice = QLabel(chr(10).join([
            "LEARN • INSPECT • COPY — Command Clinic does not run commands.",
            "",
            "1. Select a command and read its description and safety level.",
            "2. Consult COMMAND --help or man COMMAND for available options.",
            "3. Open a terminal and type commands yourself when appropriate.",
            "4. Replace placeholders such as FILE, PACKAGE and /dev/sdX.",
            "",
            "Ubuntu/Linux commands generally use --help, not Windows /?.",
            "Some commands require extra packages, network or privileges.",
            "Avoid modification and HIGH RISK commands on rescue targets.",
        ]))
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "background: white; border: 1px solid #dce7df;"
            "border-radius: 7px; padding: 12px; color: #344f42;"
        )
        body.addWidget(notice)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search commands: disk, apt, journalctl, network..."
        )
        filters.addWidget(self.search, 2)

        self.category = QComboBox()
        self.category.addItems(["All Categories"] + CATEGORIES)
        filters.addWidget(self.category, 1)
        body.addLayout(filters)

        self.count_label = QLabel()
        body.addWidget(self.count_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Command example", "Purpose", "Category", "Safety"
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.setMinimumHeight(420)
        body.addWidget(self.table)

        detail_heading = QLabel("Selected command")
        detail_heading.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #176a4d;"
        )
        body.addWidget(detail_heading)

        self.detail = QLabel(
            "Select a command to see its syntax, purpose and safety."
        )
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail.setStyleSheet(
            "background: white; border: 1px solid #dce7df;"
            "border-radius: 7px; padding: 12px;"
        )
        body.addWidget(self.detail)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copy Selected Command")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_command)
        buttons.addWidget(self.copy_button)

        self.help_button = QPushButton("Copy Help Example")
        self.help_button.setEnabled(False)
        self.help_button.clicked.connect(self.copy_help)
        buttons.addWidget(self.help_button)
        buttons.addStretch()
        body.addLayout(buttons)

        footer = QLabel(
            "REFERENCE ONLY | No built-in terminal or automatic execution. "
            "Commands are examples, not verified repair instructions."
        )
        footer.setWordWrap(True)
        body.addWidget(footer)

        self.search.textChanged.connect(self.refresh)
        self.category.currentTextChanged.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self.select_command)
        self.refresh()

    def refresh(self, *_):
        self.filtered = search_commands(
            self.search.text(), self.category.currentText()
        )
        self.selected = None
        self.copy_button.setEnabled(False)
        self.help_button.setEnabled(False)
        self.table.setRowCount(len(self.filtered))

        for row, entry in enumerate(self.filtered):
            values = (
                entry.syntax, entry.description,
                entry.category,
                {"R": "READ-ONLY", "C": "MODIFIES",
                 "H": "HIGH RISK"}[entry.safety],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setToolTip(
                        "Review carefully. This is not a safety guarantee."
                    )
                self.table.setItem(row, column, item)

        self.count_label.setText(
            f"Showing {len(self.filtered)} of {len(COMMANDS)} "
            "Ubuntu/Linux command examples"
        )
        self.detail.setText(
            "Select a command to inspect it. Nothing runs automatically."
        )

    def select_command(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.filtered):
            self.selected = None
            return

        entry = self.filtered[row]
        self.selected = entry
        safety = {
            "R": "READ-ONLY / INSPECTION",
            "C": "MODIFIES SYSTEM OR FILES",
            "H": "HIGH RISK / POTENTIALLY DESTRUCTIVE",
        }[entry.safety]

        self.detail.setText(chr(10).join([
            "Command: " + entry.syntax,
            "Category: " + entry.category,
            "Purpose: " + entry.description,
            "Safety: " + safety,
            "",
            "Read the manual and verify the target before using.",
            "Copying does not execute the command.",
        ]))
        self.copy_button.setEnabled(True)
        self.help_button.setEnabled(True)

    def copy_command(self):
        if self.selected is None:
            return
        QApplication.clipboard().setText(self.selected.syntax)

    def copy_help(self):
        if self.selected is None:
            return
        command = self.selected.syntax.split()[0]
        if command == "sudo":
            parts = self.selected.syntax.split()
            command = parts[1] if len(parts) > 1 else "sudo"
        if command.startswith("/"):
            command = command.rsplit("/", 1)[-1]
        QApplication.clipboard().setText(
            "man " + command
        )
