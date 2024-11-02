import hashlib
import os
import struct
import bencodepy

def decode_bencode(bencoded_value):
    if chr(bencoded_value[0]).isdigit():
        first_colon_index = bencoded_value.find(b":")
        if first_colon_index == -1:
            raise ValueError("Invalid encoded value")
        return bencoded_value[first_colon_index + 1:]
    else:
        bencoded_dict = bencodepy.decode(bencoded_value)

        # Convert byte keys to string keys
        def convert_keys_to_str(data):
            if isinstance(data, dict):
                return {k.decode() if isinstance(k, bytes) else k: convert_keys_to_str(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [convert_keys_to_str(i) for i in data]
            return data
        return convert_keys_to_str(bencoded_dict)

class TorrentUtilsClass:
    @staticmethod
    def generate_peer_id(ip=None, port=None) -> str:
        """Generate a unique peer ID."""
        if ip and port:
            identifier = f"{ip}:{port}".encode('utf-8')
            return hashlib.sha1(identifier).hexdigest()
        else:
            return '-BT0001-' + hashlib.sha1(os.urandom(20)).hexdigest()[:12]

    @staticmethod
    def compute_info_hash(torrent_data) -> bytes:
        def extract_pieces_hashes(pieces_hashes):
            index, result = 0, []
            while index < len(pieces_hashes):
                result.append(pieces_hashes[index: index + 20])
                index += 20
            return b''.join(result)

        pieces_hashes = torrent_data['info']['pieces']
        return hashlib.sha1(extract_pieces_hashes(pieces_hashes)).digest()

    def parse_torrent_file(self, torrent_file) -> tuple[str, str, str]:
        tracker_url = torrent_file["announce"].decode()
        display_name = torrent_file["info"]['name']
        info_hash = self.compute_info_hash(torrent_file)
        return info_hash, tracker_url, display_name

    def parse_compacted_peer_list(self, peer_compacted_string) -> list[dict]:
        """Parse a compacted peer list and return a list of dictionaries containing the peer 'id', 'ip', 'port'.

        'id' is generated using the peer's IP and port.
        """
        peer_list = []
        for i in range(0, len(peer_compacted_string), 6):
            ip = peer_compacted_string[i:i+4]
            port = peer_compacted_string[i+4:i+6]

            peer_dict = {
                'id': self.generate_peer_id(ip, port),
                'ip': '.'.join(map(str, ip)),
                'port': struct.unpack('!H', port)[0]
            }
            peer_list.append(peer_dict)
        return peer_list

    def get_metadata_info(self, metadata):
        if not metadata:
            return None
        return decode_bencode(metadata)

TorrentUtils = TorrentUtilsClass()