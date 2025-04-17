import hashlib
import os
import socket
import struct
from database import Database, Torrent, Peer
from typing import List, Dict, Tuple
from pydantic import BaseModel
import ipaddress


def is_ipv4(ip: str) -> bool:
    """
    Determines if the given IP address is IPv4.
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except ValueError:
        return False


def is_ipv6(ip: str) -> bool:
    """
    Determines if the given IP address is IPv6.
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except ValueError:
        return False


def to_compact(peer_list: List[Peer]) -> Tuple[bytes, bytes]:
    """
    Convert a list of PeerInfo objects to compact binary formats for IPv4 and IPv6.
    """
    def get_validated_bytes_ip(ip: str, family) -> bytes:
        try:
            return socket.inet_pton(family, ip)
        except socket.error as e:
            print(f"Invalid IP address '{ip}': {e}")
            return b''

    compact_ipv4 = b''
    compact_ipv6 = b''

    for peer in peer_list:
        ip = peer.ip
        port_bytes = peer.port.to_bytes(2, byteorder='big')

        if is_ipv4(ip):
            compact_ipv4 += get_validated_bytes_ip(ip, socket.AF_INET) + port_bytes
        elif is_ipv6(ip):
            compact_ipv6 += get_validated_bytes_ip(ip, socket.AF_INET6) + port_bytes
        else:
            print(f"Invalid IP address format for peer '{peer.peer_id}': {ip}")

    return compact_ipv4, compact_ipv6


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
