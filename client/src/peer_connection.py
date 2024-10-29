from queue import Queue
import socket
import struct
import threading
from enum import Enum

import bencodepy
from .torrent_utils import TorrentUtils
from .piece_manager import PieceManager


class MessageType(Enum):
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8
    PORT = 9
    EXTENDED = 20


class ExtensionMessageType(Enum):
    REQUEST = 0
    DATA = 1
    REJECT = 2


class PeerConnection:
    def __init__(self, peer: dict, info_hash, piece_manager: PieceManager, extension_supported=False):
        self.out_queue = Queue()
        self.in_queue = Queue()

        self.queue_running = True
        self.metadata_running = True

        self.info_hash = info_hash
        self.ip = peer['ip']
        self.port = peer['port']
        self.peer_id = peer['id']
        self.extension_supported = extension_supported
        self.piece_manager = piece_manager

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_connection()

        reserved_bytes = TorrentUtils.get_reserved_bytes(self.extension_supported)
        self.handshake_message = (
            b"\x13BitTorrent protocol"
            + reserved_bytes
            + bytes.fromhex(self.info_hash)
            + self.peer_id.encode('utf-8')
        )

    def init_connection(self):
        """Establish connection to the peer and start send/receive threads."""
        try:
            print(f"Connected to peer {self.peer_id} at {self.ip}:{self.port}")
            self.socket.connect((self.ip, self.port))
            self.peer_handshake()

            in_thread = threading.Thread(target=self.send_messages)
            out_thread = threading.Thread(target=self.recv_messages)

            in_thread.start()
            out_thread.start()

            in_thread.join()
            out_thread.join()

        except Exception as e:
            print(f"Failed to connect to peer {self.peer_id}: {e}")
        finally:
            self.sock.close()

    def peer_handshake(self):
        self.sock.send(self.handshake_message)
        response = self.sock.recv(68)

        if response[:20] != b"\x13BitTorrent protocol" or len(response) < 68:
            raise ValueError("Invalid base handshake response. Connection Severed")

        self.extension_supported = bool(response[25] & 0x10)
        info_hash = response[28:48]
        response_peer_id = response[48:].hex()

        if self.info_hash != info_hash:
            raise ValueError('Different info hash and peer id. Connection Severed.')

        if self.peer_id != response_peer_id:
            raise ValueError('Different peer id. Connection Severed.')

        peer_bitfield_message = self.recv_message()
        assert peer_bitfield_message[4] == MessageType.BITFIELD.value, "Expected bitfield message"
        self.piece_manager.add_peer_bitfield(self.peer_id, peer_bitfield_message[5:])

        if self.extension_supported:
            extension_id = 1
            handshake_message = {"m": {"ut_metadata": extension_id}}
            bencoded_handshake = bencodepy.encode(handshake_message)
            # 1 byte for message ID, 1 byte for extension message ID
            message_length = (len(bencoded_handshake) + 2)
            # All extension messages use ID 20
            message_id = 20
            extension_message_id = 0  # 0 for extension handshake
            payload = (
                struct.pack(">Ib", message_length, message_id)
                + struct.pack("B", extension_message_id)
                + bencoded_handshake
            )
            # Send the extension handshake
            self.sock.send(payload)
            message = self.recv_message()
            assert message[4] == MessageType.EXTENDED.value, "Expected extension handshake message"
            # Extract the extension message ID and payload
            # extension_message_id = message[5]
            payload = message[6:]
            # Decode the payload to get the 'ut_metadata' ID
            decoded_payload = bencodepy.decode(payload)
            ut_metadata_id = decoded_payload[b"m"][b"ut_metadata"]
            print(f"Received extension handshake with 'ut_metadata' ID: {ut_metadata_id}")
            print(f"Peer Metadata Extension ID: {ut_metadata_id}")

            piece_idx = self.piece_manager.get_next_metadata_piece(self.peer_id)
            self.send_metadata_request(ut_metadata_id, piece_idx)

    def send_metadata_request(self, metadata_id, piece_idx):
        """Send the metadata request to a peer."""
        request_dict = {"msg_type": 0, "piece": piece_idx}
        bencoded_request = bencodepy.encode(request_dict)
        # 1 byte for message ID (20), 1 byte for extension message ID
        message_length = (len(bencoded_request) + 2)
        payload = (
            struct.pack(">Ib", message_length, MessageType.EXTENDED.value)
            + struct.pack("B", metadata_id)
            + bencoded_request
        )
        # Send the metadata request
        self.sock.send(payload)

    def receive_metadata_data(self, metadata_id):
        """Receive the metadata data message from the peer."""
        try:
            message = sock.recv(4096)
            if not message:
                raise ConnectionError("Failed to receive metadata data message.")
            if len(message) < 6:
                raise ValueError("Received message is too short.")
            if message[4] != 20:
                raise ValueError("Received an unexpected message type.")
            bencoded_dict = message[6:]
            # Look for the end of the bencoded dictionary, which should end with 'ee'
            bencoded_end_index = bencoded_dict.find(b"ee") + 2  # Include the 'ee' ending
            # Decode the bencoded part
            decoded_message = bencodepy.decode(bencoded_dict[:bencoded_end_index])
            # Ensure it's a data message
            if decoded_message.get(b"msg_type") != 1:
                raise ValueError("Received an unexpected message type.")
            # Extract metadata information
            total_size = decoded_message.get(b"total_size", 0)
            piece_index = decoded_message.get(b"piece", 0)
            # The raw metadata piece starts right after the bencoded dictionary
            metadata_piece = bencoded_dict[bencoded_end_index:]
            print(f"Received metadata piece of size {total_size} bytes.")
            return metadata_piece
        except Exception as e:
            print(f"Error receiving metadata data: {e}")

    def terminate(self):
        """Terminate the connection and stop the send/receive threads."""
        self.queue_running = False

    def add_message(self, message: bytes):
        """Add a message to the queue (input does not include length prefix)."""
        self.out_queue.put(message)

    def send_messages(self):
        """Send messages from a queue to the peer."""
        while self.queue_running:
            message = self.out_queue.get(timeout=5)
            length_prefix = len(message).to_bytes(4, byteorder="big")
            try:
                self.sock.sendall(length_prefix + message)
            except Exception as e:
                print(f"Error sending message: {e}")

    def put_in_messages(self):
        """Receive message from a queue, including handling the BitTorrent protocol length prefix.
            Return the complete message, including the 4-byte length prefix, or None on failure.
        """
        while self.queue_running:
            try:
                message = self.recv_message()
                self.in_queue.put(message)
            except (ConnectionError, ValueError) as e:
                print(f"Error receiving message: {e}")

    def recv_message(self, timeout=-1):
        length_prefix = self.sock.recv(4)
        if not length_prefix or len(length_prefix) < 4:
            raise ConnectionError("Incomplete message length prefix received.")

        message_length = int.from_bytes(length_prefix, byteorder="big")
        if message_length <= 0:
            raise ValueError("Invalid message length received.")

        message = b""
        while len(message) < message_length:
            chunk = self.sock.recv(min(4096, message_length - len(message)))
            if not chunk:
                raise ConnectionError("Connection closed before full message received.")
            message += chunk

        return message
