import hashlib
import os
import socket
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

        metadata = torrent_content['info']
        files = metadata['files']
        for file in files:
            file['path'] = [e.decode('utf-8') for e in file['path']]
        metadata['name'] = metadata['name'].decode('utf-8')

        tracker_url = torrent_content["announce"].decode()
        display_name = metadata['name']
        info_hash = self.compute_info_hash(torrent_content).hex()

        return info_hash, tracker_url, display_name, metadata

    # def parse_compacted_peer_list(self, compacted_peer: bytes, compacted_peer6: bytes) -> list:
    #     peer_list = []
    #     peer_size = 18  # 16 bytes IPv6 + 2 bytes port
    #     if len(compacted_peer6) % peer_size != 0:
    #         print("Warning: Compacted peer string length is not a multiple of 18 bytes.")

    #     for i in range(0, len(compacted_peer6), peer_size):
    #         peer_data = compacted_peer6[i:i+peer_size]
    #         if len(peer_data) < peer_size:
    #             print(f"Skipping incomplete peer data: {peer_data}")
    #             continue  # Skip incomplete data

    #         ip_bytes = peer_data[:16]
    #         port_bytes = peer_data[16:]

    #         try:
    #             ip_str = socket.inet_ntop(socket.AF_INET6, ip_bytes)
    #         except socket.error as e:
    #             print(f"Error converting IP bytes to string: {e}")
    #             continue  # Skip invalid IPs

    #         port = int.from_bytes(port_bytes, byteorder='big')
    #         peer_id = self.generate_peer_id(ip_str, port)

    #         peer_dict = {
    #             'id': peer_id,
    #             'ip': ip_str,
    #             'port': port
    #         }
    #         peer_list.append(peer_dict)

    #     return peer_list

    def parse_compacted_peer_list(self, compacted_peer: bytes, compacted_peer6: bytes):
        """
        Parses compacted peer lists for both IPv4 and IPv6 and returns two separate lists.
        """
        def parse_peers(compacted_peer, peer_size, family):
            peers = []
            if len(compacted_peer) % peer_size != 0:
                print(f"Warning: Compacted peer string length is not a multiple of {peer_size} bytes.")

            for i in range(0, len(compacted_peer), peer_size):
                peer_data = compacted_peer[i:i+peer_size]
                if len(peer_data) < peer_size:
                    print(f"Skipping incomplete peer data: {peer_data}")
                    continue  # Skip incomplete data

                ip_bytes = peer_data[:peer_size - 2]
                port_bytes = peer_data[peer_size - 2:]

                try:
                    ip_str = socket.inet_ntop(family, ip_bytes)
                except socket.error as e:
                    print(f"Error converting IP bytes to string: {e}")
                    continue  # Skip invalid IPs

                port = int.from_bytes(port_bytes, byteorder='big')
                peer_id = self.generate_peer_id(ip_str, port)

                peer = {
                    'id': peer_id,
                    'ip': ip_str,
                    'port': port
                }
                peers.append(peer)
            return peers

        IPV4_PEER_SIZE = 6
        IPV6_PEER_SIZE = 18
        ipv4_peers = parse_peers(compacted_peer, IPV4_PEER_SIZE, socket.AF_INET)
        ipv6_peers = parse_peers(compacted_peer6, IPV6_PEER_SIZE, socket.AF_INET6)

        return (ipv4_peers, ipv6_peers)

    @staticmethod
    def receive_and_validate_handshake(sock, info_hash):
        handshake = sock.recv(68)
        extension_supported = bool(handshake[25] & 0x10)
        handshake_info_hash = handshake[28:48].hex()
        peer_id = handshake[48:].hex()

        if handshake_info_hash != info_hash:
            raise ValueError(f'Different info hash. Connection Severed. {handshake_info_hash} != {info_hash}')
        return extension_supported, peer_id

    @staticmethod
    def divide_piece_into_blocks(piece_index, piece_size, block_size=64*1024):
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
    def generate_info_dictionary(file_path, piece_size=512*1024) -> tuple[dict, dict]:
        """Generate the info dictionary and pieces used for downloading"""
        def generate_file_dictionary(root, path: str):
            length = os.path.getsize(path)
            path = path.split(os.sep)
            path.remove(root)
            if path == []:
                path = [os.path.basename(root)]
            return {
                'length': length,
                'path': path
            }

        pieces = b''
        if os.path.isdir(file_path):
            files = []
            for root, dirnames, file_names in os.walk(file_path):
                for file_name in file_names:
                    p = os.path.join(root, file_name)
                    files.append(generate_file_dictionary(file_path, p))

                    file_content = open(p, 'rb').read()
                    pieces += file_content
        else:
            files = [generate_file_dictionary(file_path, file_path)]
            pieces = open(file_path, 'rb').read()

        pieces_dict = dict(enumerate(pieces[i:i+piece_size] for i in range(0, len(pieces), piece_size)))
        pieces_hash = b''.join([hashlib.sha1(pieces_dict[k]).digest() for k in sorted(pieces_dict.keys())])

        metadata = {
            'piece length': piece_size,
            'pieces': pieces_hash,
            'name': os.path.basename(file_path),
            'files': files
        }

        return metadata, pieces_dict

    def parse_uploaded_torrent(self, uploader_info: dict, piece_size=512*1024) -> tuple[str, dict, dict]:
        """ Parse the uploaded torrent information and return metadata and pieces"""
        tracker_url = uploader_info['tracker_url']
        save_torrent_dir = uploader_info['save_torrent_dir']
        upload_dir = uploader_info['upload_dir']

        metadata, pieces_dict = self.generate_info_dictionary(upload_dir, piece_size)
        torrent_file = self.generate_torrent_file(tracker_url, metadata, save_torrent_dir)

        info_hash = self.compute_info_hash(torrent_file).hex()
        display_name = metadata['name']

        self.generate_magnet_link(info_hash, tracker_url, display_name, save_torrent_dir)
        return info_hash, tracker_url, display_name, metadata, pieces_dict

    @staticmethod
    def generate_torrent_file(tracker_url, metadata, save_torrent_dir=None):
        torrent_file = {
            'announce': tracker_url,
            'info': metadata
        }
        if save_torrent_dir:
            with open(os.path.join(save_torrent_dir, f'{metadata['name']}.torrent'), 'wb') as f:
                f.write(bencodepy.encode(torrent_file))

        return torrent_file

    @staticmethod
    def generate_magnet_link(info_hash, tracker_url, display_name, save_torrent_dir=None):
        magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={display_name}&tr={tracker_url}"
        if save_torrent_dir:
            save_magnet_path = os.path.join(save_torrent_dir, f'{display_name}.txt')
            with open(os.path.join(save_magnet_path), 'w') as f:
                f.write(magnet_link)

        return magnet_link

    @staticmethod
    def piece2file_map(files, piece_size):
        """Maps each piece to the corresponding file(s), handling pieces that span multiple files.
        """
        piece_to_file_map = dict()
        current_file_index = 0
        current_file_offset = 0
        current_piece = 0

        # Iterate through each piece
        while True:
            piece_remaining = piece_size  # Track remaining bytes to map in the current piece
            piece_to_file_map[current_piece] = []

            # Continue mapping until the entire piece is accounted for
            while piece_remaining > 0:
                # Get current file info
                current_file = files[current_file_index]
                file_name = current_file["path"]
                file_length = current_file["length"]

                # Calculate how much data can fit in the current file
                available_in_file = file_length - current_file_offset

                if piece_remaining <= available_in_file:
                    # The piece fits within the remaining part of the current file
                    piece_to_file_map[current_piece].append({
                        "file": os.path.join(*file_name),
                        "length_in_file": piece_remaining,
                        # "is_last": piece_remaining == available_in_file
                    })
                    current_file_offset += piece_remaining
                    piece_remaining = 0  # Entire piece is mapped

                    # Move to the next file if the current file is exhausted
                    if current_file_offset >= file_length:
                        current_file_index += 1
                else:
                    # The piece spans into the next file
                    piece_to_file_map[current_piece].append({
                        "file": os.path.join(*file_name),
                        "length_in_file": available_in_file,
                        # "is_last": True  # This is the last part of the piece within this file
                    })
                    piece_remaining -= available_in_file
                    current_file_index += 1
                    current_file_offset = 0

                if current_file_index >= len(files):
                    break
            if current_file_index >= len(files):
                break

            current_piece += 1  # Move to the next piece

        return piece_to_file_map

TorrentUtils = TorrentUtilsClass()
