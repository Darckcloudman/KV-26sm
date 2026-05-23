# -*- coding: utf-8 -*-
"""Styled QMessageBox utilities with light-grey theme and QtAwesome alert icon."""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QPalette, QColor
import qtawesome as qta  # type: ignore[import-untyped]


def _apply_style(msg: QMessageBox):
    """Apply light-grey palette and stylesheet to a QMessageBox instance."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#5A5A5A"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
    msg.setPalette(palette)

    msg.setStyleSheet("""
        QMessageBox {
            background-color: #5A5A5A;
        }
        QMessageBox QLabel {
            background-color: transparent;
            color: #FFFFFF;
            font-size: 13px;
            padding: 8px;
        }
        QPushButton {
            background-color: #FFFFFF;
            color: #000000;
            border-radius: 6px;
            padding: 6px 18px;
            font-weight: bold;
            min-width: 70px;
        }
        QPushButton:hover {
            background-color: #E8E8E8;
        }
        QPushButton:pressed {
            background-color: #D0D0D0;
        }
    """)


def show_critical(parent, title: str, text: str):
    """Show a critical error message box."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowIcon(qta.icon("mdi.alert", color="#FF5252"))
    _apply_style(msg)
    msg.exec()


def show_warning(parent, title: str, text: str):
    """Show a warning message box."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowIcon(qta.icon("mdi.alert", color="#FFC107"))
    _apply_style(msg)
    msg.exec()


def show_info(parent, title: str, text: str):
    """Show an information message box."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowIcon(qta.icon("mdi.information", color="#448AFF"))
    _apply_style(msg)
    msg.exec()


def show_question(parent, title: str, text: str,
                  buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                  default=QMessageBox.StandardButton.No):
    """Show a question message box and return the clicked button."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setStandardButtons(buttons)
    msg.setDefaultButton(default)
    msg.setWindowIcon(qta.icon("mdi.help-circle", color="#448AFF"))
    _apply_style(msg)
    return msg.exec()


def show_about(parent, title: str, text: str):
    """Show an about message box."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowIcon(qta.icon("mdi.information", color="#448AFF"))
    _apply_style(msg)
    msg.exec()
