import pytest

from src.wsjtx_udp_message_parser import WsjtxUdpMessageParser, WsjtxUdpMessageParserException


def test_example_decode_message():
    example_message = b'\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x04MSHV\x01\x02d\xb7x\xff\xff\xff\xf6?\xc9\x99\x99\xa0\x00\x00\x00\x00\x00\x01r\x00\x00\x00\x03FT8\x00\x00\x00\x12VK4GTR VE3ARF FN25\x00\x00'

    parser = WsjtxUdpMessageParser(example_message)
    result = parser.parse()

    assert result.message == "VK4GTR VE3ARF FN25"
    assert result.mode == "FT8"
    assert result.id == "MSHV"
    assert result.timestamp == 40155000
    assert result.snr == -10


def test_missing_magic_number():
    example_message = b'1234567890'
    parser = WsjtxUdpMessageParser(example_message)

    with pytest.raises(WsjtxUdpMessageParserException):
        result = parser.parse()