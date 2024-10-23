import json
import socket
import requests
import os
import bencodepy
import threading
from .parser import generate_peer_id, parse_magnet_link, compute_info_hash

tracker_response_test = {
    'files': ['file1.txt', 'file2.txt', 'file3.txt'],
    'info': {
        'name': 'Example Torrent',
        'length': 1000
    }
}


class TorrentClient:
    def __init__(self, ip, port, torrent_file=None, magnet_link=None):
        self.ip = ip
        self.port = port
        self.peer_id = generate_peer_id()
        self.status = 'started'
        # self.download_dir = download_dir
        self.files = []

        if magnet_link:
            magnet_params = parse_magnet_link(magnet_link)
            self.info_hash = magnet_params['info_hash']
            self.tracker_url = magnet_params['tracker_url']
            self.display_name = magnet_params['display_name']
            self.total_length = int(magnet_params['exact_length']) if magnet_params['exact_length'] else None

        self.left = None
        self.downloaded = 0

    def start(self):
        pass

    def get_files_from_torrent(self):
        """Extract the list of files from the torrent data."""
        files = []
        total_length = 0
        if b'files' in self.torrent_data[b'info']:
            # Multiple files
            for file_info in self.torrent_data[b'info'][b'files']:
                file_length = file_info[b'length']
                file_path = os.path.join(*[name.decode('utf-8') for name in file_info[b'path']])
                total_length += file_length
                files.append({'path': file_path, 'length': file_length})
        else:
            # Single file
            file_length = self.torrent_data[b'info'][b'length']
            file_name = self.torrent_data[b'info'][b'name'].decode('utf-8')
            total_length += file_length
            files.append({'path': file_name, 'length': file_length})

        return files, total_length

    def compute_progress_from_directory(self):
        """Compute the amount of data already downloaded and left to download based on the directory contents."""
        total_size = 0
        if self.download_dir:
            for file_info in self.files:
                file_path = os.path.join(self.download_dir, file_info['path'])
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)  # Get the size of the file
        # Calculate the "left" and "downloaded" fields
        downloaded = total_size
        left = self.total_length - total_size

        return left, downloaded

    def send_tracker_request(self, test=False):
        if not self.tracker_url:
            print("No tracker URL found in the magnet link or torrent file.")
            return None

        params = {
            'info_hash': self.info_hash,
            'peer_id': self.peer_id,
            'ip': self.ip,
            'port': self.port,
            'uploaded': 0,
            'downloaded': self.downloaded,
            'left': self.left or 0,
            'compact': 1,
            'event': self.status
        }

        print("Request: ")

        def byte_serializer(obj):
            if isinstance(obj, bytes):
                return obj.decode('utf-8', errors='replace')
            raise TypeError

        json.dumps(params, indent=2, default=byte_serializer)

        if test:
            return tracker_response_test

        # Send GET request to the tracker
        response = requests.get(self.tracker_url, params=params)

        if response.status_code == 200:
            return response
        else:
            print("Failed to connect to tracker:", response.status_code)
            return None

    def download_file_from_peers(self):
        """Download multiple files from multiple peers using multithreading."""
        # Start a thread for each file
        threads = []
        for file_info in self.files:
            thread = threading.Thread(target=self.download_single_file, args=(file_info,))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    def download_single_file(self, file_info):
        """Simulate downloading a single file from peers (implement actual peer communication here)."""
        file_path = os.path.join(self.download_dir, file_info['path'])
        print(f"Downloading {file_info['path']} to {file_path}")

        # Simulate downloading the file from peers (actual logic for peer communication would go here)
        file_data = b'This is the content of the file.'

        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_data)

        print(f"Finished downloading {file_info['path']}")

# Example Usage


if __name__ == "__main__":
    # Using a .torrent file
    pass
