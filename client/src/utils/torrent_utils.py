import hashlib
import os
import struct
import bencodepy

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

    @staticmethod
    def decode_bencode(bencoded_value):
        """For .torrent file parsing"""
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

    def parse_torrent_file(self, torrent_file_path) -> tuple[str, str, str, str]:
        """Parse a magnet link and extract the info_hash, tracker_url, display_name, metadata (None).
        Anything not found will be set to None.
        """
        with open(torrent_file_path, "rb") as torrent_file:
            bencoded_content = torrent_file.read()
        torrent_content = self.decode_bencode(bencoded_content)

        tracker_url = torrent_content["announce"].decode()
        display_name = torrent_content["info"]['name']
        info_hash = self.compute_info_hash(torrent_content)
        metadata = torrent_content['info']

        return info_hash, tracker_url, display_name, metadata

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

    @staticmethod
    def receive_and_validate_handshake(sock, info_hash):
        handshake = sock.recv(68)
        extension_supported = bool(handshake[25] & 0x10)
        handshake_info_hash = handshake[28:48]
        peer_id = handshake[48:].hex()

        if handshake_info_hash != info_hash:
            raise ValueError('Different info hash and peer id. Connection Severed.')
        return extension_supported, peer_id

    @staticmethod
    def divide_piece_into_blocks(piece_index, piece_size, block_size=16*1024):
        """
        Divide a piece into blocks and prepare request arguments for each block.
        """
        args_list = []
        num_blocks = (piece_size + block_size - 1) // block_size

        for block_num in range(num_blocks):
            begin = block_num * block_size
            length = min(block_size, piece_size - begin)
            args_list.append((piece_index, begin, length))

        return args_list

    @staticmethod
    def generate_info_dictionary(file_path, piece_size=512*1024) -> tuple[dict, bytes]:
        """Generate the info dictionary and pieces used for downloading"""
        def generate_file_dictionary(file_path):
            file_size = os.path.getsize(file_path)
            return {
                'length': file_size,
                'path': file_path.split(os.sep)
            }

        pieces_hash = b''
        pieces = b''
        if os.path.isdir(file_path):
            files = []
            for root, _, file_names in os.walk(file_path):
                for file_name in file_names:
                    file_path = os.path.join(root, file_name)
                    files.append(generate_file_dictionary(file_path))

                    file_content = open(file_path, 'rb').read()
                    pieces += file_content
                    pieces_hash += hashlib.sha1(file_content).digest()
        else:
            files = [generate_file_dictionary(file_path)]

        return {
            'piece length': piece_size,
            'pieces': pieces_hash,
            'name': os.path.basename(file_path),
            'files': files
        }, pieces

    def parse_uploaded_torrent(self, uploader_info: dict, piece_size=512*1024) -> tuple[str, dict, dict]:
        """ Parse the uploaded torrent information and return metadata and pieces"""
        tracker_url = uploader_info['tracker_url']
        save_torrent_dir = uploader_info['save_torrent_dir']
        upload_dir = uploader_info['upload_dir']

        metadata, pieces = self.generate_info_dictionary(upload_dir, piece_size)
        torrent_file = {
            'announce': tracker_url,
            'info': metadata
        }
        with open(os.path.join(save_torrent_dir, f'{metadata['name']}.torrent'), 'wb') as f:
            f.write(bencodepy.encode(torrent_file))

        pieces_dict = dict(enumerate(pieces[i:i+piece_size] for i in range(0, len(pieces), piece_size)))
        info_hash = self.compute_info_hash(torrent_file)
        display_name = metadata['name']

        return info_hash, tracker_url, display_name, metadata, pieces_dict


TorrentUtils = TorrentUtilsClass()
