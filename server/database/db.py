import hashlib
from typing import List, Dict
from datetime import datetime
import bencodepy


class Peer:
    def __init__(self, peer_id: str, ip: str, port: int, uploaded: int, downloaded: int, left: int, status: str, info_hash: str):
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.uploaded = uploaded
        self.downloaded = downloaded
        self.left = left
        self.status = status
        self.last_announce = datetime.now()
        self.info_hash = info_hash
        self.id = f'{peer_id}-{info_hash}'

    def update_announce(self, uploaded: int, downloaded: int, left: int, status: str):
        """Update peer's stats on each announce."""
        self.uploaded = uploaded
        self.downloaded = downloaded
        self.left = left
        self.status = status
        self.last_announce = datetime.now()

    def __repr__(self):
        return f"Peer({self.peer_id}, {self.status}, uploaded={self.uploaded}, downloaded={self.downloaded}, left={self.left})"


class Torrent:
    def __init__(self, info_hash: str):
        self.info_hash = info_hash  # SHA-1 hash of the torrent's info section
        self.seeders_id_list = []   # List of peer IDs that are seeders
        self.leechers_id_list = []  # List of peer IDs that are leechers
        self.peer_list: List[Peer] = []  # List of all peers participating in this torrent

    def add_peer(self, peer: Peer):
        """Add a peer to the torrent, update seeder/leecher lists."""
        self.peer_list.append(peer)
        if peer.left == 0:
            self.seeders_id_list.append(peer.peer_id)
        else:
            self.leechers_id_list.append(peer.peer_id)

    def remove_peer(self, peer_id: str):
        """Remove a peer from the torrent, update seeder/leecher lists."""
        self.peer_list = [peer for peer in self.peer_list if peer.peer_id != peer_id]
        self.seeders_id_list = [pid for pid in self.seeders_id_list if pid != peer_id]
        self.leechers_id_list = [pid for pid in self.leechers_id_list if pid != peer_id]

    def __repr__(self):
        return f"Torrent({self.info_hash}, seeders={len(self.seeders_id_list)}, leechers={len(self.leechers_id_list)})"


class Database:
    def __init__(self):
        self.torrents: Dict[str, Torrent] = {}  # A dictionary of torrents by info_hash
        self.peers: Dict[str, Peer] = {}        # A dictionary of peers by composite key (peer_id + info_hash)

    def add_torrent(self, torrent: Torrent):
        """Add a new torrent to the database."""
        self.torrents[torrent.info_hash] = torrent
        print(f"Torrent added: {torrent}")

    def add_peer(self, peer: Peer):
        """Add a peer to the database and associate it with a torrent."""
        if peer.info_hash not in self.torrents:
            print(f"Torrent with info_hash {peer.info_hash} does not exist!")
            return

        self.peers[peer.id] = peer
        torrent = self.torrents[peer.info_hash]
        torrent.add_peer(peer)
        print(f"Peer added to torrent {torrent.info_hash}: {peer}")

    def remove_peer(self, peer: Peer):
        """Remove a peer from the torrent and peer list."""
        peer_id = peer.peer_id
        info_hash = peer.info_hash
        peer_key = f"{peer_id}-{info_hash}"

        if peer_key in self.peers:
            del self.peers[peer_key]
            self.torrents[info_hash].remove_peer(peer_id)
            print(f"Peer {peer_id} removed from torrent {info_hash}")
        else:
            print(f"Peer {peer_id} not found in torrent {info_hash}")

    def update_peer(self, peer: Peer):
        """Update an existing peer's data."""
        peer_key = f"{peer.peer_id}-{peer.info_hash}"
        if peer_key in self.peers:
            peer = self.peers[peer_key]
            peer.update_announce(peer.uploaded, peer.downloaded, peer.left, peer.status)
            print(f"Peer {peer.peer_id} updated: {peer}")
        else:
            print(f"Peer {peer.peer_id} not found!")

    def get_torrent_peers(self, info_hash: str) -> List[Peer] | None:
        """Retrieve all peers for a specific torrent."""
        if info_hash in self.torrents:
            return self.torrents[info_hash].peer_list
        else:
            return None

    def get_torrent(self, info_hash: str) -> Torrent:
        """Retrieve a torrent by info_hash."""
        return self.torrents.get(info_hash, None)

    def __repr__(self):
        return f"Database(Torrents: {len(self.torrents)}, Peers: {len(self.peers)})"
