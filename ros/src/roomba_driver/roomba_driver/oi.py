"""Roomba Open Interface protocol."""

import struct
import time

OP_START = 128
OP_BAUD = 129
OP_SAFE = 131
OP_SENSORS = 142
OP_DRIVE_DIRECT = 145
OP_QUERY_LIST = 149

BAUD_DEFAULT = 115200
BAUD = 19200
BAUD_CODE_19200 = 7

PKT_OI_MODE = 35

MOTION_PACKETS = (7, 43, 44, 35)
MOTION_FORMAT = ">BHHB"
BATTERY_PACKETS = (21, 22, 23, 24, 25, 26, 34)
BATTERY_FORMAT = ">BHhbHHB"

MODE_OFF = 0
MODE_PASSIVE = 1
MODE_SAFE = 2
MODE_FULL = 3
MODES = ["off", "passive", "safe", "full"]

MAX_WHEEL_SPEED = 500


class BadReply(Exception):
    pass


class NoResponse(Exception):
    pass


def mode_name(mode):
    return MODES[mode] if 0 <= mode < len(MODES) else "unknown %d" % mode


def query(port, packets, fmt):
    size = struct.calcsize(fmt)
    port.flush()
    port.write([OP_QUERY_LIST, len(packets)] + list(packets))
    data = port.read(size)
    # extra bytes are late replies or charger text, the payload can't be trusted
    if len(data) != size:
        raise BadReply("sensor reply %d/%d bytes" % (len(data), size))
    return struct.unpack(fmt, data)


def probe(port):
    """Send START and return the raw packet 35 byte, which now means passive."""
    port.flush()
    port.write([OP_START])
    time.sleep(0.02)
    port.write([OP_SENSORS, PKT_OI_MODE])
    data = port.read(1)
    return data[0] if len(data) == 1 and data[0] <= len(MODES) else None


def connect(port):
    """Open the link at 19200, switching the OI down from 115200 if needed.

    Returns (mode_offset, switched). Some Roomba 600 firmware reports packet 35
    one higher than the spec (passive=2, safe=3, full=4); subtract the offset
    from every raw mode byte.
    """
    port.open_rx(BAUD)
    raw = probe(port)
    switched = False
    if raw is None:
        # fresh power-up: the OI listens at 115200, switch it down once, TX only
        port.write([OP_START, OP_BAUD, BAUD_CODE_19200], baud=BAUD_DEFAULT)
        time.sleep(0.1)
        raw = probe(port)
        switched = True
    if raw is None:
        raise NoResponse("no response at %d or %d baud, asleep? press CLEAN once"
                         % (BAUD, BAUD_DEFAULT))
    offset = raw - MODE_PASSIVE
    if offset not in (0, 1):
        raise BadReply("OI mode byte %d after START, expected passive" % raw)
    return offset, switched


def enter_safe(port):
    """Returns the raw packet 35 byte."""
    port.write([OP_SAFE])
    time.sleep(0.05)
    return query(port, [PKT_OI_MODE], ">B")[0]


def passive(port):
    port.write(drive_direct(0, 0))
    port.write([OP_START])


def drive_direct(right, left):
    """Drive Direct command, wheel speeds in mm/s."""
    right = max(-MAX_WHEEL_SPEED, min(MAX_WHEEL_SPEED, int(right)))
    left = max(-MAX_WHEEL_SPEED, min(MAX_WHEEL_SPEED, int(left)))
    return list(struct.pack(">Bhh", OP_DRIVE_DIRECT, right, left))
