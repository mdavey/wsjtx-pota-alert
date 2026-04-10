import pytest

from src.wsjtx_udp_message_parser import WsjtxUdpMessageDecode


def test_get_src_callsign_blank():
    assert WsjtxUdpMessageDecode().get_src_callsign() is None


test_messages = [
    "CQ VK3ARD",
    "CQ WWFF VK3ARD",
    "CQ POTA VK3ARD",
    "CQ VK3ARD QF22",
    "CQ WWFF VK3ARD QF22",
    "CQ POTA VK3ARD QF22",

    "VK0ARD VK3ARD",
    "VK0ARD VK3ARD QF22",
    "VK0ARD VK3ARD -10",
    "VK0ARD VK3ARD +10",
    "VK0ARD VK3ARD +0",
    "VK0ARD VK3ARD R-10",
    "VK0ARD VK3ARD R+10",
    "VK0ARD VK3ARD R+0",

    "VK0ARD VK3ARD 73",
    "VK0ARD VK3ARD RR73",
]

@pytest.mark.parametrize("message", test_messages)
def test_get_src_callsign(message):
    assert WsjtxUdpMessageDecode(message=message).get_src_callsign() == "VK3ARD"
