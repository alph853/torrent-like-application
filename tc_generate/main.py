import bencodepy
import os
import hashlib

# Define the torrent data
torrent_data = {
    "announce": "http://tracker.example.com/announce",
    "info": {
        "name": "my_directory",
        "files": [
            {
                "length": 739328,
                "path": ["my_directory", "file1.pdf"]
            },
            {
                "length": 2289664,
                "path": ["my_directory", "file2.pdf"]
            },
            {
                "length": 3020800,
                "path": ["my_directory", "file3.pdf"]
            }
        ],
        "piece length": 524288,
        "pieces": []
    }
}

# Function to divide file and compute hashes
def divide_file(file_path, piece_size=512 * 1024):
    hashes = []
    with open(file_path, 'rb') as f:
        while True:
            piece = f.read(piece_size)
            if not piece:  # End of file
                break

            sha1_hash = hashlib.sha1(piece).digest()  # Use digest() for binary output
            hashes.append(sha1_hash)
            
    return hashes

# Initialize a list to hold all pieces
all_hashes = []

# Generate file paths and compute hashes
for file in torrent_data["info"]["files"]:
    # Join the directory and file name to create the full path
    file_path = os.path.join(*file["path"])
    
    # Replace backslashes with forward slashes
    file_path = file_path.replace("\\", "/")

    # Compute the hashes for the file
    hashes = divide_file(file_path)

    # Output the hashes
    print(f"Hashes for {file_path}:")
    for i, h in enumerate(hashes):
        print(f"  Piece {i + 1} SHA-1 Hash: {h.hex()}")
    
    # Add the hashes to the list
    all_hashes.extend(hashes)

# Concatenate all hashes into a single bytes object
pieces_binary = b''.join(all_hashes)

# Assign the concatenated pieces to the torrent data
torrent_data["info"]["pieces"] = pieces_binary

# Write the final torrent data to a .torrent file
with open("sample1.torrent", "wb") as file:
    bencoded_data = bencodepy.encode(torrent_data)
    file.write(bencoded_data)

print("\nFinal Torrent Data written to sample1.torrent")
