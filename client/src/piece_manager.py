from queue import Queue
from collections import Counter
import numpy as np


class PieceManager:
    def __init__(self, peer_list, metadata_size=None, piece_size=512 * 1024):
        self.piece_size = piece_size

        self.needed_metadata_pieces = list(bool)
        self.metadata_ongoing_requests = list(bool)
        self.metadata_info = dict()

        self.metadata_size = metadata_size
        self.init_metadata_size(metadata_size, piece_size)

        self.peer_dict = {peer['id']: [] for peer in peer_list}
        self.piece_count = dict()

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
        self.peer_dict[peer_id]['bitfield'] = bitfield           #{2:1,3:0}  bitfield : [1,0,1,1,0]
        if not self.piece_count: 
            self.piece_count = {i:bitfield[i] for i in range(len(bitfield))}
        else: 
            for i in self.piece_count.keys(): 
                self.piece_count[i] += bitfield[i]

    def find_rarest(self):
        if not self.piece_count:
            return None
        data = {k:v for (k,v) in self.piece_count.items() if v > 0} 
        idx =  min(data, key=data.get)
        peers = [k for (k,v) in self.peer_dict.items() if v[idx]]
        return idx,peers
        


    def delete_piece(self, indexes):
        for i in indexes: 
            self.piece_count.pop(i,None)
