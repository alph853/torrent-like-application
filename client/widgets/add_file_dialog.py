from PyQt6.QtWidgets import *


class AddFileDialog(QDialog):
    def __init__(self, title, label=None, input=True, button=True, width=500, height=120):
        super().__init__()
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
