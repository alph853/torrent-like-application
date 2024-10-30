import hashlib
import os
import struct
from database import Database, Torrent, Peer
from typing import List, Dict, Tuple


def to_compact(peer_list: List[Peer]):
    if not peer_list:
        return b''

    compact_str = b''
    for peer in peer_list:
        # Convert each IP segment to an integer and pack it as bytes
        ip_bytes = bytes(int(octet) for octet in peer.ip.split('.'))
        port_bytes = peer.port.to_bytes(2, byteorder='big')

        # Concatenate IP and port bytes for each peer
        compact_str += ip_bytes + port_bytes

    return compact_str

# --------- FOR TESTING ------------
def generate_peer_id(ip=None, port=None) -> str:
    """Generate a unique peer ID."""
    if ip and port:
        identifier = f"{ip}:{port}".encode('utf-8')
        return hashlib.sha1(identifier).hexdigest()
    else:
        return '-BT0001-' + hashlib.sha1(os.urandom(20)).hexdigest()[:12]


def from_compact(peer_compacted_string) -> list[dict]:
    """Parse a compacted peer list and return a list of dictionaries containing the peer 'id', 'ip', 'port'.

    'id' is generated using the peer's IP and port.
    """
    peer_list = []
    for i in range(0, len(peer_compacted_string), 6):
        ip = peer_compacted_string[i:i+4]
        port = peer_compacted_string[i+4:i+6]

        peer_dict = {
            'id': generate_peer_id(ip, port),
            'ip': '.'.join(map(str, ip)),
            'port': struct.unpack('!H', port)[0]
        }
        peer_list.append(peer_dict)
    return peer_list
