# -*- coding: utf-8 -*-
"""Custom directory selection dialog with tree view. Dark theme."""

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QLineEdit, QHeaderView, QAbstractItemView,
    QFileSystemModel, QFrame
)
from PySide6.QtCore import QDir, QSize
import qtawesome as qta
from .styled_message_box import show_warning


class DirectoryTreeDialog(QDialog):
    """Directory picker with QFileSystemModel + QTreeView."""

    def __init__(self, parent=None, initial_path=None):
        super().__init__(parent)
        self.setWindowTitle("Select Archive Directory")
        self.setFixedSize(480, 530)
        self.selected_directory = None
        self._history = []
        self._history_index = -1
        self._navigating_history = False
        self._home_toggle = False
        self._setup_ui()
        self._setup_model(initial_path)
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Navigation toolbar
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)

        # Back
        self.back_btn = QPushButton()
        self.back_btn.setIcon(qta.icon('mdi.arrow-left', color='#FFFFFF'))
        self.back_btn.setIconSize(QSize(16, 16))
        self.back_btn.setProperty("nav", "true")
        self.back_btn.setToolTip("Back")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setEnabled(False)
        nav_layout.addWidget(self.back_btn)

        # Forward
        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(qta.icon('mdi.arrow-right', color='#FFFFFF'))
        self.forward_btn.setIconSize(QSize(16, 16))
        self.forward_btn.setProperty("nav", "true")
        self.forward_btn.setToolTip("Forward")
        self.forward_btn.clicked.connect(self._go_forward)
        self.forward_btn.setEnabled(False)
        nav_layout.addWidget(self.forward_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #333333;")
        sep.setFixedWidth(1)
        nav_layout.addWidget(sep)

        # Up
        self.up_btn = QPushButton()
        self.up_btn.setIcon(qta.icon('mdi.arrow-up', color='#FFFFFF'))
        self.up_btn.setIconSize(QSize(16, 16))
        self.up_btn.setProperty("nav", "true")
        self.up_btn.setToolTip("Go to parent directory")
        self.up_btn.clicked.connect(self._go_up)
        nav_layout.addWidget(self.up_btn)

        # Home
        self.home_btn = QPushButton()
        self.home_btn.setIcon(qta.icon('mdi.home', color='#FFFFFF'))
        self.home_btn.setIconSize(QSize(16, 16))
        self.home_btn.setProperty("nav", "true")
        self.home_btn.setToolTip("Toggle: drives / home")
        self.home_btn.clicked.connect(self._on_home_toggle)
        nav_layout.addWidget(self.home_btn)

        # Refresh
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(qta.icon('mdi.refresh', color='#FFFFFF'))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setProperty("nav", "true")
        self.refresh_btn.setToolTip("Refresh view")
        self.refresh_btn.clicked.connect(self._refresh)
        nav_layout.addWidget(self.refresh_btn)

        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.setIconSize(QSize(8, 8))
        layout.addWidget(self.tree_view)

        # Path bar
        path_layout = QHBoxLayout()
        path_label = QLabel("Path:")
        path_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit, 1)
        layout.addLayout(path_layout)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.select_btn = QPushButton("Select")
        self.select_btn.setDefault(True)
        self.select_btn.clicked.connect(self._on_select)
        btn_layout.addWidget(self.select_btn)

        layout.addLayout(btn_layout)

        self.tree_view.clicked.connect(self._on_tree_clicked)
        self.tree_view.doubleClicked.connect(self._on_tree_double_clicked)

    def _setup_model(self, initial_path):
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Hidden)
        self.tree_view.setModel(self.model)

        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)

        # Expand root drives for visibility
        root_index = self.model.index("")
        self.tree_view.setRootIndex(root_index)
        for i in range(self.model.rowCount(root_index)):
            idx = self.model.index(i, 0, root_index)
            self.tree_view.expand(idx)

        if initial_path and Path(initial_path).exists():
            self._navigate_to_path(str(initial_path))
        else:
            home = QDir.homePath()
            self._navigate_to_path(home)

    def _update_nav_buttons(self):
        self.back_btn.setEnabled(self._history_index > 0)
        self.forward_btn.setEnabled(self._history_index < len(self._history) - 1)

    def _add_to_history(self, path):
        """Append path to history, truncating any forward entries."""
        if not path:
            return
        if self._history and self._history[self._history_index] == path:
            return
        # Truncate forward history if we branched to a new path
        if self._history_index >= 0 and self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        self._history.append(path)
        self._history_index = len(self._history) - 1
        self._update_nav_buttons()

    def _navigate_to_path(self, path, add_to_history=True):
        """Expand tree to show given path and select it."""
        if add_to_history and not self._navigating_history:
            self._add_to_history(path)
        self.path_edit.setText(path)
        self.selected_directory = path
        index = self.model.index(path)
        if index.isValid():
            # Expand all parent nodes
            parent = index.parent()
            while parent.isValid():
                self.tree_view.expand(parent)
                parent = parent.parent()
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index)

    def _go_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._navigating_history = True
            try:
                self._navigate_to_path(path, add_to_history=False)
            finally:
                self._navigating_history = False
            self._update_nav_buttons()

    def _go_forward(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._navigating_history = True
            try:
                self._navigate_to_path(path, add_to_history=False)
            finally:
                self._navigating_history = False
            self._update_nav_buttons()

    def _go_up(self):
        """Navigate to parent directory."""
        current = self.path_edit.text()
        if not current:
            return
        parent = Path(current).parent
        if parent.exists() and str(parent) != current:
            self._navigate_to_path(str(parent))

    def _on_home_toggle(self):
        """Cycle between collapse-to-drives and go-home."""
        if self._home_toggle:
            self._go_home()
        else:
            self._collapse_to_drives()
        self._home_toggle = not self._home_toggle

    def _collapse_to_drives(self):
        """Collapse all tree nodes back to root drives level."""
        root_index = self.model.index("")
        self.tree_view.setCurrentIndex(root_index)
        self._collapse_recursive(root_index)
        # Expand only root drives
        for i in range(self.model.rowCount(root_index)):
            idx = self.model.index(i, 0, root_index)
            self.tree_view.expand(idx)
        self.path_edit.setText("")
        self.selected_directory = None

    def _go_home(self):
        """Navigate to home directory."""
        self._navigate_to_path(QDir.homePath())

    def _collapse_recursive(self, parent_index):
        """Recursively collapse all children of given index."""
        rows = self.model.rowCount(parent_index)
        for i in range(rows):
            child = self.model.index(i, 0, parent_index)
            if self.tree_view.isExpanded(child):
                self._collapse_recursive(child)
                self.tree_view.collapse(child)

    def _refresh(self):
        """Refresh the model."""
        self.model.setRootPath("")
        current = self.path_edit.text()
        if current and Path(current).exists():
            self._navigate_to_path(current)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A1A;
            }
            QTreeView {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 6px;
                outline: none;
                font-size: 10px;
            }
            QTreeView::item {
                color: #FFFFFF;
                padding: 0px 4px;
                min-height: 14px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTreeView::item:selected {
                background-color: #333333;
                color: #FFFFFF;
                border-radius: 3px;
            }
            QTreeView::item:hover {
                background-color: #2A2A2A;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            /* Dotted connector lines (brighter, more visible) */
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: none;
                border-left: 1px dotted rgba(255, 255, 255, 0.28);
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-left: 1px dotted rgba(255, 255, 255, 0.28);
                border-bottom: 1px dotted rgba(255, 255, 255, 0.28);
            }
            QTreeView::branch:!has-siblings:!adjoins-item {
                border-image: none;
            }
            QTreeView::branch:!has-siblings:adjoins-item {
                border-bottom: 1px dotted rgba(255, 255, 255, 0.28);
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-bottom: 1px dotted rgba(255, 255, 255, 0.28);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-bottom: 1px dotted rgba(255, 255, 255, 0.28);
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                color: #FFFFFF;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #333333;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
            QPushButton:default {
                background-color: #FFFFFF;
                color: #000000;
            }
            QPushButton[nav="true"] {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 0px;
                font-size: 11px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                border: none;
            }
            QPushButton[nav="true"]:hover {
                background-color: #3D3D3D;
            }
            QPushButton[nav="true"]:pressed {
                background-color: #4D4D4D;
            }
            QPushButton[nav="true"]:disabled {
                background-color: #252525;
                color: #555555;
            }
            /* Custom scrollbar */
            QScrollBar:vertical {
                background: #1A1A1A;
                width: 8px;
                border-radius: 8px;
            }
            QScrollBar::handle:vertical {
                background: #E0E0E0;
                border-radius: 6px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #FFFFFF;
            }
            QScrollBar::handle:vertical:pressed {
                background: #B0B0B0;
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #1A1A1A;
                height: 8px;
                border-radius: 8px;
            }
            QScrollBar::handle:horizontal {
                background: #E0E0E0;
                border-radius: 6px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #FFFFFF;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #B0B0B0;
            }
            QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            /* Path field – not black, blends with dialog */
            QLineEdit {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
                selection-background-color: #555555;
            }
            QLabel {
                color: #FFFFFF;
                background: transparent;
            }
        """)

    def _on_tree_clicked(self, index):
        path = self.model.filePath(index)
        self.path_edit.setText(path)
        self.selected_directory = path

    def _on_tree_double_clicked(self, index):
        path = self.model.filePath(index)
        if self.model.isDir(index):
            self._navigate_to_path(path)
        else:
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def _on_select(self):
        if not self.selected_directory:
            show_warning(self, "Warning", "Please select a directory")
            return
        self.accept()

    def get_selected_directory(self):
        return self.selected_directory
