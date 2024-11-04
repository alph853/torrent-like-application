from PyQt6.QtWidgets import *

from PyQt6.QtGui import QIcon
from widgets import *
from PyQt6.uic import loadUi
import sys
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont
from widgets.add_file_dialog import *
from src import TorrentClient
import threading
from qt_material import apply_stylesheet
import time


TOR_CLIENTS = []


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main.ui", self)
        self.setWindowTitle("BitTorrent")
        self.setWindowIcon(QIcon("ui/logo.png"))
        self.setFont(QFont("Verdana", 12))
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)
        self.action_Upload_Files.triggered.connect(self.upload_files)
        self.setup_table()
        
        self.initialize_activity_log()

    def setup_table(self):
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setHorizontalHeaderLabels(["File Name", "Status", "Seeds", "Peers", "UpSpeed","DownSpeed"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    
        for i in range(self.tableWidget.columnCount() - 1):  # Exclude the last column
            self.tableWidget.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.tableWidget.horizontalHeader().sectionResized.connect(self.limit_column_width)
        self.tableWidget.setStyleSheet("""
            QHeaderView::section {
            padding: 0px;  /* Remove padding */
            margin: 0px;   /* Remove margin */
            }
        """)

    def limit_column_width(self, logicalIndex, oldSize, newSize):
        total_width = sum(self.tableWidget.horizontalHeader().sectionSize(i) for i in range(self.tableWidget.columnCount()))
        max_width = self.tableWidget.width() - self.tableWidget.verticalHeader().width()

        if total_width > max_width:
            # Calculate the excess width
            excess_width = total_width - max_width
            for i in range(self.tableWidget.columnCount()):
                if i != logicalIndex:
                    continue  

                new_size = max(0, newSize - excess_width)
                self.tableWidget.horizontalHeader().resizeSection(i, new_size)

    def initialize_activity_log(self):
        self.tab_5 = self.findChild(QWidget, "tab_5")
        layout = self.tab_5.layout()
        if layout is None:
            layout = QVBoxLayout(self.tab_5)
            layout.setContentsMargins(0, 0, 0, 0)  
            layout.setSpacing(0)  
            self.tab_5.setLayout(layout)  

        scroll_area = QScrollArea(self.tab_5)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(190)
        scroll_area.setStyleSheet("border:1px solid #535c68;")
        
        layout.addWidget(scroll_area, alignment=Qt.AlignmentFlag.AlignTop)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0) 
        content_layout.setSpacing(0) 

        self.general_label = QLabel("", content_widget)
        self.general_label.setObjectName("general_label")
        content_layout.addWidget(self.general_label)
        scroll_area.setWidget(content_widget)

    def upload_files(self):
        dialog = UploadFilesDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            up_files = dialog.get_result()
            # Update the label with the new files
            self.update_uploaded_files_label(up_files)
            for file_name in up_files:
                f = file_name.split("/")[-1]
                self.add_upload_row(f)
                self.simulate_file_upload(f)

    def simulate_file_upload(self, file_name):
        row_count = self.tableWidget.rowCount()
        for row in range(row_count):
            if self.tableWidget.item(row, 0).text() == file_name:
                progress_bar = self.tableWidget.cellWidget(row, 4)
                for progress in range(0, 101, 10):
                    QCoreApplication.processEvents()
                    progress_bar.setValue(progress)
                    time.sleep(0.2)
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #6ab04c; }")
                self.tableWidget.item(row, 1).setText("Uploaded")

    def update_uploaded_files_label(self, up_files):
        if self.general_label is not None:
            current_text = self.general_label.text() + "\n"
            current_text += "\nUpload files:"
            new_text = current_text + "\n" + "\n".join(up_files)
            self.general_label.setText(new_text)
            self.general_label.setAlignment(Qt.AlignmentFlag.AlignTop)

    def log_activity(self, message):
        """Log activity messages to the general label."""
        if self.general_label is not None:
            current_text = self.general_label.text() + "\n"
            new_text = current_text + "\n" + message
            self.general_label.setText(new_text)
            self.general_label.setAlignment(Qt.AlignmentFlag.AlignTop)

    def add_torrent_file(self):
        dialog = AddFileDialogTorrent()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            torrent_file_path = dialog.get_result()
            ip, port = "", 0
            client = TorrentClient(ip=ip, port=port, torrent_file=torrent_file_path)
            TOR_CLIENTS.append(client)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def add_magnet_link(self):
        dialog = AddFileDialogMagnet()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            magnet_link = dialog.get_result()

            current_text = self.general_label.text() + "\n"
            self.general_label.setText(current_text + "\nAdd magnet link: " + magnet_link)

            ip, port = "", 0
            client = TorrentClient(ip=ip, port=port, magnet_link=magnet_link)
            TOR_CLIENTS.append(client)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def add_upload_row(self, file_name):
        row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_position)
        self.tableWidget.setItem(row_position, 0, QTableWidgetItem(file_name))
        status_item = QTableWidgetItem("Uploading")
        self.tableWidget.setItem(row_position, 1, status_item)

        # Set empty items for "Seeds", "Peers", and "Down Speed"
        self.tableWidget.setItem(row_position, 2, QTableWidgetItem(""))  # Seeds
        self.tableWidget.setItem(row_position, 3, QTableWidgetItem(""))  # Peers
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)  
        progress_bar.setValue(0)  
        self.tableWidget.setCellWidget(row_position, 4, progress_bar)  # Upload Progress

    def display_client_UI(self, client):
        """Display the client in the UI.""" 
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_amber.xml')
    window.show()
    sys.exit(app.exec())