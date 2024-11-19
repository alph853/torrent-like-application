import socket
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QFont, QStandardItem, QStandardItemModel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi
import sys
from widgets.add_file_dialog import *
from src import TorrentClient
import threading
from qt_material import apply_stylesheet


def get_ip_and_port():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]
    return ip, port


class MainWindow(QMainWindow):
    update_peers_signal = pyqtSignal(str)
    update_torrent_table_signal = pyqtSignal(list) 
    current_torrent = None
    previous_peers = None

    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.setWindowIcon(QIcon("logo.png"))
        self.setWindowTitle("BitTorrent")

        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.loading_screen = None

        # Torrent Table Model
        self.torrent_model = QStandardItemModel(self)
        self.tableView.setModel(self.torrent_model)  
        self.setup_torrent_table()

        # Files Table Model
        self.files_model = QStandardItemModel(self)
        self.tableWidgetContent.setModel(self.files_model) 
        self.setup_files_table()

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)
        self.actionCreate_Torrent_2.triggered.connect(self.create_torrent)
        self.label_peers = self.findChild(QLabel, 'label_peers')
        self.update_peers_signal.connect(self.update_peers_label)
        self.update_torrent_table_signal.connect(self.update_download_progress)  

    def create_torrent(self):
        dialog = CreateTorrentDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            uploader_info = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, uploader_info=uploader_info)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def setup_torrent_table(self):
        self.torrent_model.setHorizontalHeaderLabels(["Torrent", "Progress", "Status", "Seeds", "Peers", "UpSpeed", "DownSpeed"])
        self.tableView.setModel(self.torrent_model)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetContent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)


    def setup_files_table(self):
        self.files_model.setHorizontalHeaderLabels(["File Name", "Total Size", "Remaining", "Progress"])
        self.tableWidgetContent.setModel(self.files_model)
        self.tableWidgetContent.horizontalHeader().setStretchLastSection(True)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tableWidgetContent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tableView.horizontalHeader().sectionResized.connect(self.limit_column_width)
        self.tableView.setStyleSheet("""
            QHeaderView::section {
                padding: 0px; 
                margin: 0px;  
            }
        """)
        self.tableView.clicked.connect(self.on_table_row_clicked)

    def on_table_row_clicked(self, row, column):
        self.current_torrent = self.tableView.item(row, 0).text()

    def limit_column_width(self, logicalIndex, oldSize, newSize):
        total_width = sum(self.tableView.horizontalHeader().sectionSize(i) for i in range(self.tableView.model().columnCount()))
        max_width = self.tableView.width() - self.tableView.verticalHeader().width()

        if total_width > max_width:
            excess_width = total_width - max_width
            for i in range(self.tableView.model().columnCount()):
                if i != logicalIndex:
                    continue  

                new_size = max(0, newSize - excess_width)
                self.tableView.horizontalHeader().resizeSection(i, new_size)

    def add_torrent_file(self):
        dialog = AddFileDialogTorrent()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            torrent_file_path, download_dir = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, torrent_file=torrent_file_path, download_dir=download_dir)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def add_magnet_link(self):
        dialog = AddFileDialogMagnet()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            magnet_link, download_dir = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, magnet_link=magnet_link, download_dir=download_dir)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def display_client_UI(self, client: TorrentClient):
        """Display the client in the UI."""
        threading.Thread(target=self.display_console, daemon=True, args=(client, )).start()
        while True:
            if not client.is_metadata_complete():
                self.display_loading_screen()
            else:
                self.hide_loading_screen()
                self.display_torrent_screen(client)
                threading.Thread(target=self.display_download_progress, daemon=True, args=(client, )).start()
                threading.Thread(target=self.display_peers, daemon=True, args=(client, )).start()

    def display_console(self, client: TorrentClient):
        self.console.append(client.get_console_output())
        time.sleep(0.1)

    def display_loading_screen(self):
        if not self.loading_screen:
            self.loading_screen = LoadingScreen(self)
        self.loading_screen.set_message("Loading torrent metadata...")
        self.loading_screen.show()

    def hide_loading_screen(self):
        if self.loading_screen:
            self.loading_screen.hide()    

    def display_torrent_screen(self, client: TorrentClient):
        pass

    def display_download_progress(self, client: TorrentClient):
        while True:
            progress_list = client.get_progress(self.current_torrent)
            self.update_download_progress_signal.emit(progress_list)  # Emit signal for download progress
            time.sleep(1)

    def update_download_progress(self, progress_list: list):
        """Update the download progress."""
        for file_info in progress_list:
            found = False
            for row in range(self.files_model.rowCount()):
                item = self.files_model.item(row, 0)
                if item and item.text() == file_info['filename']:
                    self.files_model.setItem(row, 1, QStandardItem(f"{file_info['totalsize']} MB"))
                    self.files_model.setItem(row, 2, QStandardItem(f"{file_info['remaining']} MB"))
                    progress_bar = self.tableWidgetContent.cellWidget(row, 3)
                    if isinstance(progress_bar, QProgressBar):
                        progress_bar.setValue(int(file_info['progress']))
                    found = True
                    break
            if not found:
                row_pos = self.files_model.rowCount()
                self.files_model.appendRow([
                    QStandardItem(file_info['filename']),
                    QStandardItem(f"{file_info['totalsize']} MB"),
                    QStandardItem(f"{file_info['remaining']} MB"),
                    QProgressBar()
                ])
                progress_bar = self.files_model.item(row_pos, 3)
                progress_bar.setValue(int(file_info['progress']))

    def display_peers(self, client: TorrentClient):
        while True:
            peers = client.get_peers()
            current_peers = {f"{peer[0]}_{peer[2]}" for peer in peers}
            if current_peers != self.previous_peers:
                self.previous_peers = current_peers
                self.update_peers_signal.emit(self.format_peers(peers))
            time.sleep(1)

    def format_peers(self, peers):
        if not peers:
            return 'No peers found...'
        return '\n'.join(f"Peer ID: {peer[0]}, IP: {peer[2]}, Port: {peer[1]}" for peer in peers)

    def update_peers_label(self, text: str):
        """Update the peers label with formatted text."""
        self.label_peers.setText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_amber.xml')
    window.show()
    sys.exit(app.exec())
