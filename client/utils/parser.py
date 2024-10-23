import os
import bencodepy
import hashlib
from urllib.parse import urlparse, parse_qs


def generate_peer_id():
    """Generate a unique peer ID."""
    return '-TC0001-' + hashlib.sha1(os.urandom(20)).hexdigest()[:12]


def compute_info_hash(torrent_data):
    """Compute the SHA-1 hash of the info section of the torrent file."""
    info = bencodepy.encode(torrent_data[b'info'])
    return hashlib.sha1(info).digest()


def parse_magnet_link(magnet_link):
    """Parse a magnet link and extract the info_hash, tracker_url, display_name and exact_length (in bytes).
    Anything not found will be set to None.
    """
    parsed_link = urlparse(magnet_link)
    params = parse_qs(parsed_link.query)

    info_hash = bytes.fromhex(params['xt'][0].split(':')[-1])  # Extract info_hash from magnet link
    tracker_url = params['tr'][0] if 'tr' in params else None  # Extract tracker URL if available
    display_name = params['dn'][0] if 'dn' in params else None  # Torrent display name
    exact_length = params['xl'][0] if 'xl' in params else None  # Exact length of the file

    return {
        'info_hash': info_hash,
        'tracker_url': tracker_url,
        'display_name': display_name,
        'exact_length': exact_length
    }


if __name__ == "__main__":
    magnet_link = "magnet:?xt=urn:btih:abc123abc123abc123abc123abc123abc123abc1&dn=example_torrent&tr=http://tracker.example.com/announce"
    print(parse_magnet_link(magnet_link))
