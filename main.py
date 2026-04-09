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
        string_length = self._parse_uint32()  # uint32 before the string gives us the number of bytes to read
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

        if message_type != 2:  # We only care about 2, the decode message.
            return None

        try:
            msg = WsjtxUdpMessageDecode()
            msg.id = self._parse_utf8()
            msg.is_new = self._parse_bool()
            msg.timestamp = self._parse_uint32()
            msg.snr = self._parse_int32()  # <-- Note: *not* unsigned!
            msg.delta_time = self._parse_float64()
            msg.delta_frequency = self._parse_uint32()
            msg.mode = self._parse_utf8()
            msg.message = self._parse_utf8()
            msg.is_low_confidence = self._parse_bool()
            msg.is_off_air = self._parse_bool()
            return msg
        except Exception as e:
            raise WsjtxUdpMessageParserException(f"Unable to parse valid message: {e}")


class UserNotifications:
    def __init__(self, time_between_notifications_seconds: int = 180):
        self._time_between_notifications_seconds = time_between_notifications_seconds
        self._audio_filename = None
        self._recent_notifications: dict = {}

    def set_audio_filename(self, filename: str):
        self._audio_filename = filename

    def notify(self, callsign: str, title: str, message: str):
        show_notification = False

        # Has it a new callsign?
        if callsign not in self._recent_notifications:
            show_notification = True

        # Have we seen it, but at least self._time_between_seconds ago?
        elif time.time() > self._recent_notifications[callsign]+self._time_between_notifications_seconds:
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
            subprocess.run(["paplay", self._audio_filename])
        except Exception as e:
            logger.error(f"Unable to play audio file {self._audio_filename}: {e}")


class WsjtxUdpListenerThread:
    def __init__(self, host: str = "127.0.0.1", port: int = 2237):
        self._addr = (host, port)
        self._callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def set_callback(self, callback: Callable[[WsjtxUdpMessageDecode], None]):
        self._callback = callback

    def start(self):
        self._thread = threading.Thread(target=self._thread_entry)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _thread_entry(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.bind(self._addr)

        logger.info(f"Listening to WSJTx messages via UDP on {self._addr[0]}:{self._addr[1]}")

        while not self._stop_event.is_set():
            try:
                data,_ = sock.recvfrom(1024)

                try:
                    message_parser = WsjtxUdpMessageParser(data)
                    message = message_parser.parse()
                    if message is not None:
                        self._callback(message)
                except WsjtxUdpMessageParserException as e:
                    logger.warning(f"Error parsing or processing WSJTx data: {e}")

            except socket.timeout:
                continue

        sock.close()


class PotaActivatorRefresherThread:
    def __init__(self, spot_url: str, update_frequency_min: int = 5, url_fetch_timeout_sec: int = 5):
        self._spot_url = spot_url
        self._update_frequency_min = update_frequency_min
        self._url_fetch_timeout_sec = url_fetch_timeout_sec
        self._json_data = None
        self._callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def set_callback(self, callback: Callable[[dict], None]):
        self._callback = callback

    def start(self):
        self._thread = threading.Thread(target=self._thread_entry)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def get_last_response(self):
        return self._json_data

    def _thread_entry(self):
        logger.info(f"Checking for updates from {self._spot_url} (every {self._update_frequency_min} minutes)")

        while not self._stop_event.is_set():
            try:
                logger.info(f"Fetching lastest spots from {self._spot_url}")
                with urllib.request.urlopen(self._spot_url, timeout=self._url_fetch_timeout_sec) as response:
                    content = response.read().decode('utf-8')
                    self._json_data = json.loads(content)
                    self._callback(self._json_data)
            except Exception as e:
                logger.warning(f"Error fetching URL: {e}")

            # wait x-minutes checking to see if thread should exit every second
            waiting = self._update_frequency_min * 60
            while waiting > 0:
                time.sleep(1)
                waiting -= 1
                if self._stop_event.is_set():
                    break


if __name__ == "__main__":

    notifications = UserNotifications()
    notifications.set_audio_filename('/usr/share/sounds/freedesktop/stereo/message-new-instant.oga')

    wsjtx_thread = WsjtxUdpListenerThread()
    pota_thread  = PotaActivatorRefresherThread("https://api.pota.app/spot/activator", 5, 10)


    def on_wsjtx_message_received(msg: WsjtxUdpMessageDecode) -> None:
        if pota_thread.get_last_response() is None:
            return

        # just the callsigns for now
        activator_callsigns = [item["activator"] for item in pota_thread.get_last_response()]

        for callsign in activator_callsigns:
            if callsign in msg.message:  # i.e.  "VK3ARD" in "CQ POTA VK3ARD"
                notifications.notify(callsign, "Found POTA via WSJTx", msg.message)

        if 'CQ POTA' in msg.message or 'CQ WWFF' in msg.message:
            callsign = msg.message[8:]
            notifications.notify(callsign, "Found POTA via WSJTx", msg.message)


    def on_new_pota_activators(data):
        logger.info(f"Fetched {len(data)} current active pota activators")


    wsjtx_thread.set_callback(on_wsjtx_message_received)
    pota_thread.set_callback(on_new_pota_activators)

    wsjtx_thread.start()
    pota_thread.start()

    running = True
    while running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Quiting...")
            wsjtx_thread.stop()
            pota_thread.stop()
            running = False
