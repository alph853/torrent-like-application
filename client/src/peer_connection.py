from queue import Queue
import socket
import struct
import threading
from enum import Enum
from .piece_manager import PieceManager
from .utils import TorrentUtils, MagnetUtils, ExtensionMessageType, MessageType

import bencodepy


class PeerConnection:
    def __init__(self, info_hash, my_id, sock: socket.socket, target_peer: dict, piece_manager: PieceManager, outgoing, client_log_function):
        self.in_queue = Queue()
        self.out_queue = Queue()

        self.id = target_peer['id']        # id generated by the peer's IP and port
        self.peer_id = None                # peer id received from the handshake
        self.ip = target_peer['ip']
        self.port = target_peer['port']
        self.piece_manager = piece_manager
        self.queue_running = True

        self.extension_message_id = 0
        self.ut_metadata_id = 3
        self.peer_not_interest = False      # peer has downloaded everything, not interested in any more pieces
        self.send_to_console = ""
        self.extension_supported = True

        self.sock = sock
        self.client_log_function = client_log_function
        self.init_connection(info_hash, my_id, outgoing)

    def init_connection(self, info_hash, my_id, outgoing):
        self.send_handshake_message(info_hash, my_id, outgoing)
        self.in_thread = threading.Thread(target=self.process_recv_messages, daemon=True)
        self.in_thread.start()

        self.out_thread = threading.Thread(target=self.process_send_messages, daemon=True)
        self.out_thread.start()

    def send_handshake_message(self, info_hash, my_id, outgoing):
        """Send base handshake message. Send an extension message if the peer supports the extension protocol."""
        if not outgoing:
            # Receive and validate the peer's handshake request
            self.extension_supported, self.peer_id = TorrentUtils.receive_and_validate_handshake(self.sock, info_hash)
            self.send_bitfield_message()

        # Send the handshake message. Both outgoing and incoming connections send the same message
        reserved_bytes = MagnetUtils.get_reserved_bytes(self.extension_supported)
        handshake_message = (
            b"\x13BitTorrent protocol"
            + reserved_bytes
            + bytes.fromhex(info_hash)
            + my_id.encode('utf-8')
        )
        self.sock.send(handshake_message)

        if outgoing:
            # Receive and validate the peer's handshake response
            self.extension_supported, self.peer_id = TorrentUtils.receive_and_validate_handshake(self.sock, info_hash)
            if self.extension_supported:
                # Send extension handshake
                self.send_extension_handshake()

    def recv_message(self):
        length_prefix = self.sock.recv(4)
        if not length_prefix or len(length_prefix) < 4:
            print(f"Received length prefix: {length_prefix.hex()}")
            raise ConnectionError("Incomplete message length prefix received.")

        message_length = int.from_bytes(length_prefix, byteorder="big")
        if message_length <= 0:
            raise ValueError("Invalid message length received.")

        message = length_prefix
        while len(message) < message_length:
            chunk = self.sock.recv(min(4096, message_length - len(message)))
            if not chunk:
                raise ConnectionError("Connection closed before full message received.")
            message += chunk

        return message


    def handle_extension_message(self, message):
        """Handle an extension message from the peer."""
        try:
            payload = message[6:]
            decoded_payload = bencodepy.decode(payload)

            if decoded_payload.get(b"msg_type") is not None:
                msg_type = decoded_payload.get(b"msg_type")
                if msg_type == ExtensionMessageType.REQUEST.value:
                    self.handle_metadata_request(message)
                elif msg_type == ExtensionMessageType.DATA.value or msg_type == ExtensionMessageType.REJECT.value:
                    self.handle_metadata_response(message)
                else:
                    print("Unknown message type received.")
            elif b"metadata_size" in decoded_payload:
                self.handle_extension_handshake_response(decoded_payload)
            elif b"m" in decoded_payload:
                self.handle_extension_handshake_request()
            else:
                print("Invalid extension message received.")
        except Exception as e:
            print(f"Error while handling extension message: {e}")


    def send_extension_handshake(self):
        """Send an extension handshake message to the peer."""
        try:
            handshake_message = {b"m": {b"ut_metadata": self.ut_metadata_id}}
            payload = MagnetUtils.construct_extension_payload(handshake_message, self.extension_message_id)
            self.sock.send(payload)
            self.client_log_function(f"Sent extension handshake to {self.ip}, {self.port}.")
        except Exception as e:
            self.client_log_function(f"Error sending extension handshake: {e}")


    def handle_extension_handshake_request(self):
        """Handle an extension handshake request from the peer."""
        try:
            metadata_size = self.piece_manager.get_metadata_size()
            response = {b"m": {b"ut_metadata": self.ut_metadata_id}}
            if metadata_size is not None:
                response[b"metadata_size"] = metadata_size
            payload = MagnetUtils.construct_extension_payload(response, self.extension_message_id)
            self.sock.send(payload)
            self.client_log_function(f"Sent extension handshake response {self.ip}, {self.port}.")
        except Exception as e:
            self.client_log_function(f"Error handling extension handshake request: {e}")


    def handle_extension_handshake_response(self, decoded_payload):
        """Handle an extension handshake response from the peer."""
        try:
            metadata_size = decoded_payload.get(b"metadata_size")
            if metadata_size is not None and self.piece_manager.get_metadata_size() is None:
                self.piece_manager.set_metadata_size(metadata_size)

            ut_metadata_id = decoded_payload[b"m"].get(b"ut_metadata")
            if ut_metadata_id is not None:
                self.ut_metadata_id = ut_metadata_id
                self.send_metadata_request()
        except Exception as e:
            self.client_log_function(f"Error handling extension handshake response: {e}")


    def send_metadata_request(self):
        """Send a metadata request to a peer."""
        try:
            piece_idx = self.piece_manager.get_next_metadata_piece()
            if piece_idx is not None:
                request_dict = {b"msg_type": ExtensionMessageType.REQUEST.value, b"piece": piece_idx}
                payload = MagnetUtils.construct_extension_payload(request_dict, self.extension_message_id)
                self.sock.send(payload)
                self.client_log_function(f"Requested metadata piece {piece_idx}.")
            else:
                self.client_log_function("All metadata pieces downloaded.")
        except Exception as e:
            self.client_log_function(f"Error sending metadata request: {e}")


    def handle_metadata_response(self, message):
        """Process a metadata data or reject message from the peer."""
        try:
            bencoded_dict = message[6:]
            bencoded_end_index = bencoded_dict.find(b"ee") + 2
            decoded_message = bencodepy.decode(bencoded_dict[:bencoded_end_index])

            raw_decoded_message = bencodepy.decode(bencoded_dict[:bencoded_end_index])
            decoded_message = {key.decode("utf-8"): value for key, value in raw_decoded_message.items()}

            msg_type = decoded_message.get("msg_type")
            piece_index = decoded_message.get("piece")

            if msg_type == ExtensionMessageType.DATA.value:
                metadata_piece = bencoded_dict[bencoded_end_index:]
                self.piece_manager.set_metadata_piece(piece_index, metadata_piece)
                self.client_log_function(f"Metadata piece {piece_index} downloaded.")
                self.send_metadata_request()
            elif msg_type == ExtensionMessageType.REJECT.value:
                self.client_log_function(f"Metadata piece {piece_index} rejected by peer.")
            else:
                self.client_log_function("Invalid metadata message type received.")
        except Exception as e:
            self.client_log_function(f"Error handling metadata response: {e}")


    def handle_metadata_request(self, message):
        """Handle a metadata request from the peer."""
        try:
            decoded_message = bencodepy.decode(message[6:])
            piece_index = decoded_message.get(b"piece")
            metadata_piece = self.piece_manager.get_metadata_piece(piece_index)

            if metadata_piece is not None:
                response = {b"msg_type": ExtensionMessageType.DATA.value, b"piece": piece_index}
                payload = MagnetUtils.construct_extension_payload(
                    response, self.extension_message_id, added_length=len(metadata_piece)) + metadata_piece
                self.sock.send(payload)
                self.client_log_function(f"Sent metadata piece {piece_index} to peer.")
            else:
                response = {b"msg_type": ExtensionMessageType.REJECT.value, b"piece": piece_index}
                payload = MagnetUtils.construct_extension_payload(response, self.extension_message_id)
                self.sock.send(payload)
                self.client_log_function(f"Rejected metadata piece {piece_index} request from peer.")
        except Exception as e:
            self.client_log_function(f"Error handling metadata request: {e}")


    def process_send_messages(self):
        """Send messages from the out queue to the peer."""
        while self.queue_running:
            try:
                message = self.out_queue.get()
                self.sock.send(message)
            except (ConnectionError, ValueError) as e:
                print(f"Error sending message: {e}")
                self.queue_running = False

    def process_recv_messages(self):
        """Receive message from a queue, including handling the BitTorrent protocol length prefix.
            Return the complete message, including the 4-byte length prefix, or None on failure.
        """
        while self.queue_running:
            try:
                message = self.recv_message()
                match message[4]:
                    case MessageType.EXTENDED.value:
                        self.handle_extension_message(message)
                    case MessageType.BITFIELD.value:
                        self.handle_bitfield_message(message)
                    case MessageType.PIECE.value:
                        self.handle_piece_message(message)
                    case MessageType.HAVE.value:
                        self.handle_have_message(message)
                    case MessageType.CHOKE.value:
                        self.handle_choke_message()
                    case MessageType.UNCHOKE.value:
                        self.handle_unchoke_message()
                    case MessageType.INTERESTED.value:
                        self.handle_interest_message()
                    case MessageType.NOT_INTERESTED.value:
                        self.handle_not_interested_message()
                    case MessageType.REQUEST.value:
                        self.handle_request_message(message)
                    case _:
                        print(f"Unhandled message type: {message[4]}")
            except (ConnectionError, ValueError) as e:
                print(f"Error receiving message: {e}")
                self.queue_running = False

    def send_bitfield_message(self):
        """Send a bitfield message to the peer."""
        bitfield = self.piece_manager.get_bitfield()
        message = struct.pack(">IB", len(bitfield) + 1 + 4, MessageType.BITFIELD.value) + bitfield
        self.enqueue_send_message(message)

    def handle_bitfield_message(self, message):
        """Handle a bitfield message from the peer."""
        bitfield = message[5:]
        bitfield = [int(b) for b in bitfield]
        self.client_log_function(f"Receive bitfield message from peer {self.ip}, {
                                 self.port}: {''.join([str(b) for b in bitfield])}\n")
        self.piece_manager.add_peer_bitfield(self.id, bitfield)

    def send_choke_message(self):
        """Send a choke message to the peer."""
        message = struct.pack(">IB", 1+4, MessageType.CHOKE.value)
        self.enqueue_send_message(message)

    def handle_choke_message(self):
        """Handle a choke message from the peer."""
        self.client_log_function(f"Peer {self.id} choked.")

    def send_unchoke_message(self):
        """Send an unchoke message to the peer."""
        message = struct.pack(">IB", 1+4, MessageType.UNCHOKE.value)
        self.enqueue_send_message(message)

    def handle_unchoke_message(self):
        """Handle an unchoke message from the peer."""
        self.piece_manager.add_unchoked_peer(self.id)
        self.client_log_function(f"Peer {self.ip}, {self.port} unchoked.")

    def send_request_message(self, piece_index, begin, length):
        """Send a request message to the peer."""
        message = struct.pack(">IBIII", 17, MessageType.REQUEST.value, piece_index, begin, length)
        self.enqueue_send_message(message)

    def handle_request_message(self, message):
        """Handle a request message from the peer."""
        if self.peer_not_interest:
            return
        else:
            index, begin, length = struct.unpack(">III", message[5:])
            block = self.piece_manager.get_block(index, begin, length)
            self.send_piece_message(index, begin, block)
        self.client_log_function(f"Receive request message from peer {self.ip}, {
                                 self.port}: {index}, {begin}, {length}")

    def send_have_message(self, piece_index):
        """Send a have message to the peer."""
        message = struct.pack(">IBI", 9, MessageType.HAVE.value, piece_index)
        self.enqueue_send_message(message)

    def handle_have_message(self, message):
        """Handle a have message from the peer."""
        piece_index = struct.unpack(">I", message[5:])[0]
        self.piece_manager.add_peer_piece(self.id, piece_index)
        self.client_log_function(f"Peer {self.ip}, {self.port} has piece {piece_index}")

    def send_piece_message(self, piece_index, begin, block):
        """Send a piece message to the peer."""
        message = struct.pack(">IBII", len(block) + 13, MessageType.PIECE.value, piece_index, begin) + block
        self.enqueue_send_message(message)

    def handle_piece_message(self, message):
        """Handle a piece message from the peer."""
        _, begin = struct.unpack(">II", message[5:13])
        block = message[13:]
        self.piece_manager.add_block(self.id, begin, block)
        self.client_log_function(f"Receive a block from peer ({self.ip}, {self.port})")

    def send_interest_message(self):
        """Send an interested to the peer for a specific piece."""
        message = struct.pack(">IB", 5, MessageType.INTERESTED.value)
        self.enqueue_send_message(message)

    def handle_interest_message(self):
        """Handle an interested message from the peer."""
        if self.id in self.piece_manager.select_peers_for_unchoking():
            self.send_unchoke_message()
        else:
            self.send_choke_message()

    def send_not_interested_message(self):
        """Send a not interested message to the peer."""
        message = struct.pack(">IB", 5, MessageType.NOT_INTERESTED.value)
        self.enqueue_send_message(message)

    def handle_not_interested_message(self):
        """Handle a not interested message from the peer."""
        self.peer_not_interest = True

    def enqueue_send_message(self, message):
        """Enqueue a message to be sent to the peer."""
        self.out_queue.put(message)

    def seeding(self):
        """Terminate the connection and stop the send threads."""
        self.out_thread.join()
        self.send_not_interested_message()
