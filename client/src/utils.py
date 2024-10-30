import os
import struct
import bencodepy
import hashlib
from urllib.parse import urlparse, parse_qs
from PyQt6.QtWidgets import QDialog, QVBoxLayout,QListWidget, QPushButton,QLabel, QFileDialog

def extract_pieces_hashes(pieces_hashes):
    index, result = 0, []
    while index < len(pieces_hashes):
        result.append(pieces_hashes[index: index + 20])
        index += 20
        return b''.join(result)

class TorrentUtilsClass:
    @staticmethod
    def generate_peer_id() -> str:
        """Generate a unique peer ID."""
        return '-BT0001-' + hashlib.sha1(os.urandom(20)).hexdigest()[:12]

    
    @staticmethod
    def compute_info_hash(torrent_data) -> bytes:
        pieces_hashes = torrent_data['info']['pieces']  # Get pieces from the info section
        return hashlib.sha1(extract_pieces_hashes(pieces_hashes)).digest()

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
    
    def parse_torrent_file(self,torrent_file)->tuple[str,str,str]:
        tracker_url = torrent_file["announce"].decode()
        display_name = torrent_file["info"]['name']
        info_hash = self.compute_info_hash(torrent_file)
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
    
TorrentUtils = TorrentUtilsClass()

print(type(TorrentUtils.generate_peer_id()))
magnet_link = "magnet:?xt=urn:btih:2b3b3f7e4e9d3f1e1f3f4e9d3f1e1f3f4e9d3f1&dn=ubuntu-20.04-desktop-amd64.iso&tr=udp://tracker.opentrackr.org:1337/announce"
magnet_params = TorrentUtils.parse_magnet_link(magnet_link)

print(magnet_params)


class AddFileDialogTorrent(QDialog):
    def __init__(self, title, label):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 300, 150)

        self.layout = QVBoxLayout()
        
        self.label = QLabel(label)
        self.layout.addWidget(self.label)

        # Label to show the selected file name
        self.file_name_label = QLabel("No file selected")
        self.layout.addWidget(self.file_name_label)

        # Button to browse for file
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        self.layout.addWidget(self.browse_button)

        # This will store the selected file path
        self.selected_file = ""

        # Add an OK button to confirm selection
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)

    def browse_file(self):
        options = QFileDialog.Option(0)  # Create an instance of QFileDialog.Options
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select a .torrent file", 
            "", 
            "Torrent Files (*.torrent);;All Files (*)", 
            options=options  # Pass the options here
        )
        if file_name:
            self.selected_file = file_name
            self.file_name_label.setText(f"Selected file: {file_name}") 

    def get_result(self):
        return self.selected_file

class ConfigFormTorrent(QDialog):
    def __init__(self, display_name, file_names, info):
        super().__init__()
        self.setWindowTitle(display_name)
        self.setGeometry(100, 100, 300, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("Select a file to download:")
        self.layout.addWidget(self.label)

        # Create a QListWidget to display file names
        self.file_list_widget = QListWidget()
        self.file_list_widget.addItems(file_names)  # Add file names to the list widget
        self.layout.addWidget(self.file_list_widget)

        # Add an OK button to confirm selection
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)

    def get_selected_files(self):
        selected_items = self.file_list_widget.selectedItems()
        return [item.text() for item in selected_items]