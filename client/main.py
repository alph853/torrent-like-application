from PyQt6.QtWidgets import *
from widgets import AddFileDialog, ConfigForm
from PyQt6.uic import loadUi
import sys
from utils import TorrentClient


IP = "123"
PORT = "456"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)
        self.setWindowTitle("BitTorrent")

        self.actionAdd_Torrent_File.triggered.connect(self.add_torrent_file)
        self.actionAdd_Magnet_Link.triggered.connect(self.add_magnet_link)

    def add_torrent_file(self):
        title = "Add Torrent File"
        label = "Enter the path to the torrent file:"
        dialog = AddFileDialog(title, label)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            torrent_file_path = dialog.get_result()

    def add_magnet_link(self):
        title = "Add Magnet Link"
        label = "Enter the magnet link:"
        dialog = AddFileDialog(title, label)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            magnet_link = dialog.get_result()
            client = TorrentClient(IP, PORT, magnet_link=magnet_link)
            tracker_response = client.send_tracker_request(test=True)
            config_form = ConfigForm(display_name=client.display_name,
                                     file_names=tracker_response['files'], info=tracker_response['info'])

            if config_form.exec() == QDialog.DialogCode.Accepted:
                chosen_files = config_form.get_selected_files()
                print("Start the client with selected files", chosen_files)
                client.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
