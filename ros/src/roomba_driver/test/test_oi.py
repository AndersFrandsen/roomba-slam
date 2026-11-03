import struct

import pytest

from roomba_driver import oi


def test_query_list_decodes_motion_packets(port):
    port.replies.append(struct.pack(oi.MOTION_FORMAT, 0b11, 65535, 12, oi.MODE_SAFE))
    assert oi.query(port, oi.MOTION_PACKETS, oi.MOTION_FORMAT) == (3, 65535, 12, oi.MODE_SAFE)
    assert port.writes == [([oi.OP_QUERY_LIST, 4, 7, 43, 44, 35], oi.BAUD)]


def test_query_raises_on_short_reply(port):
    port.replies.append(b"\x00\x01")
    with pytest.raises(oi.BadReply):
        oi.query(port, oi.MOTION_PACKETS, oi.MOTION_FORMAT)


def test_query_raises_on_long_reply(port):
    port.replies.append(struct.pack(oi.BATTERY_FORMAT, 0, 15000, 0, 20, 1000, 2000, 0) + b"\x02")
    with pytest.raises(oi.BadReply):
        oi.query(port, oi.BATTERY_PACKETS, oi.BATTERY_FORMAT)


def test_connect_at_19200(port):
    port.replies.append(bytes([oi.MODE_PASSIVE]))
    assert oi.connect(port) == (0, False)
    assert port.rx_baud == oi.BAUD
    assert all(baud == oi.BAUD for _, baud in port.writes)


def test_connect_switches_down_from_115200(port):
    port.replies += [b"", bytes([oi.MODE_PASSIVE])]
    assert oi.connect(port) == (0, True)
    assert ([oi.OP_START, oi.OP_BAUD, oi.BAUD_CODE_19200], oi.BAUD_DEFAULT) in port.writes


def test_connect_detects_mode_offset(port):
    # this Roomba 600 reports passive as 2
    port.replies.append(bytes([2]))
    assert oi.connect(port) == (1, False)


def test_connect_rejects_implausible_mode(port):
    port.replies.append(bytes([oi.MODE_OFF]))
    with pytest.raises(oi.BadReply):
        oi.connect(port)


def test_connect_gives_up(port):
    with pytest.raises(oi.NoResponse):
        oi.connect(port)


def test_drive_direct_is_right_then_left_big_endian():
    assert oi.drive_direct(200, -200) == [145, 0x00, 0xC8, 0xFF, 0x38]


def test_drive_direct_clamps():
    assert oi.drive_direct(900, -900) == oi.drive_direct(500, -500)


def test_passive_stops_wheels_first(port):
    oi.passive(port)
    assert [data for data, _ in port.writes] == [oi.drive_direct(0, 0), [oi.OP_START]]
