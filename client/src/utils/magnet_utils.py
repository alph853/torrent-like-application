import struct
from urllib.parse import urlparse, parse_qs

import bencodepy

from .config import MessageType

class MagnetUtilsClass:
    @staticmethod
    def parse_magnet_link(magnet_link) -> tuple[str, str, str, str]:
        """Parse a magnet link and extract the info_hash, tracker_url, display_name, metadata (None).
        Anything not found will be set to None.
        """
        if not magnet_link.startswith("magnet:?"):
            raise ValueError("Invalid magnet link format")
        parsed_link = urlparse(magnet_link)
        params = parse_qs(parsed_link.query)

        info_hash = params.get("xt", [None])[0]  # urn:btih: followed by the info hash
        display_name = params.get("dn", [None])[0]  # The display name
        tracker_url = params.get("tr", [None])[0]  # The tracker URL
        metadata = None

        return info_hash, tracker_url, display_name, metadata

    @staticmethod
    def get_reserved_bytes(extension_handshake=False) -> bytes:
        """Produce 8 zero-bytes with the 20th bit from the right set to 1."""
        reserved_bytes = bytearray(8)
        if extension_handshake:
            reserved_bytes[5] = 0x10
        return bytes(reserved_bytes)

    @staticmethod
    def construct_extension_payload(message, extension_message_id) -> bytes:
        """Construct a payload for an extension message."""
        bencoded_message = bencodepy.encode(message)
        message_length = len(bencoded_message) + 2
        payload = (
            struct.pack(">Ib", message_length, MessageType.EXTENDED.value)
            + struct.pack("B", extension_message_id)
            + bencoded_message
        )
        return payload


MagnetUtils = MagnetUtilsClass()
