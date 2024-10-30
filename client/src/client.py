import json
from queue import Queue
import socket
import requests
import os
import threading
from .utils import TorrentUtils, MagnetUtils
from .piece_manager import PieceManager
from .peer_connection import PeerConnection


class TorrentClient:
    def __init__(self, ip, port, torrent_file=None, magnet_link=None):
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file

        self.ip = ip
        self.port = port
        self.status = 'started'
        self.peer_id = TorrentUtils.generate_peer_id()
        self.left = None
        self.downloaded = 0
        self.uploaded = 0

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"Listening on {self.ip}:{self.port}")

        # Start listening for incoming peer connections
        threading.Thread(target=self.listen_for_peers, daemon=True).start()

        if magnet_link:
            params = MagnetUtils.parse_magnet_link(magnet_link)
        elif torrent_file:
            params = TorrentUtils.parse_torrent_file(torrent_file)
        self.info_hash, self.tracker_url, self.display_name = params

        self.interval: float
        self.peer_list: list[dict]
        self.send_tracker_request()

        self.piece_manager = PieceManager(self.peer_list)
        self.peer_connections: dict[str, PeerConnection] = dict()
        self.init_connections()

    def listen_for_peers(self):
        """Listen for incoming peer connections and handle each new peer in a separate thread."""
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"New connection from {client_address}")
            threading.Thread(target=self.handle_peer_connection, args=(
                client_socket, client_address), daemon=True).start()

    def handle_peer_connection(self, client_socket, client_address):
        """Handle communication with a newly connected peer."""
        try:
            connection = PeerConnection(client_socket, self.info_hash, self.piece_manager, self.peer_id)
            self.peer_connections[client_address] = connection
        except Exception as e:
            print(f"Error handling connection from {client_address}: {e}")
        finally:
            client_socket.close()


    def send_tracker_request(self) -> tuple:
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
        response = requests.get(self.tracker_url, params=params)
        peers = response.get['peers']
        self.interval = response.get('interval', 0)
        self.peer_list = TorrentUtils.parse_compacted_peer_list(peers)

    def init_connections(self):
        """Initiate connections to all peers in the peer list."""
        for target_peer in self.peer_list:
            thread = threading.Thread(target=self.connect_to_peer, args=(target_peer,))
            thread.start()

    def connect_to_peer(self, target_peer: dict):
        connection = PeerConnection(target_peer, self.info_hash, self.piece_manager, self.peer_id)
        self.peer_connections[target_peer['id']] = connection


if __name__ == "__main__":
    # Using a .torrent file
    pass
