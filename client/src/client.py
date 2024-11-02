from queue import Queue
import socket
import time
import bencodepy
import requests
import threading
from .utils import TorrentUtils, MagnetUtils
from .piece_manager import DownloadingFSM, PieceManager
from .peer_connection import PeerConnection


class TorrentClient:
    def __init__(self, ip, port, torrent_file=None, magnet_link=None, download_dir=None, upload_dir=None):
        self.running = True
        self.download_dir = download_dir
        self.ip = ip
        self.port = port
        self.peer_id = TorrentUtils.generate_peer_id()
        # ---------------- Basic peer attrs ----------------
        self.downloading = True
        self.status = 'started'
        self.left = None
        self.downloaded = 0
        self.uploaded = 0
        # ---------------- Process inputs -----------------

        if magnet_link:
            params = MagnetUtils.parse_magnet_link(magnet_link)
            self.info_hash, self.tracker_url, self.display_name, self.metadata = params
        elif torrent_file:
            params = TorrentUtils.parse_torrent_file(torrent_file)
            self.info_hash, self.tracker_url, self.display_name, self.metadata = params
        elif upload_dir:
            params = TorrentUtils.parse_uploaded_torrent(uploader)
            self.init_uploader()

        # ----------------- Server socket -----------------

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"Listening on {self.ip}:{self.port}")

        threading.Thread(target=self.listen_for_peers, daemon=True).start()

        # -------------------------------------------------
        # --------------- Start connections ---------------
        self.interval = None
        self.peer_list = None

        threading.Thread(target=self.send_tracker_request, daemon=True).start()

        # -------------------------------------------------

        # --------------- Start downloading ---------------
        self.piece_manager = PieceManager(peer_list=self.peer_list, metadata=self.metadata)
        self.peer_connections: dict[str, PeerConnection] = dict()
        self.init_connections()

        threading.Thread(target=self.start_downloading, daemon=True).start()
        # -------------------------------------------------

    def init_uploader(self):
        self.downloading = False
        self.status = 'completed'
        self.left = 0
        self.downloaded = self.metadata['info']['length']
        self.uploaded = 0

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
        while self.running:
            params = {
                'ip': self.ip,
                'port': self.port,
                'info_hash': self.info_hash,
                'peer_id': self.peer_id,
                'uploaded': self.uploaded,
                'downloaded': self.downloaded,
                'left': self.left,
                'compact': 1,
                'event': self.status
            }
            if not self.peer_list:
                response = requests.get(self.tracker_url, params=params).content
                response = bencodepy.decode(response)
                print(f"Response from tracker: {response}")

                peers = response[b'peers']
                self.interval = response[b'interval']
                self.peer_list = TorrentUtils.parse_compacted_peer_list(peers)
                print(f"Interval: {self.interval} \nReceived peer list: {self.peer_list}")
            # Wait for the interval before sending another request
            time.sleep(self.interval)

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
        """Start downloading pieces. If metdata is not fully downloaded yet, the thread will be in busy waiting.
        Metadata is requested whenever an extension response is received, so this thread will not handle metadata download.
        """
        while True:
            if not self.piece_manager.is_metadata_complete():
                continue
            if self.piece_manager.is_waiting_for_piece_response():
                continue

            if self.piece_manager.is_piece_request_done():
                for connection in self.peer_connections.values():
                    connection.send_have_message()

            piece_idx, peers = self.piece_manager.find_next_rarest_piece()
            if not piece_idx:       # If no piece is found, all pieces are downloaded
                break
            for id in peers:
                self.peer_connections[id].send_request_message(piece_idx)

            time.sleep(0.2)  # Wait for peers to respond

            unchoked_peers = self.piece_manager.get_unchoked_peers()
            if not unchoked_peers:
                continue

            # Divide piece into blocks and request from peers
            block_requests = TorrentUtils.divide_piece_into_blocks(piece_idx, self.piece_manager.piece_size)
            self.piece_manager.add_requesting_blocks(piece_idx, block_requests)
            # Distribute blocks among unchoked peers
            for i, args in enumerate(block_requests):
                peer = unchoked_peers[i % len(unchoked_peers)]
                connection = self.peer_connections[peer]
                connection.send_request_message(*args)

        # stop all connections and close the server socket, merge all pieces
        self.downloading = False
        self.server_socket.close()
        self.piece_manager.merge_all_pieces(self.download_dir)

        for connection in self.peer_connections.values():
            connection.seeding()


if __name__ == "__main__":
    # Using a .torrent file
    pass
