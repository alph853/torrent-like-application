import bencodepy

# Define the torrent data
torrent_data = {
    "announce": "http://tracker.example.com/announce",
    "info": {
        "name": "my_directory",
        "files": [
            {
                "length": 12345,
                "path": ["file1.txt"]
            },
            {
                "length": 67890,
                "path": ["file2.txt"]
            },
            {
                "length": 54321,
                "path": ["file3.txt"]
            }
        ],
        "piece length": 524288,
        "pieces": (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            "b95b5b798028f3c665f52f75458ff12b164a2aaebfb4c8a254cf659b9b5465b5"
            "5b30e38f48e64b79f0ff9b535f7b908b4b6e76a3e62f8c3c5e7e8a7f73e5d530"
            "68b329da9893e34099c7d8ad5b6f4f5b1e72f300679a33c51573f4f25056e747"
            "9f1cba3f00b4d7f8d16e2617a740a1c5e72e657df255017d26591d3fbbd6f013"
            "3e5c6b7f5b1a1e5887cf3dc1c0f95c9a1efb9e8aee8f3a90fcdb3b57e7e74888"
        )
    }
}

# Bencode the torrent data
bencoded_torrent = bencodepy.encode(torrent_data)

# Save the bencoded data to a .torrent file
with open('torrent_file.torrent', 'wb') as f:
    f.write(bencoded_torrent)

print("Torrent file created successfully.")