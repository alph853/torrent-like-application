import json
from queue import Queue
import socket
import requests
import os
import threading
from .utils import TorrentUtils
from .piece_manager import PieceManager
from .peer_connection import PeerConnection


class TorrentClient:
    def __init__(self, torrent_file=None, magnet_link=None):
        self.magnet_link = magnet_link
        self.torrent_file = torrent_file
        self.status = 'started'
        self.peer_id = TorrentUtils.generate_peer_id()
        self.left = None
        self.downloaded = 0
        self.uploaded = 0

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.peer_connections: dict[str, PeerConnection] = {}

        if magnet_link:
            params = TorrentUtils.parse_magnet_link(magnet_link)
        elif torrent_file: 
            params = TorrentUtils.parse_torrent_file(torrent_file)
            
        self.info_hash = params['info_hash']
        self.tracker_url = params['tracker_url']
        self.display_name = params['display_name']
        self.interval, peer_list = self.send_tracker_request()

        self.piece_manager = PieceManager(peer_list)
        
     
        

    def send_tracker_request(self) -> tuple:
        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'uploaded': 0,
            'downloaded': self.downloaded,
            'left': self.left,
            'compact': 1,
            'event': self.status
        }
        response = requests.get(self.tracker_url, params=params)
        interval = response.get('interval', 0)
        peers = response.get['peers']
        peer_list = TorrentUtils.parse_compacted_peer_list(peers)
        return interval, peer_list

    def init_connections(self):
        """Initiate connections to all peers in the peer list."""
        for peer in self.peer_list:
            thread = threading.Thread(target=self.connect_to_peer, args=(peer,))
            thread.start()

    def connect_to_peer(self, peer):
        connection = PeerConnection(peer, self.info_hash, self.peer_id)
        self.peer_connections[peer['ip']] = connection

    def download_file_from_peers(self):
        """Download multiple files from multiple peers using multithreading."""
        # Start a thread for each file
        threads = []
        for file_info in self.files:
            thread = threading.Thread(target=self.download_single_file, args=(file_info,))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    # Using a .torrent file
    pass
