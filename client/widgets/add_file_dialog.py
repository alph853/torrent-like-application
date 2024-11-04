from PyQt6.QtWidgets import *


class AddFileDialogMagnet(QDialog):
    def __init__(self):
        super().__init__()

        title = "Add Magnet Link"
        label = "Enter the magnet link:"
        width = 500
        height = 120

        self.setWindowTitle(title)
        self.setFixedSize(width, height)  # Set the fixed size of the dialog
        self.layout = QVBoxLayout()

        message = QLabel(label)
        vspace = QSpacerItem(15, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(message)
        self.layout.addItem(vspace)

        self.input = QLineEdit()
        vspace = QSpacerItem(15, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.input)
        self.layout.addItem(vspace)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def accept(self):
        self.result = self.input.text()
        self.done(1)

    def get_result(self):
        return self.result


class AddFileDialogTorrent(QDialog):
    def __init__(self):
        super().__init__()
        width = 500
        height = 120

        options = QFileDialog.Option(0)  # Create an instance of QFileDialog.Options
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select a .torrent file",
            "",
            "Torrent Files (*.torrent);;All Files (*)",
            options=options  # Pass the options here
        )
        if file_name:
            self.selected_file = file_name

            self.setWindowTitle("Add Torrent File")
            self.setFixedSize(width, height)

            layout = QVBoxLayout()

            label = QLabel("Chosen file:")

            browse_layout = QHBoxLayout()
            self.filename_line = QLineEdit(file_name)

            # Button to browse for file
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(self.browse_file)
            browse_layout.addWidget(self.filename_line)
            browse_layout.addWidget(browse_button)

            # Add an OK button to confirm selection
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                          QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)

            layout.addWidget(label)
            layout.addLayout(browse_layout)
            layout.addWidget(button_box)

            self.setLayout(layout)

    def browse_file(self):
        options = QFileDialog.Option(0)  # Create an instance of QFileDialog.Options
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select a .torrent file",
            "",
            "Torrent Files (*.torrent);;All Files (*)",
            options=options  # Pass the options here
        )
        if file_name:
            self.selected_file = file_name
            self.file_name_label.setText(f"Selected file: {file_name}") 

    def accept(self):
        self.result = self.selected_file
        self.done(1)

    def get_result(self):
        return self.result


class UploadFilesDialog(QDialog):
    def __init__(self):
        super().__init__()
        width = 500
        height = 120

        options = QFileDialog.Option(0)  # Create an instance of QFileDialog.Options
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files",
            "",
            "All Files (*)",
            options=options  # Pass the options here
        )
        if file_names:
            self.selected_files = file_names

            self.setWindowTitle("Upload files: ")
            self.setFixedSize(width, height)

            layout = QVBoxLayout()

            label = QLabel("Chosen files:")

            browse_layout = QHBoxLayout()
            self.filename_line = QLineEdit(", ".join(file_names))

            # Button to browse for files
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(self.browse_files)
            browse_layout.addWidget(self.filename_line)
            browse_layout.addWidget(browse_button)

            # Add an OK button to confirm selection
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                          QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)

            layout.addWidget(label)
            layout.addLayout(browse_layout)
            layout.addWidget(button_box)

            self.setLayout(layout)

    def browse_files(self):
        options = QFileDialog.Option(0)  # Create an instance of QFileDialog.Options
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files",
            "",
            "All Files (*)",
            options=options  # Pass the options here
        )
        if file_names:
            self.selected_files = file_names
            self.filename_line.setText(", ".join(file_names))

    def accept(self):
        self.result = self.selected_files
        self.done(1)

    def get_result(self):
        return self.result


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