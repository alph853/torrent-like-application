import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt


class ConfigForm(QDialog):
    def __init__(self, display_name, file_names=[], info={}, width=1000, height=500):
        super().__init__()

        if display_name is None:
            display_name = "Unknown Torrent"

        self.setWindowTitle(display_name)
        self.setFixedSize(width, height)

        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        # Left Panel: Information labels
        left_panel = QVBoxLayout()
        label1 = QLabel("Label 1: Some Info")
        label2 = QLabel("Label 2: More Info")
        left_panel.addWidget(label1)
        left_panel.addWidget(label2)

        # Right Panel: List of strings with checkboxs
        right_panel = QVBoxLayout()
        label = QLabel("Select files to download:")
        right_panel.addWidget(label)
        self.checkbox_list = QListWidget()
        for string in file_names:
            checkbox_item = QListWidgetItem(self.checkbox_list)
            checkbox = QCheckBox(string)
            self.checkbox_list.setItemWidget(checkbox_item, checkbox)
        right_panel.addWidget(self.checkbox_list)

        # Add left and right panels to the top layout
        top_layout.addLayout(left_panel)
        top_layout.addLayout(right_panel)

        bottom_layout = QHBoxLayout()
        # Directory Chooser Button
        self.dir_edit = QLineEdit()
        self.dir_edit.setText(os.getcwd())
        bottom_layout.addWidget(self.dir_edit)

        dir_button = QPushButton("Choose Directory")
        dir_button.clicked.connect(self.choose_directory)
        bottom_layout.addWidget(dir_button)

        # Add top layout and directory button to the main layout
        main_layout.addLayout(top_layout)
        label = QLabel("Select saved directory:")
        main_layout.addWidget(label)
        main_layout.addLayout(bottom_layout)

        # Bottom Layout: OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)  # OK button
        button_box.rejected.connect(self.reject)  # Cancel button

        main_layout.addWidget(button_box)

    def choose_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Choose Directory")
        self.dir_edit.setText(dir_path)

    def accept(self):
        self.result = self.get_selected_files()
        self.done(1)

    def get_selected_files(self):
        selected_files = dict()
        for i in range(self.checkbox_list.count()):
            filename = self.checkbox_list.item(i).text()
            selected_files[filename] = (filename.checkState() == Qt.CheckState.Checked)
        return selected_files


class ConfigFormTorrent(QDialog):
    def __init__(self, display_name, file_names, info):
        super().__init__()
        self.setWindowTitle(display_name)
        self.setGeometry(100, 100, 300, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("Select a file to download:")
        self.layout.addWidget(self.label)

        # Create a QListWidget to display file names
        self.file_list_widget = QListWidget()
        self.file_list_widget.addItems(file_names)  # Add file names to the list widget
        self.layout.addWidget(self.file_list_widget)

        # Add an OK button to confirm selection
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)

    def get_selected_files(self):
        selected_items = self.file_list_widget.selectedItems()
        return [item.text() for item in selected_items]
