import dataclasses
import struct
from typing import Optional
import re


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


    def get_src_callsign(self) -> Optional[str]:
        """
        Get the callsign of the person who sent the message (at least try)
        None on unknown or failure
        """
        rules = [
            r"^CQ (?:[A-Z]{2,4} )?([0-9A-Z]+)(?: [A-Z]{2}[0-9]{2})?$",  # Match CQ [WWFF] CALLSIGN [QF22]
            r"^(?:[0-9A-Z]+) ([0-9A-Z]+)(?: [A-Z]{2}[0-9]{2})?$",       # Match DEST CALLSIGN [QF22]
            r"^(?:[0-9A-Z]+) ([0-9A-Z]+) (?:R?[\-\+]\d+)$",             # Match DEST CALLSIGN [R]+12   or   [R]+00    or  [R]-10
            r"^(?:[0-9A-Z]+) ([0-9A-Z]+) (?:RR)?73$",                   # Match DEST CALLSIGN [RR]73
        ]

        for regex in rules:
            m = re.match(regex, self.message)
            if m is not None:
                return m.group(1)

        return None


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

