import socket
import time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QFont, QStandardItem, QStandardItemModel
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QTimer
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
    update_download_torrent_signal = pyqtSignal(list)
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

        self.tabWidget = self.findChild(QTabWidget, 'tabWidget')
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        self.current_tab_idx = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.display_client_UI)
        self.timer.start(250)
        self.display_functions = [self.display_console, self.display_peers, self.display_download_progress]
        self.previous_torrent_list = []
        self.previous_id_progress = -1
        self.previous_id_console = -1
        self.previous_download_progress = []

    def start_torrent_client(self, dialog_class):
        dialog = dialog_class()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            threading.Thread(target=self.init_client, daemon=True, kwargs=(
                {**get_ip_and_port(), **dialog.get_result()})).start()

    def init_client(self, **kwargs):
        client = TorrentClient(**kwargs)
        TORRENT_CLIENT_LIST.append(client)

        while True:
            time.sleep(1000)

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
        self.files_model.removeRows(0, self.files_model.rowCount())

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
        # for client in TORRENT_CLIENT_LIST:
        #     if not client.is_metadata_complete():
        #         self.display_loading_screen()
        #         return

        # self.hide_loading_screen()
        if TORRENT_CLIENT_LIST:
            client = TORRENT_CLIENT_LIST[GLOBAL_ID]
            self.display_functions[self.current_tab_idx](client)
            torrent_list = [client.get_self_torrent_info() for client in TORRENT_CLIENT_LIST]
            self.update_torrent_progress(torrent_list)

    def display_console(self, client):
        if self.previous_id_console != GLOBAL_ID:
            self.label_general.setText(client.get_full_string_console())
        else:
            text = client.get_console_output()
            if text:
                self.label_general.append(text)
        self.previous_id_console = GLOBAL_ID

    def display_peers(self, client):
        peers = client.get_peers()
        peer_text = '\n'.join(f"IP: {peer[0]}, Port: {peer[1]}" for peer in peers) if peers else 'No peers found...'
        self.label_peers.setText(peer_text)

    def display_download_progress(self, client):
        progress_list = client.get_progress()

        if self.previous_id_progress != GLOBAL_ID:
            self.files_model.removeRows(0, self.files_model.rowCount())
            for file_info in progress_list:
                self.files_model.appendRow([
                    QStandardItem(file_info['filename']),
                    QStandardItem(f"{file_info['totalsize']} B"),
                    QStandardItem(f"{file_info['remaining']} B"),
                    QStandardItem(str(int(round(file_info['progress'], 2)*100)))  # Progress as string
                ])
        else:
            for row, (file_info, previous_info) in enumerate(zip(progress_list, self.previous_download_progress)):
                if previous_info != file_info:
                    self.files_model.setItem(row, 2, QStandardItem(f"{file_info['remaining']} B"))
                    self.files_model.setItem(row, 3, QStandardItem(
                        str(int(round(file_info['progress'], 2)*100))))  # Progress as string
        self.previous_download_progress = progress_list
        self.previous_id_progress = GLOBAL_ID

    def update_torrent_progress(self, torrent_list: list):
        if not torrent_list:
            return

        if len(torrent_list) == len(self.previous_torrent_list):
            for row, file_info, previous_info in zip(range(self.torrent_model.rowCount()), torrent_list, self.previous_torrent_list):
                if previous_info != file_info:
                    self.torrent_model.setItem(row, 2, QStandardItem(f"{file_info['status']}"))
                    self.torrent_model.setItem(row, 5, QStandardItem(f"{file_info['upspeed']} B/s"))
                    self.torrent_model.setItem(row, 6, QStandardItem(f"{file_info['downspeed']} B/s"))
                    self.torrent_model.setItem(row, 1, QStandardItem(
                        # Progress as string
                        str(int(round((file_info['downloaded'])/(file_info['downloaded']+file_info['left']), 2)*100))))
        else:
            for file_info in torrent_list[len(self.previous_torrent_list):]:
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
        self.previous_torrent_list = torrent_list

    def display_loading_screen(self):
        if not self.loading_screen:
            self.loading_screen = LoadingScreen(self)
        self.loading_screen.set_message("Loading torrent metadata...")
        self.loading_screen.show()

    def hide_loading_screen(self):
        if self.loading_screen:
            self.loading_screen.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_amber.xml')
    window.show()
    sys.exit(app.exec())
