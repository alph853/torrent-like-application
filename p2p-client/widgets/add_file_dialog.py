import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
import requests
from PyQt6.QtGui import QPalette, QColor
from .config import *


class AddFileDialogMagnet(QDialog):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(500)

        self.setWindowTitle('Add Magnet Link')
        main_layout = QVBoxLayout()

        main_layout.addWidget(QLabel("Enter the magnet link:"))

        self.input = QLineEdit()
        main_layout.addWidget(self.input)

        main_layout.addWidget(QLabel("Choose saved directory:"))

        self.save_dir = QLineEdit()
        self.save_dir.setPlaceholderText("Select Directory")
        self.save_dir.setText(SAVE_DIR_MAGNET)

        save_dir_layout = QHBoxLayout()
        browse_button_2 = QPushButton("Browse")
        browse_button_2.clicked.connect(self.browse_dir)
        save_dir_layout.addWidget(self.save_dir)
        save_dir_layout.addWidget(browse_button_2)
        main_layout.addLayout(save_dir_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def browse_dir(self):
        folder_dialog = QFileDialog()
        folder_path = folder_dialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.save_dir.setText(folder_path)

    def accept(self):
        self.magnet_link = self.input.text()
        self.download_dir = self.save_dir.text()
        self.done(1)

    def get_result(self):
        return {
            'magnet_link': self.magnet_link,
            'download_dir': self.download_dir
        }


class AddFileDialogTorrent(QDialog):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(500)

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
            main_layout = QVBoxLayout()

            browse_layout = QHBoxLayout()
            self.filename_line = QLineEdit(file_name)
            # Button to browse for file
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(self.browse_file)
            browse_layout.addWidget(self.filename_line)
            browse_layout.addWidget(browse_button)

            self.save_dir = QLineEdit()
            self.save_dir.setPlaceholderText("Select Directory")
            self.save_dir.setText(SAVE_DIR_TORRENT)

            save_dir_layout = QHBoxLayout()
            browse_button_2 = QPushButton("Browse")
            browse_button_2.clicked.connect(self.browse_dir)
            save_dir_layout.addWidget(self.save_dir)
            save_dir_layout.addWidget(browse_button_2)

            # Add an OK button to confirm selection
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                          QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(self.accept)
            # button_box.rejected.connect(self.reject)

            main_layout.addWidget(QLabel("Chosen file:"))
            main_layout.addLayout(browse_layout)
            main_layout.addWidget(QLabel("Choose saved directory:"))
            main_layout.addLayout(save_dir_layout)
            main_layout.addWidget(button_box)

            self.setLayout(main_layout)

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

    def browse_dir(self):
        folder_dialog = QFileDialog()
        folder_path = folder_dialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.save_dir.setText(folder_path)

    def accept(self):
        if os.path.isdir(self.save_dir.text()):
            self.torrent_file_path = self.selected_file
            self.download_dir = self.save_dir.text()
            self.done(1)
        else:
            warning_dialog = QMessageBox()
            warning_dialog.setIcon(QMessageBox.Icon.Warning)
            warning_dialog.setWindowTitle("Invalid Directory")
            warning_dialog.setText("The selected directory path is not valid.")
            warning_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            warning_dialog.exec()

    def get_result(self):
        return {
            'torrent_file': self.torrent_file_path,
            'download_dir': self.download_dir
        }


class CreateTorrentDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Torrent Creator")

        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Select file/folder to share"))

        file_selection_layout = QVBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select Directory")
        self.file_path.setText('D:/STUDY/Semester241/MMT/slide')
        self.file_path.setStyleSheet("color: white;")
        file_buttons_layout = QHBoxLayout()
        select_file_button = QPushButton("Select file")
        select_folder_button = QPushButton("Select folder")
        file_buttons_layout.addWidget(select_file_button)
        file_buttons_layout.addWidget(select_folder_button)

        file_selection_layout.addWidget(self.file_path)
        file_selection_layout.addLayout(file_buttons_layout)

        main_layout.addLayout(file_selection_layout)

        vspace = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(vspace)

        settings_group = QGroupBox("Settings")
        settings_layout = QGridLayout()

        piece_size_label = QLabel("Piece size:")
        piece_size_combo = QComboBox()
        piece_size_combo.addItems(["512 KiB", "512 KiB", "512 KiB", "512 KiB"])

        calculate_pieces_button = QPushButton("Get number of pieces")
        calculate_pieces_button.clicked.connect(self.calculate_pieces)
        self.number_of_pieces_label = QLabel("N/A")

        private_torrent_checkbox = QCheckBox("Private torrent (Won't distribute on DHT network)")
        start_seeding_checkbox = QCheckBox("Start seeding immediately")
        ignore_ratio_checkbox = QCheckBox("Ignore share ratio limits for this torrent")
        optimize_alignment_checkbox = QCheckBox("Optimize alignment")

        piece_boundary_label = QLabel("Align to piece boundary for files larger than:")
        piece_boundary_combo = QComboBox()
        piece_boundary_combo.addItems(["512 KiB", "1 MiB", "2 MiB"])
        piece_boundary_combo.setStyleSheet("""
            QComboBox {
                color: white;
                background-color: black;
                border: 1px solid gray;
            }
            QComboBox QAbstractItemView {
                color: white;
                background-color: black;
            }
        """)
        piece_size_combo.setStyleSheet("""
            QComboBox {
                color: white;
                background-color: black;
                border: 1px solid gray;
            }
            QComboBox QAbstractItemView {
                color: white;
                background-color: black;
            }
        """)
        button_style = """
QPushButton {
    border: 1px solid white;
    border-radius: 5px;
    color: white;
    background-color: transparent;
    font-size:12px;
    padding-top: -3px;
    padding-bottom: -3px;
}
QPushButton:hover {
    border: 1px solid #ffd740;  
    background-color: #202020;  
}
QPushButton:pressed {
    border: 1px solid #ffb300;  
    background-color: #303030;  
}

"""
        self.setStyleSheet(button_style)
        # Adding widgets to settings layout
        settings_layout.addWidget(piece_size_label, 0, 0)
        settings_layout.addWidget(piece_size_combo, 0, 1)
        settings_layout.addWidget(calculate_pieces_button, 0, 2)
        settings_layout.addWidget(self.number_of_pieces_label, 0, 3)
        settings_layout.addWidget(private_torrent_checkbox, 1, 0, 1, 3)
        settings_layout.addWidget(start_seeding_checkbox, 2, 0, 1, 3)
        settings_layout.addWidget(ignore_ratio_checkbox, 3, 0, 1, 3)
        settings_layout.addWidget(optimize_alignment_checkbox, 4, 0, 1, 3)
        settings_layout.addWidget(piece_boundary_label, 5, 0, 1, 2)
        settings_layout.addWidget(piece_boundary_combo, 5, 2)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        vspace = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(vspace)

        # Fields for tracker URLs, web seed URLs, comments, and source
        fields_layout = QFormLayout()

        self.tracker_urls = QTextEdit()
        self.tracker_urls.setText(TRACKER_URL)
        fields_layout.addRow("Tracker URLs:", self.tracker_urls)

        save_torrent_dir_layout = QHBoxLayout()
        # save_torrent_dir_layout.addWidget(QLabel("Select file/folder to share"))

        self.save_torrent_path = QLineEdit()
        self.save_torrent_path.setPlaceholderText("Select Directory")
        self.save_torrent_path.setText(SAVE_DIR)
        self.save_torrent_path.setStyleSheet("color: white;")

        file_buttons_layout = QHBoxLayout()
        select_folder_torrent_button = QPushButton("Browse")
        file_buttons_layout.addWidget(select_folder_torrent_button)

        save_torrent_dir_layout.addWidget(self.save_torrent_path)
        save_torrent_dir_layout.addLayout(file_buttons_layout)
        fields_layout.addRow("Save torrent to:", save_torrent_dir_layout)

        main_layout.addLayout(fields_layout)

        vspace = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(vspace)

        button_layout = QHBoxLayout()
        create_button = QPushButton("Create Torrent")
        create_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(create_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        # Set the main layout
        self.setLayout(main_layout)

        # Button Connections
        select_file_button.clicked.connect(self.select_file)
        select_folder_button.clicked.connect(self.select_folder)
        select_folder_torrent_button.clicked.connect(self.select_folder_torrent)
        cancel_button.clicked.connect(self.close)

    def calculate_pieces(self):
        if os.path.exists(self.file_path.text()):
            if os.path.isdir(self.file_path.text()):
                total_length = 0
                for root, _, files in os.walk(self.file_path.text()):
                    for file in files:
                        total_length += os.path.getsize(os.path.join(root, file))
            else:
                total_length = os.path.getsize(self.file_path.text())
            num_pieces = total_length // (512 * 1024)
            num_pieces = num_pieces if total_length % (512 * 1024) == 0 else num_pieces + 1
            self.number_of_pieces_label.setText(str(num_pieces))

    def select_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select File")
        if file_path:
            self.file_path.setText(file_path)

    def select_folder(self):
        folder_dialog = QFileDialog()
        folder_path = folder_dialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.file_path.setText(folder_path)

    def select_folder_torrent(self):
        folder_dialog = QFileDialog()
        folder_path = folder_dialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.save_torrent_path.setText(folder_path)

    def accept(self):
        upload_dir = self.file_path.text()
        if not os.path.exists(upload_dir):
            QMessageBox.critical(self, "Error", "The file/folder does not exist.")
            return

        tracker_url = self.tracker_urls.toPlainText().strip()
        try:
            tracker_response = requests.get(tracker_url.replace("announce", "")).content
            if tracker_response != b'"xyz"':
                print(tracker_response)
                raise requests.exceptions.RequestException
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Error", "The tracker URL is invalid.")
            return

        save_torrent_dir = self.save_torrent_path.text()
        if not os.path.exists(save_torrent_dir):
            QMessageBox.critical(self, "Error", "The save directory for torrent file does not exist.")
            return

        self.result = {
            "upload_dir": upload_dir,
            "tracker_url": tracker_url,
            "save_torrent_dir": save_torrent_dir,
        }
        self.done(1)

    def get_result(self):
        return {
            'uploader_info': self.result
        }


class ProgressBarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = int(index.data(Qt.ItemDataRole.DisplayRole) or 0)

        # Save the painter state
        painter.save()

        # Create a QStyleOptionProgressBar
        progress_bar_option = QStyleOptionProgressBar()
        rect = option.rect
        rect.setHeight(rect.height() + 10)  # Increase the height by 10 pixels
        progress_bar_option.rect = rect
        progress_bar_option.minimum = 0
        progress_bar_option.maximum = 100
        progress_bar_option.progress = progress
        progress_bar_option.text = f"{progress}%"
        progress_bar_option.textVisible = True

        # Apply the palette colors
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#4CAF50"))  # Green color for the bar
        palette.setColor(QPalette.ColorRole.Base, QColor("#f1f1f1"))       # Background color
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#3e3e3e"))  # Text color
        progress_bar_option.palette = palette

        # Draw the progress bar
        QApplication.style().drawControl(QStyle.ControlElement.CE_ProgressBar, progress_bar_option, painter)

        # Restore the painter state
        painter.restore()

    def createEditor(self, parent, option, index):
        progress_bar = QProgressBar(parent)
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        return progress_bar

    def setEditorData(self, editor, index):
        progress = index.data(Qt.ItemDataRole.DisplayRole)
        if progress is not None:
            editor.setValue(int(progress))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value())


class LoadingScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading...")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout()
        self.label = QLabel("Loading, please wait...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.setFixedSize(300, 150)
