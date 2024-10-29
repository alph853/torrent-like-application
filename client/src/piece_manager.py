from queue import Queue
from collections import Counter

class PieceManagerP2P:
    def __init__(self, peer_list, length):
        self.metadata_queue = Queue()
        
        self.peer_dict = {peer['id']: [] for peer in peer_list}
        self.piece_count = list()

    def add_piece(self, piece):

        self.pieces[piece.index] = piece

    def add_peer_bitfield(self, peer_id, bitfield):
        bitfield = [int(b) for b in bitfield]
        self.peer_dict[peer_id]['bitfield'] = bitfield
        self.piece_count = {str(i): (sum(x) if sum(x)!=0 else 99 )for i, x in enumerate(zip(*self.peer_dict.values()))}
        # {"a": [1, 0, 1, 1, 0],
        # "bv": [1, 0, 1, 1, 1],
        # "d": [0, 0, 1, 0, 0]}

        # {"0":2,"1":99,"2":3,"3":2,"4":1}
    def find_rarest(self):
        if not self.piece_count:
            return []  
        return self.piece_count.index(min(self.piece_count.values)) 
    
    def noti_piece_downloaded(self,idx):
        self.piece_count[idx] = 99 

    def get_next_metadata_piece(self):
        """Get the next metadata piece index to request from a peer."""
        return self.needed_piece_queue.get()
