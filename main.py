import dataclasses
import json
import struct
import socket
import sys
import threading
import time
import urllib.request
import subprocess
import logging
from typing import Optional, Callable


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_handler = logging.StreamHandler(sys.stdout)
logger_handler.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s  %(message)s', datefmt='%Y-%d-%m %I:%M:%S %p'))
logger.addHandler(logger_handler)


POTA_ACTIVATOR_URL = 'https://api.pota.app/spot/activator'
POTA_ACTIVATOR_URL_TIMEOUT = 5 # seconds


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

    def parse(self) -> Optional[WsjtxUdpMessageDecode]:
        magic_number = self._parse_uint32()

        if magic_number != 0xadbccbda:
            raise WsjtxUdpMessageParserException(f"Invalid magic number: {magic_number}")

        schema = self._parse_uint32()

        if schema not in [2]:
            raise WsjtxUdpMessageParserException(f"Invalid schema number: {schema}")

        message_type = self._parse_uint32()

        if message_type != 2:  # Decode message
            return None

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


class Notifications:
    def __init__(self):
        self.time_between_notifications_seconds: int = 180
        self.audio_filename = '/usr/share/sounds/freedesktop/stereo/message-new-instant.oga'
        self._recent_notifications: dict = {}

    def notify(self, callsign: str, title: str, message: str):
        show_notification = False

        # Has it a new callsign?
        if callsign not in self._recent_notifications:
            show_notification = True

        # Have we seen it, but at least self._time_between_seconds ago?
        elif time.time() > self._recent_notifications[callsign]+self.time_between_notifications_seconds:
            show_notification = True

        if show_notification:
            logger.info(f"Found POTA activator: {callsign}")
            self._recent_notifications[callsign] = time.time()  # reset/set time
            self._show_toast_notification(title, message)
            self._play_audio()
        else:
            logger.debug(f"Found POTA activator, but suppressing alert: {callsign}")

    @staticmethod
    def _show_toast_notification(message: str, body: str):
        try:
            subprocess.run(["notify-send", message, body])
        except Exception as e:
            logger.error(f"Unable to send notification: {e}")

    def _play_audio(self):
        try:
            subprocess.run(["paplay", self.audio_filename])
        except Exception as e:
            logger.error(f"Unable to play audio file {self.audio_filename}: {e}")



def wsjtx_udp_listener(addr: tuple[str, int], stop_event: threading.Event, callback: Callable[[WsjtxUdpMessageDecode], None]):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    sock.bind(addr)

    logger.info(f"Listening to WSJTx messages via UDP on {addr[0]}:{addr[1]}")

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(1024)

            try:
                message_parser = WsjtxUdpMessageParser(data)
                message = message_parser.parse()
                if message is not None:
                    callback(message)
            except WsjtxUdpMessageParserException as e:
                logger.warning(f"Error parsing or processing WSJTx data: {e}")

        except socket.timeout:
            continue

    sock.close()


def pota_activator_updator(stop_event: threading.Event, callback: Callable, refresh_timer_minutes: int = 5 ):
    logger.info(f"Checking for updates from {POTA_ACTIVATOR_URL} every {refresh_timer_minutes} minutes")

    while not stop_event.is_set():
        try:
            logger.info(f"Fetching url from {POTA_ACTIVATOR_URL}")
            with urllib.request.urlopen(POTA_ACTIVATOR_URL, timeout=POTA_ACTIVATOR_URL_TIMEOUT) as response:
                content = response.read().decode('utf-8')
                callback(json.loads(content))
        except Exception as e:
            logger.warning(f"Error fetching URL: {e}")

        # wait x-minutes checking to see if thread should exit every second
        waiting = refresh_timer_minutes * 60
        while waiting > 0:
            time.sleep(1)
            waiting -= 1
            if stop_event.is_set():
                break


notifications = Notifications()
CURRENT_ACTIVATOR_CALLSIGNS = []

def on_wsjtx_message_received(msg: WsjtxUdpMessageDecode) -> None:
    global CURRENT_ACTIVATOR_CALLSIGNS

    for callsign in CURRENT_ACTIVATOR_CALLSIGNS:
        if callsign in msg.message:  # i.e.  "VK3ARD" in "CQ POTA VK3ARD"
            notifications.notify(callsign, "Found POTA via WSJTx", msg.message)

    if 'CQ POTA' in msg.message or 'CQ WWFF' in msg.message:
        callsign = msg.message[8:]
        notifications.notify(callsign, "Found POTA via WSJTx", msg.message)


def on_new_pota_activators(data):
    global CURRENT_ACTIVATOR_CALLSIGNS
    logger.info(f"Fetched {len(data)} current active pota activators")

    CURRENT_ACTIVATOR_CALLSIGNS = []

    for item in data:
        CURRENT_ACTIVATOR_CALLSIGNS.append(item["activator"])


if __name__ == "__main__":
    wsjtx_stop_signal = threading.Event()
    wsjtx_thread = threading.Thread(target=wsjtx_udp_listener, args=(("127.0.0.1", 2237), wsjtx_stop_signal, on_wsjtx_message_received))
    wsjtx_thread.start()

    pota_stop_signal = threading.Event()
    pota_thread = threading.Thread(target=pota_activator_updator, args=(pota_stop_signal, on_new_pota_activators))
    pota_thread.start()

    running = True
    while running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Quiting...")
            running = False
            wsjtx_stop_signal.set()
            wsjtx_thread.join()

            pota_stop_signal.set()
            pota_thread.join()
            logger.info("Bye!")
