import socket
import time
from PyQt6.QtWidgets import *
from widgets import *
from PyQt6.uic import loadUi
import sys
# from src.utils.torrent_utils import decode_bencode
from widgets.add_file_dialog import *
from src import TorrentClient
import threading

def get_ip_and_port():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]
    return ip, port

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.setWindowTitle("BitTorrent")

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)
        self.actionCreate_Torrent_2.triggered.connect(self.create_torrent)

    def create_torrent(self):
        dialog = CreateTorrentDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            uploader_info = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, uploader_info=uploader_info)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

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
                self.display_torrent_screen(client)
                threading.Thread(target=self.display_download_progress, daemon=True, args=(client, )).start()
                threading.Thread(target=self.display_peers, daemon=True, args=(client, )).start()

    def display_console(self, client: TorrentClient):
        self.console.append(client.get_console_output())
        time.sleep(0.1)

    def display_loading_screen(self):
        pass

    def display_torrent_screen(self, client: TorrentClient):
        pass

    def display_download_progress(self, client: TorrentClient):
        while True:
            progress = client.get_progress()
            time.sleep(0.1)
            pass

    def display_peers(self, client: TorrentClient):
        while True:
            peers = client.get_peers()
            time.sleep(0.1)
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
