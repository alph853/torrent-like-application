from PyQt6.QtWidgets import *
from widgets import *
from PyQt6.uic import loadUi
import sys
from src.utils.torrent_utils import decode_bencode
from widgets.add_file_dialog import *
from src import TorrentClient


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.setWindowTitle("BitTorrent")

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)

    def add_torrent_file(self):
        
        dialog = AddFileDialogTorrent()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            torrent_file_path = dialog.get_result()
            with open(torrent_file_path, "rb") as torrent_file:
                bencoded_content = torrent_file.read()

            torrent = decode_bencode(bencoded_content)
            print(torrent)
        file_names = [file["path"][0].decode('utf-8') for file in torrent["info"]["files"]]
        config_form = ConfigFormTorrent(display_name=torrent["info"]["name"].decode('utf-8'),file_names=file_names,info = torrent["info"])
        if config_form.exec() == QDialog.DialogCode.Accepted:
            chosen_file = config_form.get_selected_files()[0]
            print("Start the client with selected files", chosen_file)
        client = TorrentClient(torrent_file=torrent,selected_file=chosen_file)



    def add_magnet_link(self):
        dialog = AddFileDialogMagnet()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            magnet_link = dialog.get_result()
            client = TorrentClient(magnet_link=magnet_link)
            # config_form = ConfigForm(display_name=client.display_name,
            #                          file_names=tracker_response['files'], info=tracker_response['info'])

            # if config_form.exec() == QDialog.DialogCode.Accepted:
            #     chosen_files = config_form.get_selected_files()
            #     print("Start the client with selected files", chosen_files)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
