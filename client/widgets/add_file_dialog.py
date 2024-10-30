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
            self.filename_line.setText(file_name)

    def accept(self):
        self.result = self.selected_file
        self.done(1)

    def get_result(self):
        return self.result
