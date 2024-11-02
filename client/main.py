from PyQt6.QtWidgets import *
from widgets import *
from PyQt6.uic import loadUi
import sys
from src.utils.torrent_utils import decode_bencode
from widgets.add_file_dialog import *
from src import TorrentClient
import threading


TOR_CLIENTS = []


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.setWindowTitle("BitTorrent")

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)
        self.action_Upload_Files.triggered.connect(self.upload_files)

    def upload_files(self):
        # seeder
        dialog = UploadFilesDialog()
        pass

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
            ip, port = "", 0
            client = TorrentClient(ip=ip, port=port, magnet_link=magnet_link)
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
