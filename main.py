"""
import socket

# 1. Create a UDP socket (SOCK_DGRAM)
# AF_INET is for IPv4, SOCK_DGRAM specifies UDP protocol
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 2. Bind the socket to the address and port
# Use '0.0.0.0' or an empty string to listen on all available interfaces
UDP_IP = "127.0.0.1"
UDP_PORT = 2237
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for UDP packets on {UDP_IP}:{UDP_PORT}...")

while True:
    # 3. Receive data from the buffer (1024 bytes at a time)
    # recvfrom returns a tuple: (data, sender_address)
    data, addr = sock.recvfrom(1024)

    print(f"Received message: {data} from {addr}")
"""


import dataclasses
import struct
import socket
import threading
import time
from typing import Optional, Callable


@dataclasses.dataclass
class WsjtxUdpMessageDecode:
    id: str = ""
    new: bool = False
    timestamp: int = 0
    snr: int = 0
    delta_time: float = 0.0
    delta_frequency: int = 0
    mode: str = ""
    message: str = ""
    is_low_confidence: bool = False
    is_off_air: bool = False

class WsjtxUdpMessageParserException(Exception):
    pass

class WsjtxUdpMessageParser:
    def __init__(self, data: bytes):
        self._cursor = 0
        self._data = data

    def _take(self, size: int) -> bytes:
        portion = self._data[self._cursor:self._cursor + size]
        self._cursor += size
        # print(f"Current position: {self._cursor} - Left {self._data[self._cursor:]}")
        return portion

    def _parse_int32(self) -> int:
        return struct.unpack(">i", self._take(4))[0]

    def _parse_uint32(self) -> int:
        return struct.unpack(">I", self._take(4))[0]

    def _parse_float64(self) -> float:
        return struct.unpack(">d", self._take(8))[0]

    def _parse_utf8(self) -> str:
        string_length = self._parse_uint32()
        raw_string = self._take(string_length)
        return raw_string.decode("utf-8")

    def _parse_bool(self) -> bool:
        return self._take(1) == b"\x01"

    def parse(self):
        magic_number = self._parse_uint32()

        if magic_number != 0xadbccbda:
            raise WsjtxUdpMessageParserException(f"Invalid magic number: {magic_number}")

        schema = self._parse_uint32()

        if schema not in [2]:
            raise WsjtxUdpMessageParserException(f"Invalid schema number: {schema}")

        message_type = self._parse_uint32()

        if message_type != 2:
            raise WsjtxUdpMessageParserException(f"Unsupported message type: {message_type}")

        try:
            msg = WsjtxUdpMessageDecode()
            msg.id = self._parse_utf8()
            msg.is_new = self._parse_bool()
            msg.timestamp = self._parse_uint32()
            msg.snr = self._parse_int32()
            msg.delta_time = self._parse_float64()
            msg.delta_frequency = self._parse_uint32()
            msg.mode = self._parse_utf8()
            msg.message = self._parse_utf8()
            msg.is_low_confidence = self._parse_bool()
            msg.is_off_air = self._parse_bool()
            return msg
        except Exception as e:
            raise WsjtxUdpMessageParserException(f"Unable to parse valid message: {e}")











def wsjtx_udp_listener(addr: tuple[str, int], stop_event: threading.Event, callback: Callable[[WsjtxUdpMessageDecode], None]):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    sock.bind(addr)

    print(f"Listening for UDP packets on {addr[0]}:{addr[1]}")

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(1024)

            try:
                message_parser = WsjtxUdpMessageParser(data)
                message = message_parser.parse()
                callback(message)
            except WsjtxUdpMessageParserException as e:
                print(f"Exception: {e}")

        except socket.timeout:
            continue

    sock.close()


def message_received(msg: WsjtxUdpMessageDecode) -> None:
    print(msg)




if __name__ == "__main__":
    stop_signal = threading.Event()
    listener_thread = threading.Thread(target=wsjtx_udp_listener, args=(("127.0.0.1", 2237), stop_signal, message_received))
    listener_thread.start()

    running = True
    while running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping thread")
            running = False
            stop_signal.set()
            listener_thread.join()
            print("Done")
