"""Sireh Doctor graphical application entry point."""

import sys


def main():
    from PyQt5.QtWidgets import QApplication
    from sireh_doctor.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Sireh Doctor")

    window = MainWindow()
    window.showMaximized()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
