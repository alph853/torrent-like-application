# torrent-like-application

## Installation on Window

```bash
conda create -n p2p python -y
conda activate p2p
pip install -r requirements.txt
pip install pyqt6-tools
pip install qt_material
```

## Run tracker server

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Magnet Link Sample

magnet:?xt=urn:btih:2b3b3f7e4e9d3f1e1f3f4e9d3f1e1f3f4e9d3f1&dn=ubuntu-20.04-desktop-amd64.iso&tr=udp://tracker.opentrackr.org:1337/announce

## Tracker Request sample

http://localhost:8000/ip=120.0.2.1&port=20007&announce?info_hash=1234567890abcdef1234567890abcdef12345678&peer_id=peer1&uploaded=0&downloaded=0&left=1000&compact=1&event=started
