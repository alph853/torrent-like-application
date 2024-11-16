import base64
import json
import os
from queue import Queue
from collections import Counter
import random
import threading
import time
import bencodepy

from .utils import TorrentUtils, MagnetUtils

lock = threading.Lock()


class DownloadingFSM(enumerate):
    META_DOWN, PIECE_FIND, PIECE_REQ, PIECE_REQ_DONE, DOWN_DONE, SEEDING = range(6)

class PieceManager:
    def __init__(self, peer_list, metadata: dict, pieces: dict, client, piece_size=512*1024, block_size=64*1024, num_unchoked=4):
        self.piece_size = piece_size
        self.block_size = block_size
        self.metadata = metadata
        self.num_unchoked = num_unchoked
        self.peer_upload = {peer['id']: 0 for peer in peer_list}
        self.client = client
        self.not_interest_peers = []
        self.top_uploaders = []
        self.optimistic_unchoked_peer = None
        self.unchoked_peers = []

        if metadata:
            self.metadata_pieces, self.metadata_size = self.split_metadata(metadata, piece_size)
            self.metadata_piece_count = self.metadata_size // piece_size + (1 if self.metadata_size % piece_size else 0)
            self.number_of_pieces = len(self.metadata['pieces'])//20
            self.piece_counter = {i: 0 for i in range(self.number_of_pieces)}
            if pieces:
                self.state = DownloadingFSM.SEEDING
            else:
                self.state = DownloadingFSM.PIECE_FIND
            self.peer_bitfields = {peer['id']: [0] * self.number_of_pieces for peer in peer_list}
            self.init_file_manager()
            threading.Thread(target=self.calculating_top_uploaders, daemon=True).start()
        else:
            self.state = DownloadingFSM.META_DOWN
            self.needed_metadata_pieces = None
            self.metadata_ongoing_requests = None

            self.metadata_pieces = dict()
            self.metadata_size = None
            self.metadata_piece_count = None
            self.number_of_pieces = None
            self.piece_counter = dict()             # Counter of pieces that held by the client
            self.peer_bitfields = {peer['id']: [] for peer in peer_list}

        self.pieces = pieces                    # Pieces the client holds
        self.requesting_blocks = dict()
        self.requesting_piece = None
        self.number_of_blocks = -1
        self.block_request_complete = None

    def is_done_downloading(self):
        # self.print_self_info()
        return self.state in (DownloadingFSM.DOWN_DONE, DownloadingFSM.SEEDING)

    def is_seeding(self):
        return self.state == DownloadingFSM.SEEDING

    def split_metadata(self, metadata: dict, piece_size) -> tuple[dict, int]:
        metadata = bencodepy.encode(metadata)
        metadata_size = len(metadata)
        metadata_pieces = dict()
        for i in range(0, metadata_size, piece_size):
            metadata_pieces[i] = metadata[i:i + piece_size]
        return metadata_pieces, metadata_size

    def is_metadata_complete(self):
        return self.state != DownloadingFSM.META_DOWN

    def get_metadata_size(self):
        return self.metadata_size

    def set_metadata_size(self, size):
        if size is None:
            return None
        self.metadata_size = size
        self.metadata_piece_count = size // self.piece_size + (1 if size % self.piece_size else 0)

        self.needed_metadata_pieces = [True] * self.metadata_piece_count
        self.metadata_ongoing_requests = [False] * self.metadata_piece_count

    def set_metadata_piece(self, piece_index, metadata_piece):
        self.metadata_pieces[piece_index] = metadata_piece
        self.needed_metadata_pieces[piece_index] = False

    def get_next_metadata_piece(self) -> int | None:
        """Get the next metadata piece index to request from a peer. Return None means all pieces are downloaded."""
        if self.is_metadata_complete():
            return None

        for piece_idx, piece_needed in enumerate(self.needed_metadata_pieces):
            if piece_needed and not self.metadata_ongoing_requests[piece_idx]:
                self.metadata_ongoing_requests[piece_idx] = True
                return piece_idx
        piece = next((i for i, x in enumerate(self.needed_metadata_pieces) if x), None)

        if piece is None:
            self.state = DownloadingFSM.PIECE_FIND
            self.metadata_merge()
            threading.Thread(target=self.calculating_top_uploaders, daemon=True).start()

        return piece

    def get_metadata_piece(self, piece_index):
        return self.metadata_pieces.get(piece_index, None)

    def metadata_merge(self):
        pieces = [self.metadata_pieces[idx] for idx in sorted(self.metadata_pieces.keys())]
        metadata = b''.join(pieces)
        self.metadata = bencodepy.decode(metadata)
        self.metadata = MagnetUtils.convert_to_normal_dict(self.metadata)
        self.number_of_pieces = len(self.metadata['pieces']) // 20

        for peer in self.peer_bitfields:
            if not self.peer_bitfields[peer]:
                self.peer_bitfields[peer] = [0] * self.number_of_pieces
        self.piece_counter = {i: self.piece_counter[i] for i in range(self.number_of_pieces)}
        self.init_file_manager()

    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------

    def get_bitfield(self) -> bytes:
        """
        Constructs the bitfield as a byte array, where each bit represents a piece.
        A bit is 1 if the piece is available, otherwise 0.
        """
        if not self.pieces:
            return b""

        with lock:
            # Initialize a byte array with enough bytes to represent all pieces
            bitfield = [0] * ((self.number_of_pieces + 7) // 8)  # One byte for every 8 pieces

            # Set the corresponding bit for each piece
            for piece_index in self.pieces.keys():
                byte_index = piece_index // 8
                bit_index = 7 - (piece_index % 8)  # Bits are ordered from most significant to least significant
                bitfield[byte_index] |= (1 << bit_index)

        return bytes(bitfield)

    def add_peer(self, id):
        self.peer_bitfields[id] = [0] * self.number_of_pieces if self.number_of_pieces else []
        self.peer_upload[id] = 0
        self.optimistic_unchoked_peer = id

    def set_peer_upload(self, id, upload):
        self.peer_upload[id] = upload

    def add_peer_bitfield(self, id, bitfield: list):
        with lock:
            self.peer_bitfields[id] = bitfield
            if not self.piece_counter:
                self.number_of_pieces = len(bitfield)
                self.piece_counter = {i: bitfield[i] for i in range(self.number_of_pieces)}
            else:
                for i in self.piece_counter.keys():
                    self.piece_counter[i] += bitfield[i]

    def find_next_rarest_piece(self) -> tuple[int, list]:
        with lock:
            if not self.piece_counter:
                self.state = DownloadingFSM.DOWN_DONE
                return None, []

            self.state = DownloadingFSM.PIECE_FIND
            data = {k: v for (k, v) in self.piece_counter.items() if v > 0}
            idx = min(data, key=data.get)
            peers = [id for (id, bitfield) in self.peer_bitfields.items() if bitfield[idx] == 1]
        return idx, peers

    def delete_piece(self, indexes: int):
        with lock:
            self.piece_counter.pop(indexes, None)

    def add_peer_piece(self, id, piece_index):
        if self.peer_bitfields[id]:
            self.peer_bitfields[id][piece_index] = 1

        with lock:
            if self.piece_counter.get(piece_index) is not None:
                self.piece_counter[piece_index] += 1

    def select_peers_for_unchoking(self) -> list:
        list_peers = self.top_uploaders + [self.optimistic_unchoked_peer]
        if len(list_peers) < self.num_unchoked + 1:
            list_peers += self.not_interest_peers

        return list(set(list_peers))

    def get_unchoked_peers(self):
        return self.unchoked_peers

    def add_unchoked_peer(self, id):
        self.unchoked_peers.append(id)

    def add_not_interest_peers(self, id):
        self.not_interest_peers.append(id)

    def calculating_top_uploaders(self):
        optimistic_timer = 0
        while True:
            not_fully_downloaded_peers = list(set(self.peer_upload.keys()) - set(self.not_interest_peers))
            peer_upload = {id: self.peer_upload[id] for id in not_fully_downloaded_peers}

            top_uploaders = Counter(peer_upload).most_common(self.num_unchoked)
            self.top_uploaders = [id for id, _ in top_uploaders]

            time.sleep(10)

            optimistic_timer = (optimistic_timer + 10) % 30
            if optimistic_timer == 0:
                remaining_peers = list(set(peer_upload.keys()) - set(self.top_uploaders))
                if remaining_peers:
                    self.optimistic_unchoked_peer = random.choice(remaining_peers)
                optimistic_timer = 0
            self.client.log(f'\nRegular "calculating_top_uploaders" routine update {'-' * 10}\n\nTop uploaders: {self.client.get_peers(
                self.top_uploaders)}\nOptimistic Unchoked Peer: {self.client.get_peers([self.optimistic_unchoked_peer])}\n{'-' * 61}\n\n')


    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------
    def get_block(self, piece_idx, begin, length):
        return self.pieces[piece_idx][begin:begin + length]

    def add_requesting_blocks(self, piece_idx, block_requests):
        self.requesting_blocks = dict()
        self.requesting_piece = piece_idx
        self.number_of_blocks = len(block_requests)
        self.state = DownloadingFSM.PIECE_REQ

    def add_block(self, id, start, block_data):
        self.requesting_blocks[start] = block_data
        self.set_peer_upload(id, len(block_data))

        if len(self.requesting_blocks.keys()) == self.number_of_blocks:
            self.state = DownloadingFSM.PIECE_REQ_DONE
            self.merge_blocks_to_piece()

    def merge_blocks_to_piece(self):
        piece_data = b''.join([self.requesting_blocks[i] for i in sorted(self.requesting_blocks.keys())])
        self.pieces[self.requesting_piece] = piece_data
        piece_map_info = self.piece2file_map[self.requesting_piece]
        self.unchoked_peers = []

        for file in piece_map_info:
            length_in_file = file['length_in_file']
            file_key = file['file']

            if self.file_manager[file_key]['length'] != 0:
                add_percentage = round(length_in_file / self.file_manager[file_key]['length'], 2) * 100
            else:
                add_percentage = 0
            self.file_manager[file_key]['downloaded'] += add_percentage
            self.delete_piece(self.requesting_piece)

    def is_piece_request_done(self) -> int | None:
        if self.state == DownloadingFSM.PIECE_REQ_DONE or self.requesting_piece is not None:
            piece = self.requesting_piece
            self.requesting_piece = None
            return piece
        return None

    def is_waiting_for_piece_response(self):
        return self.state == DownloadingFSM.PIECE_REQ

    def merge_all_pieces(self, dir):
        if sorted(self.pieces.keys()) != list(range(self.number_of_pieces)):
            return None

        all_pieces = [self.pieces[i] for i in sorted(self.pieces.keys())]
        all_pieces = b''.join(all_pieces)

        global_len = 0
        for file in self.metadata['files']:
            file_path = os.path.join(dir, *file['path'])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(all_pieces[global_len:global_len + file['length']])
            global_len += file['length']

        self.state = DownloadingFSM.SEEDING
        return all_pieces

    def init_file_manager(self):
        self.file_manager = dict()
        self.piece2file_map = TorrentUtils.piece2file_map(self.metadata['files'], self.piece_size)

        for file in self.metadata['files']:
            file_path = os.path.join(*file['path'])
            length = file['length']
            self.file_manager[file_path] = {
                'length': length,
                'downloaded': 100 if length == 0 else 0
            }

        # print('File manager:', json.dumps(self.file_manager, indent=2, default=bytes_serializer))
        # print('Piece to file map:', json.dumps(self.piece2file_map, indent=2, default=bytes_serializer))

    def get_progress(self):
        progress = {file: self.file_manager[file]['downloaded'] for file in self.file_manager}
        progress = list(progress.items())
        return progress

    def print_self_info(self):
        print(json.dumps({
            'state': self.state,
            'piece_counter': self.piece_counter,
            'number_of_pieces': self.number_of_pieces,
            'peer_bitfields': self.peer_bitfields
        }, indent=2, default=bytes_serializer))


def bytes_serializer(obj):
    if isinstance(obj, bytes):
        # Encode bytes to base64 and then decode to a UTF-8 string for JSON compatibility
        return base64.b64encode(obj).decode('utf-8')
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
