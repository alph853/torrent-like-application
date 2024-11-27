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


torrent_file = "D:\STUDY\Semester241\MMT\slide.torrent"

ip, port = get_ip_and_port()
torrent_client = TorrentClient(ip=ip, port=port, torrent_file=torrent_file,
                               download_dir='D:\STUDY\Semester241\MMT\ASM_MMT\\asm1\\ ', cli=True)

while True:
    time.sleep(100)
