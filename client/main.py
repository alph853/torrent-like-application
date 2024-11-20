import socket
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QFont, QStandardItem, QStandardItemModel
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt6.uic import loadUi
import sys
from widgets.add_file_dialog import *
from src import TorrentClient
import threading
from qt_material import apply_stylesheet


TORRENT_CLIENT_LIST: list[TorrentClient] = []
GLOBAL_ID = 0


def get_ip_and_port():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]

    return {
        'ip': ip,
        'port': port
    }


class MainWindow(QMainWindow):
    update_peers_signal = pyqtSignal(str)
    update_console_signal = pyqtSignal(str)
    update_download_progress_signal = pyqtSignal(list)
    update_download_torrent_signal = pyqtSignal(list)
    previous_peers = None

    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), "main.ui")
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        loadUi(ui_path, self)
        self.setWindowIcon(QIcon(logo_path))
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
        self.label_general = self.findChild(QTextEdit, 'label_general')
        self.label_general.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.update_peers_signal.connect(self.update_peers_label)
        self.update_console_signal.connect(self.update_general_label)
        self.update_download_progress_signal.connect(self.update_download_progress)
        self.update_download_torrent_signal.connect(self.update_torrent_progress)

        self.tabWidget = self.findChild(QTabWidget, 'tabWidget')
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        threading.Thread(target=self.display_torrent_table, daemon=True).start()
        threading.Thread(target=self.display_client_UI, daemon=True).start()

        self.display_thread_functions = [self.display_console, self.display_peers, self.display_download_progress]
        self.previous_tab_idx = 0
        self.current_tab_idx = 0

    def start_torrent_client(self, dialog_class):
        dialog = dialog_class()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            threading.Thread(target=self.init_client, daemon=True, kwargs=(
                {**get_ip_and_port(), **dialog.get_result()})).start()

    def init_client(self, **kwargs):
        client = TorrentClient(**kwargs)
        TORRENT_CLIENT_LIST.append(client)

        while True:
            continue

    def create_torrent(self):
        self.start_torrent_client(CreateTorrentDialog)

    def add_torrent_file(self):
        self.start_torrent_client(AddFileDialogTorrent)

    def add_magnet_link(self):
        self.start_torrent_client(AddFileDialogMagnet)

    def setup_torrent_table(self):
        self.torrent_model.setHorizontalHeaderLabels(
            ["Torrent", "Progress", "Status", "Seeds", "Peers", "UpSpeed", "DownSpeed"])
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
        delegate = ProgressBarDelegate()
        self.tableWidgetContent.setItemDelegateForColumn(3, delegate)

    def on_table_row_clicked(self, index: QModelIndex):
        global GLOBAL_ID
        GLOBAL_ID = index.row()

    def limit_column_width(self, logicalIndex, oldSize, newSize):
        total_width = sum(self.tableView.horizontalHeader().sectionSize(i)
                          for i in range(self.tableView.model().columnCount()))
        max_width = self.tableView.width() - self.tableView.verticalHeader().width()

        if total_width > max_width:
            excess_width = total_width - max_width
            for i in range(self.tableView.model().columnCount()):
                if i != logicalIndex:
                    continue

                new_size = max(0, newSize - excess_width)
                self.tableView.horizontalHeader().resizeSection(i, new_size)

    def on_tab_changed(self, index):
        self.current_tab_idx = index

    def display_client_UI(self):
        """Display the client in the UI."""
        active_thread = None
        while True:
            continue_flag = False
            for client in TORRENT_CLIENT_LIST:
                if not client.is_metadata_complete():
                    self.display_loading_screen()
                    continue_flag = True
                    break
            if continue_flag:
                time.sleep(1)
                continue

            self.hide_loading_screen()
            if not TORRENT_CLIENT_LIST:
                time.sleep(1)
                continue

            if self.current_tab_idx != self.previous_tab_idx:
                client = TORRENT_CLIENT_LIST[GLOBAL_ID]
                if active_thread:
                    active_thread.join()
                active_thread = threading.Thread(
                    target=self.display_thread_functions[self.current_tab_idx], daemon=True, args=(client, ))
                active_thread.start()
                self.previous_tab_idx = self.current_tab_idx
            time.sleep(1)

    def display_loading_screen(self):
        if not self.loading_screen:
            self.loading_screen = LoadingScreen(self)
        self.loading_screen.set_message("Loading torrent metadata...")
        self.loading_screen.show()

    def hide_loading_screen(self):
        if self.loading_screen:
            self.loading_screen.hide()

    def display_console(self, client: TorrentClient):
        while self.current_tab_idx == 0:
            self.update_console_signal.emit(client.get_console_output())
            time.sleep(1)

    def update_general_label(self, text: str):
        """Update the peers label with formatted text."""
        if self.label_general.toPlainText() != text:
            self.label_general.setText(text)

    def display_download_progress(self, client: TorrentClient):
        while self.current_tab_idx == 2:
            progress_list = client.get_progress()
            self.update_download_progress_signal.emit(progress_list)
            time.sleep(1)

    def display_torrent_table(self):
        while True:
            torrent_list = [client.get_self_torrent_info() for client in TORRENT_CLIENT_LIST]
            self.update_download_torrent_signal.emit(torrent_list)
            time.sleep(1)

    def update_download_progress(self, progress_list: list):
        """Update the download progress."""
        for file_info in progress_list:
            found = False
            for row in range(self.files_model.rowCount()):
                item = self.files_model.item(row, 0)
                if item and item.text() == file_info['filename']:
                    self.files_model.setItem(row, 1, QStandardItem(f"{file_info['totalsize']} B"))
                    self.files_model.setItem(row, 2, QStandardItem(f"{file_info['remaining']} B"))
                    self.files_model.setItem(row, 3, QStandardItem(
                        str(int(round(file_info['progress'], 2)*100))))  # Progress as string
                    found = True
                    break
            if not found:
                self.files_model.appendRow([
                    QStandardItem(file_info['filename']),
                    QStandardItem(f"{file_info['totalsize']} B"),
                    QStandardItem(f"{file_info['remaining']} B"),
                    QStandardItem(str(int(round(file_info['progress'], 2)*100)))  # Progress as string
                ])

    def update_torrent_progress(self, progress_list: list):
        for file_info in progress_list:
            found = False
            for row in range(self.torrent_model.rowCount()):
                item = self.torrent_model.item(row, 0)
                if item and item.text() == file_info['name']:
                    self.torrent_model.setItem(row, 2, QStandardItem(f"{file_info['status']}"))
                    self.torrent_model.setItem(row, 5, QStandardItem(f"{file_info['upspeed']} B/s"))
                    self.torrent_model.setItem(row, 6, QStandardItem(f"{file_info['downspeed']} B/s"))
                    self.torrent_model.setItem(row, 1, QStandardItem(
                        # Progress as string
                        str(int(round((file_info['downloaded'])/(file_info['downloaded']+file_info['left']), 2)*100))))
                    found = True
                    break
            if not found:
                self.torrent_model.appendRow([
                    QStandardItem(file_info['name']),
                    QStandardItem(str(int(round((file_info['downloaded']) /
                                  (file_info['downloaded']+file_info['left']), 2)*100))),
                    QStandardItem(file_info['status']),
                    QStandardItem(f"{file_info['seeds']}"),
                    QStandardItem(f"{file_info['peers']}"),
                    QStandardItem(f"{file_info['upspeed']}"),
                    QStandardItem(f"{file_info['downspeed']}"),
                ])

    def display_peers(self, client: TorrentClient):
        while self.current_tab_idx == 1:
            peers = client.get_peers()
            current_peers = {f"{peer[0]}, {peer[1]}" for peer in peers}
            if current_peers != self.previous_peers:
                self.previous_peers = current_peers
                self.update_peers_signal.emit(self.format_peers(peers))
            time.sleep(1)

    def format_peers(self, peers):
        if not peers:
            return 'No peers found...'
        return '\n'.join(f"IP: {peer[0]}, Port: {peer[1]}" for peer in peers)

    def update_peers_label(self, text: str):
        """Update the peers label with formatted text."""
        self.label_peers.setText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_amber.xml')
    window.show()
    sys.exit(app.exec())
