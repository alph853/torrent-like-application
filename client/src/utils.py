import os
import struct
import bencodepy
import hashlib
from urllib.parse import urlparse, parse_qs


class TorrentUtilsClass:
    @staticmethod
    def generate_peer_id() -> str:
        """Generate a unique peer ID."""
        return '-BT0001-' + hashlib.sha1(os.urandom(20)).hexdigest()[:12]

    @staticmethod
    def compute_info_hash(torrent_data) -> bytes:
        """Compute the SHA-1 hash of the info section of the torrent file."""
        info = bencodepy.encode(torrent_data[b'info'])
        return hashlib.sha1(info).digest()

    @staticmethod
    def parse_magnet_link(magnet_link) -> tuple[str, str, str]:
        """Parse a magnet link and extract the info_hash, tracker_url, display_name and exact_length (in bytes).
        Anything not found will be set to None.
        """
        if not magnet_link.startswith("magnet:?"):
            raise ValueError("Invalid magnet link format")
        parsed_link = urlparse(magnet_link)
        params = parse_qs(parsed_link.query)

        info_hash = params.get("xt", [None])[0]  # urn:btih: followed by the info hash
        display_name = params.get("dn", [None])[0]  # The display name
        tracker_url = params.get("tr", [None])[0]  # The tracker URL

        print(type(info_hash))

        return info_hash, tracker_url, display_name

    @staticmethod
    def parse_compacted_peer_list(peer_compacted_string) -> list[dict]:
        """Parse a compacted peer list and return a list of dictionaries containing the peer 'id', 'ip', 'port'."""
        peer_list = []
        for i in range(0, len(peer_compacted_string), 26):
            peer_id = peer_compacted_string[i:i+20]
            ip = peer_compacted_string[i+20:i+24]
            port = peer_compacted_string[i+24:i+26]

            peer_dict = {
                'id': peer_id.decode('utf-8', errors='replace'),
                'ip': '.'.join(map(str, ip)),
                'port': struct.unpack('!H', port)[0]
            }
            peer_list.append(peer_dict)
        return peer_list

    @staticmethod
    def get_reserved_bytes(extension_handshake=False) -> bytes:
        """Produce 8 zero-bytes with the 20th bit from the right set to 1."""
        reserved_bytes = bytearray(8)
        if extension_handshake:
            reserved_bytes[5] = 0x10
        return bytes(reserved_bytes)


TorrentUtils = TorrentUtilsClass()

print(type(TorrentUtils.generate_peer_id()))
magnet_link = "magnet:?xt=urn:btih:2b3b3f7e4e9d3f1e1f3f4e9d3f1e1f3f4e9d3f1&dn=ubuntu-20.04-desktop-amd64.iso&tr=udp://tracker.opentrackr.org:1337/announce"
magnet_params = TorrentUtils.parse_magnet_link(magnet_link)

print(magnet_params)
