import socket
from PyQt6.QtWidgets import *
from widgets import *
from PyQt6.uic import loadUi
import sys
# from src.utils.torrent_utils import decode_bencode
from widgets.add_file_dialog import *
from src import TorrentClient
import threading

TOR_CLIENTS = []


def get_ip_and_port():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]
    print(f"IP: {ip}, Assigned Port: {port}")
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
            TOR_CLIENTS.append(client)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()


    def add_torrent_file(self):
        dialog = AddFileDialogTorrent()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            torrent_file_path, download_dir = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, torrent_file=torrent_file_path, download_dir=download_dir)
            TOR_CLIENTS.append(client)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def add_magnet_link(self):
        dialog = AddFileDialogMagnet()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            magnet_link, download_dir = dialog.get_result()
            ip, port = get_ip_and_port()
            client = TorrentClient(ip=ip, port=port, magnet_link=magnet_link, download_dir=download_dir)
            TOR_CLIENTS.append(client)
            threading.Thread(target=self.display_client_UI, daemon=True, args=(client, )).start()

    def display_client_UI(self, client):
        """Display the client in the UI."""
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
