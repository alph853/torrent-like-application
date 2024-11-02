import json
from queue import Queue
import socket
import bencodepy
import requests
import os
import threading
from .utils import TorrentUtils, MagnetUtils
from .piece_manager import PieceManager
from .peer_connection import PeerConnection


class TorrentClient:
    def __init__(self, ip, port, torrent_file=None, magnet_link=None):
        # ---------------- Basic peer attrs ----------------
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file
        self.ip = ip
        self.port = port
        self.status = 'started'
        self.peer_id = TorrentUtils.generate_peer_id()
        self.left = None
        self.downloaded = 0
        self.uploaded = 0
        # ---------------- Process inputs -----------------
        if magnet_link:
            params = MagnetUtils.parse_magnet_link(magnet_link)
        elif torrent_file:
            params = TorrentUtils.parse_torrent_file(torrent_file)
        self.info_hash, self.tracker_url, self.display_name = params
        # ----------------- Server socket -----------------
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"Listening on {self.ip}:{self.port}")

        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        # -------------------------------------------------

        # --------------- Start connections ---------------
        self.interval: float
        self.peer_list: list[dict]
        self.send_tracker_request()

        self.piece_manager = PieceManager(self.peer_list)
        self.peer_connections: dict[str, PeerConnection] = dict()
        self.init_connections()
        # -------------------------------------------------

        # --------------- Start downloading ---------------
        self.selected_files = None

        # -------------------------------------------------

    # -------------------------------------------------
    # -------------------------------------------------
    # ----------------- Server socket -----------------
    def listen_for_peers(self):
        """Listen for incoming peer connections and handle each new peer in a separate thread."""
        while True:
            sock, addr = self.server_socket.accept()
            print(f"New connection from {addr}")
            threading.Thread(target=self.handle_peer_connection, args=(
                sock, addr), daemon=True).start()

    def handle_peer_connection(self, sock, addr):
        """Handle communication with a newly connected peer."""
        ip, port = addr
        target_peer = {
            'id': TorrentUtils.generate_peer_id(ip, port),
            'ip': ip,
            'port': port
        }
        try:
            connection = PeerConnection(sock, target_peer, self.piece_manager)
            connection.handshake_response(self.info_hash, self.peer_id, outgoing=False)
            self.peer_connections[addr] = connection
            self.piece_manager.add_peer(addr)
        except Exception as e:
            print(f"Error handling connection from {addr}: {e}")
    # -------------------------------------------------
    # -------------------------------------------------

    def send_tracker_request(self):
        # Send a request to the tracker, initialize peer_list and interval
        params = {
            'ip': self.ip,
            'port': self.port,
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'uploaded': 0,
            'downloaded': self.downloaded,
            'left': self.left,
            'compact': 1,
            'event': self.status
        }
        # localhost/announce
        response = requests.get(self.tracker_url, params=params).content
        response = bencodepy.decode(response)
        peers = response.get[b'peers']
        self.interval = response.get(b'interval', 0)
        self.peer_list = TorrentUtils.parse_compacted_peer_list(peers)
        print(f"Interval: {self.interval} \nReceived peer list: {self.peer_list}")
    # -------------------------------------------------
    # -------------------------------------------------
    def init_connections(self):
        """Initiate connections to all peers in the peer list."""
        for target_peer in self.peer_list:
            thread = threading.Thread(target=self.connect_to_peer, args=(target_peer,))
            thread.start()

    def connect_to_peer(self, target_peer: dict):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            connection = PeerConnection(sock, target_peer, self.piece_manager)
            connection.send_handshake_message(self.info_hash, self.peer_id, outgoing=True)
            self.peer_connections[target_peer['id']] = connection
        except Exception as e:
            print(f"Failed to connect to peer {target_peer['id']}: {e}")
            return
    # -------------------------------------------------
    # -------------------------------------------------

    def is_metadata_complete(self):
        return self.piece_manager.is_metadata_complete()

    def start_downloading(self):
        while not self.piece_manager.is_download_complete():
            piece_idx, peers = self.piece_manager.find_rarest()
            for peer in peers:
                connection = self.peer_connections[peer['id']]
                connection.send_interest_message(piece_idx)



if __name__ == "__main__":
    # Using a .torrent file
    pass
