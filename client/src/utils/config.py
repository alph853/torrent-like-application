from enum import Enum


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


GLOBAL_TERMINAL = "Welcome to BitTorrent Client\n"
GLOBAL_TERMINAL += "Type 'help' to see available commands\n"
