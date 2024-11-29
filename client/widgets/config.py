from PyQt6.QtCore import QStandardPaths

download_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)


SAVE_DIR_TORRENT = download_path
SAVE_DIR_MAGNET = download_path
SAVE_DIR = download_path
TRACKER_URL = 'http://192.168.1.194:8000/announce'

print(download_path)
