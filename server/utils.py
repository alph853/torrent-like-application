from database import Database, Torrent, Peer
from typing import List, Dict

def to_compact(peer_list: List[Peer]):
    if not peer_list:
        return b''
    compact_str = b''
    for peer in peer_list:
        peer_id = peer.peer_id.encode()
        ip = peer.ip.split('.')
        port = peer.port.to_bytes(2, byteorder='big')
        compact_str += peer_id + bytes(ip) + port
    return compact_str