import hashlib
import os
import socket
import struct
from database import Database, Torrent, Peer
from typing import List, Dict, Tuple


def to_compact(peer_list: List[Peer]) -> bytes:
    """
    Convert a list of Peer objects with IPv6 addresses to a compact binary format.
    Each peer is represented by 16 bytes for the IPv6 address and 2 bytes for the port.
    """
    if not peer_list:
        return b''

    compact_bytes = b''
    for peer in peer_list:
        try:
            # Convert IPv6 address to 16-byte binary format
            ip_bytes = socket.inet_pton(socket.AF_INET6, peer.ip)
        except socket.error as e:
            print(f"Invalid IPv6 address '{peer.ip}': {e}")
            continue  # Skip invalid IP addresses

        # Convert port to 2-byte big-endian format
        port_bytes = peer.port.to_bytes(2, byteorder='big')

        # Concatenate IP and port bytes
        compact_bytes += ip_bytes + port_bytes
    return compact_bytes

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
