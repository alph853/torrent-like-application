import socket
import time
from src import TorrentClient


def get_ip_and_port():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((ip, 0))
        port = sock.getsockname()[1]
    return ip, port


uploader_info = {
    'tracker_url': 'http://localhost:8000/announce',
    'save_torrent_dir': 'D:/STUDY/Semester241/MMT',
    'upload_dir': 'D:/STUDY/Semester241/MMT/slide'
}

ip, port = get_ip_and_port()
uploader = TorrentClient(ip=ip, port=port, uploader_info=uploader_info, cli=True)

while True:
    time.sleep(100)
