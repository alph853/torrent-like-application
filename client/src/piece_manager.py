import os
from queue import Queue
from collections import Counter
import threading
import time
import bencodepy

from .utils import TorrentUtils

lock = threading.Lock()


class DownloadingFSM(enumerate):
    META_DOWN, PIECE_FIND, PIECE_REQ, PIECE_REQ_DONE, DOWN_DONE = range(5)

class PieceManager:
    def __init__(self, peer_list, piece_size=512*1024, block_size=64*1024, metadata: dict = None):
        self.piece_size = piece_size
        self.block_size = block_size
        self.metadata = metadata

        if metadata:
            self.state = DownloadingFSM.PIECE_FIND
            self.metadata_pieces, self.metadata_size = self.split_metadata(metadata, piece_size)
            self.metadata_piece_count = self.metadata_size // piece_size + (1 if self.metadata_size % piece_size else 0)
        else:
            self.state = DownloadingFSM.META_DOWN
            self.needed_metadata_pieces = None
            self.metadata_ongoing_requests = None

            self.metadata_pieces = dict()
            self.metadata_size = None
            self.metadata_piece_count = None

        self.piece_counter = dict()             # Counter of pieces that held by the client
        self.pieces = dict()                    # Pieces the client holds

        self.requesting_blocks = dict()
        self.requesting_piece = None
        self.number_of_blocks = -1
        self.block_request_complete = None

        self.number_of_pieces = None
        self.peer_bitfields = {peer['id']: [] for peer in peer_list}

        self.top_uploaders = []
        self.peer_upload = {peer['id']: 0 for peer in peer_list}

        self.optimistic_unchoked_peer = None
        self.unchoked_peers = []
        self.interest_peers = []

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
        lock.acquire()
        self.metadata_pieces[piece_index] = metadata_piece
        self.needed_metadata_pieces[piece_index] = False
        lock.release()

    def get_next_metadata_piece(self) -> int | None:
        """Get the next metadata piece index to request from a peer. Return None means all pieces are downloaded."""
        if self.is_metadata_complete():
            return None

        lock.acquire()
        for piece_idx, piece_needed in enumerate(self.needed_metadata_pieces):
            if piece_needed and not self.metadata_ongoing_requests[piece_idx]:
                self.metadata_ongoing_requests[piece_idx] = True
                return piece_idx
        piece = next((i for i, x in enumerate(self.needed_metadata_pieces) if x), None)
        lock.release()

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

    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------

    def get_bitfield(self):
        if self.pieces == {}:
            return ""
        return ''.join([str(1) if i in self.pieces else str(0) for i in range(self.number_of_pieces)])

    def is_piece_request_done(self):
        return self.state == DownloadingFSM.PIECE_REQ_DONE

    def add_peer(self, id):
        self.peer_bitfields[id] = [0] * self.number_of_pieces if self.number_of_pieces else []
        self.peer_upload[id] = 0
        self.optimistic_unchoked_peer = id

    def set_peer_upload(self, id, upload):
        self.peer_upload[id] = upload

    def add_peer_bitfield(self, id, bitfield: list):
        bitfield = [int(b) for b in bitfield]
        self.peer_bitfields[id] = bitfield  # {2:1,3:0}  bitfield : [1,0,1,1,0]
        if not self.piece_counter:
            self.number_of_pieces = len(bitfield)
            self.piece_counter = {i: bitfield[i] for i in range(self.number_of_pieces)}
        else:
            for i in self.piece_counter.keys():
                self.piece_counter[i] += bitfield[i]

    def find_next_rarest_piece(self) -> tuple[int, list]:
        if not self.piece_counter:
            self.state = DownloadingFSM.DOWN_DONE
            return None, []

        self.state = DownloadingFSM.PIECE_FIND
        data = {k: v for (k, v) in self.piece_counter.items() if v > 0}
        idx =  min(data, key=data.get)
        peers = [k for (k, v) in self.peer_bitfields.items() if v[idx]]
        return idx, peers

    def delete_piece(self, indexes: int):
        self.piece_counter.pop(indexes, None)

    def add_peer_piece(self, id, piece_index):
        self.peer_bitfields[id][piece_index] = 1
        self.piece_counter[piece_index] += 1

    def is_download_complete(self):
        return self.download_complete

    def get_unchoked_peers(self) -> list:
        return self.top_uploaders + [self.optimistic_unchoked_peer]

    def calculating_top_uploaders(self):
        while not self.download_complete:
            top_uploaders = Counter(self.peer_upload).most_common(4)
            self.top_uploaders = [id for id, _ in top_uploaders]
            time.sleep(5)

    # -------------------------------------------------
    # -------------------------------------------------
    # -------------------------------------------------
    def get_block(self, piece_idx, begin, length):
        return self.pieces[piece_idx][begin:begin + length]

    def add_block(self, start, block_data):
        self.requesting_blocks[start] = block_data

        if len(self.requesting_blocks.keys()) == self.number_of_blocks:
            self.state = DownloadingFSM.PIECE_REQ_DONE
            self.merge_blocks_to_piece()

    def add_requesting_blocks(self, piece_idx, block_requests):
        self.requesting_blocks = dict()
        self.requesting_piece = piece_idx
        self.number_of_blocks = len(block_requests)
        self.state = DownloadingFSM.PIECE_REQ

    def is_waiting_for_piece_response(self):
        return self.state == DownloadingFSM.PIECE_REQ

    def add_interest_peer(self, id):
        self.interest_peers.append(id)

    def get_interest_peers(self):
        """Get the list of peers that will response to us."""
        return self.interest_peers

    def add_not_interested_peer(self, id):
        self.not_interested_peers.append(id)

    def merge_blocks_to_piece(self):
        piece_data = b''.join([self.requesting_blocks[i] for i in sorted(self.requesting_blocks.keys())])
        self.pieces[self.requesting_piece] = piece_data
        self.delete_piece(self.requesting_piece)

    def merge_all_pieces(self, dir):
        if sorted(self.pieces.keys()) != list(range(self.number_of_pieces)):
            print(f"Not all pieces are downloaded. List: {sorted(self.pieces.keys())}")

        all_pieces = [self.pieces[i] for i in sorted(self.pieces.keys())]
        all_pieces = b''.join(all_pieces)

        global_len = 0
        for file in self.metadata['info']['files']:
            file_path = os.path.join(dir, *file['path'])
            with open(file_path, 'wb') as f:
                f.write(all_pieces[global_len:global_len + file['length']])
            global_len += file['length']

        return all_pieces
