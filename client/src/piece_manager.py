from queue import Queue
from collections import Counter

import bencodepy

from .utils import TorrentUtils


class PieceManager:
    def __init__(self, peer_list, metadata_size=None, piece_size=512 * 1024, metadata: bytes = None):
        self.metadata_piece_count = None

        if metadata:
            self.metadata = metadata
            self.metadata_complete = True
            self.metadata_size = metadata_size
            self.metadata_piece_count = metadata_size // piece_size + (1 if metadata_size % piece_size else 0)
        else:
            self.metadata_complete = False
            self.metadata_size = None
            self.needed_metadata_pieces = None
            self.metadata_ongoing_requests = None

        self.piece_size = piece_size
        self.number_of_pieces = None
        self.peer_bitfields = {peer['id']: [] for peer in peer_list}
        self.piece_counter = dict()
        self.download_complete = False
        self.pieces = dict()

        self.metadata_info = TorrentUtils.get_metadata_info(metadata)

    def is_metadata_complete(self):
        return self.metadata_complete

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
        self.metadata_info[piece_index] = metadata_piece
        self.needed_metadata_pieces[piece_index] = False

    def get_next_metadata_piece(self) -> int | None:
        """Get the next metadata piece index to request from a peer. Return None means all pieces are downloaded."""
        if self.metadata_complete:
            self.metadata_merge()
            return None

        for piece_idx, piece_needed in enumerate(self.needed_metadata_pieces):
            if piece_needed and not self.metadata_ongoing_requests[piece_idx]:
                self.metadata_ongoing_requests[piece_idx] = True
                return piece_idx
        piece = next((i for i, x in enumerate(self.needed_metadata_pieces) if x), None)

        if piece is None:
            self.metadata_complete = True
        return piece

    def metadata_merge(self):
        pieces = [self.metadata_info[idx] for idx in sorted(self.metadata_info.keys())]
        metadata = b''.join(pieces)
        self.metadata_info = bencodepy.decode(metadata)

    def add_piece(self, piece):
        self.pieces[piece.index] = piece

    def add_peer(self, peer_id):
        self.peer_bitfields[peer_id] = [0] * self.number_of_pieces if self.number_of_pieces else []

    def add_peer_bitfield(self, id, bitfield: list):
        bitfield = [int(b) for b in bitfield]
        self.peer_bitfields[id] = bitfield  # {2:1,3:0}  bitfield : [1,0,1,1,0]
        if not self.piece_counter:
            self.number_of_pieces = len(bitfield)
            self.piece_counter = {i: bitfield[i] for i in range(self.number_of_pieces)}
        else:
            for i in self.piece_counter.keys():
                self.piece_counter[i] += bitfield[i]

    def find_rarest(self) -> tuple[int, list]:
        if not self.piece_counter:
            return None, []
        data = {k: v for (k, v) in self.piece_counter.items() if v > 0}
        idx =  min(data, key=data.get)
        peers = [k for (k, v) in self.peer_bitfields.items() if v[idx]]
        return idx, peers

    def delete_piece(self, indexes: list):
        for i in indexes:
            self.piece_counter.pop(i, None)

    def add_peer_piece(self, peer_id, piece_index):
        self.peer_bitfields[peer_id][piece_index] = 1
        self.piece_counter[piece_index] += 1

    def is_download_complete(self):
        return self.download_complete

    def set_piece(self, piece_index, piece_data):
        self.pieces[piece_index] = piece_data
        self.delete_piece([piece_index])