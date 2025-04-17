from PyQt6.QtCore import QStandardPaths

download_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)


SAVE_DIR_TORRENT = download_path
SAVE_DIR_MAGNET = download_path
SAVE_DIR = download_path
TRACKER_URL = 'https://10diembtl.ngrok.app/announce'


# TRACKER_URL = 'http://10.128.49.47:8000/announce'
