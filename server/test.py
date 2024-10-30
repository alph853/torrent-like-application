from database import Database, Torrent, Peer

# Create a sample database instance
db = Database()

# Create some sample torrents
torrent1 = Torrent(
    info_hash="1234567890abcdef1234567890abcdef12345678",
    name="Sample Torrent 1",
    length=1024 * 1024 * 1024,  # 1 GB
    files=["file1.txt", "file2.txt"]
)

torrent2 = Torrent(
    info_hash="abcdef1234567890abcdef1234567890abcdef12",
    name="Sample Torrent 2",
    length=2 * 1024 * 1024 * 1024,  # 2 GB
    files=["file3.txt", "file4.txt"]
)

# Add torrents to the database
db.add_torrent(torrent1)
db.add_torrent(torrent2)
