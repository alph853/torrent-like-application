from queue import Queue
from collections import Counter


class PieceManager:
    def __init__(self, peer_list, metadata_size=None, piece_size=512 * 1024):
        self.piece_size = piece_size

        self.needed_metadata_pieces = list(bool)
        self.metadata_ongoing_requests = list(bool)
        self.metadata_info = dict()

        self.metadata_size = metadata_size
        self.init_metadata_size(metadata_size, piece_size)

        # self.peer_dict = {peer['id']: [] for peer in peer_list}
        # self.piece_count = dict()

    def get_metadata_size(self):
        return self.metadata_size

    def set_metadata_size(self, metadata_size):
        self.metadata_size = metadata_size
        self.init_metadata_size(metadata_size, self.piece_size)

    def set_metadata_piece(self, piece_index, metadata_piece):
        self.metadata_info[piece_index] = metadata_piece
        self.needed_metadata_pieces[piece_index] = False

    def get_next_metadata_piece(self):
        """Get the next metadata piece index to request from a peer. Return None means all pieces are downloaded."""
        for piece_idx, piece_needed in enumerate(self.needed_metadata_pieces):
            if piece_needed and not self.metadata_ongoing_requests[piece_idx]:
                self.metadata_ongoing_requests[piece_idx] = True
                return piece_idx
        piece = next((i for i, x in enumerate(self.needed_metadata_pieces) if x), None)
        return piece

    def init_metadata_size(self, size, piece_size):
        if size is None:
            return None
        self.metadata_piece_count = size // piece_size + (1 if size % piece_size else 0)
        self.needed_metadata_pieces = [True] * self.metadata_piece_count
        self.metadata_ongoing_requests = [False] * self.metadata_piece_count


    def add_piece(self, piece):
        self.pieces[piece.index] = piece

    def add_peer_bitfield(self, peer_id, bitfield):
        bitfield = [int(b) for b in bitfield]
        self.peer_dict[peer_id]['bitfield'] = bitfield
        self.piece_count = {str(i): (sum(x) if sum(x) != 0 else float('inf'))
                            for i, x in enumerate(zip(*self.peer_dict.values()))}

    def find_rarest(self):
        if not self.piece_count:
            return None
        return self.piece_count.index(min(self.piece_count.values))

    def noti_piece_downloaded(self, idx):
        self.piece_count[idx] = float('inf')
