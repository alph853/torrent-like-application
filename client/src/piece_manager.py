from queue import Queue


class PieceManagerP2P:
    def __init__(self, peer_list, length):
        self.metadata_queue = Queue()
        self.piece_queue = Queue()
        self.peer_dict = {peer['id']: {'peer': peer, 'bitfield': []} for peer in peer_list}

    def add_piece(self, piece):
        self.pieces[piece.index] = piece

    def add_peer_bitfield(self, peer_id, bitfield):
        bitfield = [int(b) for b in bitfield]
        self.peer_dict[peer_id]['bitfield'] = bitfield

    def get_next_metadata_piece(self):
        """Get the next metadata piece index to request from a peer."""
        return self.index_queue.get()


PieceManager = PieceManagerP2P()
