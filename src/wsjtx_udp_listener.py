import logging
import socket
import threading
from typing import Callable

from wsjtx_udp_message_parser import WsjtxUdpMessageDecode, WsjtxUdpMessageParser, WsjtxUdpMessageParserException


logger = logging.getLogger(__name__)


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
        sock.settimeout(0.100)
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
