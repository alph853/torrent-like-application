import json
from queue import Queue
import socket
import time
import bencodepy
import requests
import threading
from .utils import TorrentUtils, MagnetUtils, INIT_STRING
from .piece_manager import DownloadingFSM, PieceManager
from .peer_connection import PeerConnection

LOCK = threading.Lock()

class TorrentClient:

    def __init__(self, ip, port, torrent_file=None, magnet_link=None,
                 download_dir=None, uploader_info: dict = None, cli=False):
        self.running = True
        self.ip = ip
        self.port = port
        self.peer_id = TorrentUtils.generate_peer_id()
        # ---------------- Basic peer attrs ----------------
        self.downloading = True
        self.status = 'started'
        self.left = None
        self.downloaded = 0
        self.uploaded = 0
        self.download_dir = download_dir
        self.send_to_console = INIT_STRING
        self.full_string_log = INIT_STRING
        # ---------------- Process inputs -----------------

        if magnet_link:
            params = MagnetUtils.parse_magnet_link(magnet_link)
            self.init_downloader(params)
        elif torrent_file:
            params = TorrentUtils.parse_torrent_file(torrent_file)
            self.init_downloader(params)
        elif uploader_info:
            params = TorrentUtils.parse_uploaded_torrent(uploader_info)
            self.init_uploader(params)

        # ----------------- Server socket -----------------
        threading.Thread(target=self.listen_for_connections_ipv4, daemon=True).start()
        threading.Thread(target=self.listen_for_connections_ipv6, daemon=True).start()

        # -------------------------------------------------
        # --------------- Start connections ---------------
        self.peer_list, self.peer6_list, self.interval = self.send_tracker_request()

        threading.Thread(target=self.send_tracker_request_periodic, daemon=True).start()

        # -------------------------------------------------
        # ---------------- Start Torrenting ---------------
        self.peer_connections: dict[str, PeerConnection] = dict()
        self.piece_manager = PieceManager(peer_list=self.peer_list,
                                          metadata=self.metadata, pieces=self.pieces, client=self)

        if cli:
            threading.Thread(target=self.periodic_update_console, daemon=True).start()

        self.connected_to_peers = False
        self.init_connections()

        if not uploader_info:
            while not self.connected_to_peers:
                time.sleep(0.5)
            threading.Thread(target=self.start_downloading, daemon=True).start()
        else:
            threading.Thread(target=self.start_uploading_only, daemon=True).start()

        # -------------------------------------------------

    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------

    def init_downloader(self, params):
        self.info_hash, self.tracker_url, self.display_name, self.metadata = params
        self.pieces = dict()
        self.log(f"Downloading Torrent '{self.display_name}'  ...\n")

    def init_uploader(self, params):
        self.info_hash, self.tracker_url, self.display_name, self.metadata, pieces_dict = params

        self.downloading = False
        self.left = 0
        self.downloaded = sum([file['length'] for file in self.metadata['files']])
        self.uploaded = 0

        self.pieces = pieces_dict
        self.log(f"Seeding Torrent '{self.display_name}'  ...\n")

    # -------------------------------------------------
    # ----------------- Server socket -----------------

    def listen_for_connections_ipv4(self):
        """Listens for incoming IPv4 connections and handles them.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', self.port))
        server_socket.listen()

        while True:
            try:
                conn, addr = server_socket.accept()
                ip, port = addr
                threading.Thread(target=self.handle_peer_connection, args=(conn, ip, port), daemon=True).start()
            except Exception as e:
                self.log(f"Error accepting IPv4 connection: {e}\n")

    def listen_for_connections_ipv6(self):
        """Listens for incoming IPv6 connections and handles them.
        """
        server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        server_socket.bind(('', self.port))
        server_socket.listen()

        while True:
            try:
                conn, addr = server_socket.accept()
                ip, port, _, _ = addr
                threading.Thread(target=self.handle_peer_connection, args=(conn, ip, port), daemon=True).start()
            except Exception as e:
                self.log(f"Error accepting IPv6 connection: {e}\n")

    def handle_peer_connection(self, conn, ip, port):
        """Handle communication with a newly connected peer."""
        target_peer = {
            'id': TorrentUtils.generate_peer_id(ip, port),
            'ip': ip,
            'port': port
        }
        addr = f"{ip} : {port}"
        self.log(f"New connection from {addr}\n")
        try:
            connection = PeerConnection(self.info_hash, self.peer_id, conn,
                                        target_peer, self.piece_manager, outgoing=False, client=self)
            self.peer_connections[target_peer['id']] = connection
            self.piece_manager.add_peer(target_peer['id'])
            self.log(f"Successfully add connection to peer {target_peer['ip']}, {target_peer['port']}\n")
        except Exception as e:
            self.log(f"Error handling connection from {addr}: {e}\n")

    # -------------------- Connect --------------------
    # -------------------------------------------------

    def init_connections(self):
        """Initiate connections to all peers in the peer list."""
        for target_peer in self.peer_list:
            threading.Thread(target=self.connect_to_peer, args=(target_peer, socket.AF_INET)).start()
        for target_peer in self.peer6_list:
            threading.Thread(target=self.connect_to_peer, args=(target_peer, socket.AF_INET6)).start()

    def connect_to_peer(self, target_peer: dict, family):
        self.log(f"Connecting to peer {target_peer['ip']}, {target_peer['port']}\n")
        sock = socket.socket(family, socket.SOCK_STREAM)
        addr = (target_peer['ip'], target_peer['port'])
        try:
            sock.connect(addr)
            connection = PeerConnection(self.info_hash, self.peer_id, sock,
                                        target_peer, self.piece_manager, outgoing=True, client=self)
            self.peer_connections[target_peer['id']] = connection
            self.log(f"Successfully connect to peer {addr}\n")
            self.connected_to_peers = True
        except Exception as e:
            self.log(f"Failed to connect to peer {addr}: {e}\n")

    def remove_connection(self, id):
        # self.peer_connections.pop(id)
        # self.piece_manager.remove_peer(id)
        pass
    # -------------------------------------------------
    # -------------------------------------------------

    def send_tracker_request(self):
        # Send a request to the tracker, initialize peer_list and interval
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
        response = requests.get(self.tracker_url, params=params).content
        response = bencodepy.decode(response)
        peers = response[b'peers']
        peers6 = response[b'peers6']
        interval = response[b'interval']
        peer_list, peer6_list = TorrentUtils.parse_compacted_peer_list(peers, peers6)
        return peer_list, peer6_list, interval

    def send_tracker_request_periodic(self):
        # Send a request to the tracker, initialize peer_list and interval
        pass

    # ------------------ UI handling ------------------
    # -------------------------------------------------

    def log(self, string):
        LOCK.acquire()
        self.send_to_console += string
        self.full_string_log += string
        LOCK.release()

    def get_full_string_console(self):
        LOCK.acquire()
        self.send_to_console = ""
        LOCK.release()
        return self.full_string_log

    def get_console_output(self):
        LOCK.acquire()
        string = self.send_to_console
        self.send_to_console = ""
        LOCK.release()
        return string

    def is_metadata_complete(self):
        return self.piece_manager.is_metadata_complete()

    def get_progress(self) -> list[dict[str, int]]:
        """Get the progress of the download in percentage."""
        return self.piece_manager.get_progress()

    def get_peers(self, id_list=None) -> list[tuple[str, int]]:
        if id_list is not None:
            return [(c.ip, c.port) for c in self.peer_connections.values() if c.id in id_list]
        return [(c.ip, c.port) for c in self.peer_connections.values()]

    def get_self_torrent_info(self):
        seeds = len(self.piece_manager.not_interest_peers)
        if not self.downloading:
            seeds += 1
        peers = len(self.peer_connections) + 1
        return {
            'name': self.piece_manager.metadata['name'],
            'status': self.status,
            'downloaded': self.piece_manager.downloaded,
            'uploaded': self.piece_manager.uploaded,
            'downspeed': self.piece_manager.dl_speed,
            'upspeed': self.piece_manager.up_speed,
            'left': self.piece_manager.left,
            'seeds': seeds,
            'peers': peers,
        }

    def pause(self):
        self.prev_status = self.status
        self.status = 'paused'
        self.piece_manager.pause()

    def cont(self):
        self.status = self.prev_status

    # -------------------------------------------------
    # -------------------------------------------------

    def start_downloading(self):
        """Start downloading pieces. If metdata is not fully downloaded yet, the thread will be in busy waiting.
        Tthis thread will not handle metadata download.
        """
        while not self.is_metadata_complete():
            self.log("Waiting for metadata...\n")
            time.sleep(2)

        self.log("\nMetadata downloaded!\n\n")

        success_get_unchoked_peers = False
        while not self.piece_manager.is_done_downloading():
            if self.status == 'paused':
                continue

            # (2) Waitng for piece response
            if self.piece_manager.is_waiting_for_piece_response():
                time.sleep(0.05)
                continue

            # (3) Check if a piece is downloaded
            piece = self.piece_manager.is_piece_request_done()
            if piece is not None:
                self.log(f"\nPiece {piece} downloaded!\n")
                for connection in self.peer_connections.values():
                    connection.send_have_message(piece)
                success_get_unchoked_peers = False
                continue

            # (1) Initiate a new piece (if begin or no piece is being downloaded or no unchoked peer)
            if not success_get_unchoked_peers:
                piece_idx, peers = self.piece_manager.find_next_rarest_piece()
                if piece_idx is None:       # If no piece is found, all pieces are downloaded
                    self.log(f'\nn{'-'*40}\nAll pieces has been downloaded!\n{"-"*40}\n')
                    break
                for id in peers:
                    self.peer_connections[id].send_interest_message()

                time.sleep(0.05)  # Wait for peers to respond

                unchoked_peers = self.piece_manager.get_unchoked_peers()
                if not unchoked_peers:
                    self.log("Trying to get unchoked peers...\n")
                    time.sleep(1)
                    continue
                success_get_unchoked_peers = True

                # Divide piece into blocks and request from peers
                block_requests = TorrentUtils.divide_piece_into_blocks(
                    piece_idx, self.piece_manager.piece_size, self.piece_manager.block_size)
                self.piece_manager.add_requesting_blocks(piece_idx, block_requests)
                self.log(f"\nREQUESTING PIECE {piece_idx} ...\n\n")
                # Distribute blocks among unchoked peers
                for i, args in enumerate(block_requests):
                    peer = unchoked_peers[i % len(unchoked_peers)]
                    self.peer_connections[peer].send_request_message(*args)
                    ip = self.peer_connections[peer].ip
                    port = self.peer_connections[peer].port
                    self.log(f"Requesting block {args} to peer {ip}, {port} ...\n")

        self.log(f"\n{'-'*40}\n{'\t\tDownload complete!!\n'*3}\n{'-'*40}\n{'-'*40}\n")
        self.status = 'completed'
        self.downloading = False
        self.piece_manager.merge_all_pieces(self.download_dir)
        threading.Thread(target=self.start_uploading_only, daemon=True).start()

    def start_uploading_only(self):
        """Start seeding the torrent."""
        for connection in self.peer_connections.values():
            connection.seeding()

    def periodic_update_console(self):
        threading.Thread(target=self.print_progress_periodically, daemon=True).start()
        while True:
            print(self.get_console_output(), end="")

    def print_progress_periodically(self):
        while True:
            # progress = self.get_progress()
            # if progress:
            #     print(json.dumps(progress, indent=2))
            time.sleep(10)
