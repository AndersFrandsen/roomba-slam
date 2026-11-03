import struct

import pytest
import rclpy
from geometry_msgs.msg import Twist

from roomba_driver import oi
from roomba_driver.node import MAX_MISSES, RoombaNode

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def motion(left=0, right=0, mode=oi.MODE_SAFE):
    return struct.pack(oi.MOTION_FORMAT, 0, left, right, mode)


def battery_reply(sources=0):
    return struct.pack(oi.BATTERY_FORMAT, 0, 15000, -200, 25, 1500, 2000, sources)


@pytest.fixture
def node(port):
    rclpy.init()
    node = RoombaNode()
    node.battery_every = 1000
    node.ticks = 1
    # connect: probe, battery, enter_safe
    port.replies += [bytes([oi.MODE_PASSIVE]), battery_reply(), bytes([oi.MODE_SAFE])]
    node.start(port)
    yield node
    node.destroy_node()
    rclpy.shutdown()


def drives(port):
    return [data for data, _ in port.writes if data[0] == oi.OP_DRIVE_DIRECT]


def test_connects_into_safe_mode(node, port):
    port.replies.append(motion())
    node.on_timer()
    assert node.linked
    assert node.mode == oi.MODE_SAFE
    assert ([oi.OP_SAFE], oi.BAUD) in port.writes


def test_stays_passive_on_dock(port):
    rclpy.init()
    try:
        node = RoombaNode()
        node.ticks = 1
        port.replies += [bytes([oi.MODE_PASSIVE]), battery_reply(sources=2)]
        node.start(port)
        port.replies.append(motion(mode=oi.MODE_PASSIVE))
        node.on_timer()
        assert node.mode == oi.MODE_PASSIVE
        assert ([oi.OP_SAFE], oi.BAUD) not in port.writes
        node.destroy_node()
    finally:
        rclpy.shutdown()


def test_cmd_vel_drives_then_times_out(node, port):
    port.replies.append(motion())
    node.on_timer()

    twist = Twist()
    twist.linear.x = 0.1
    node.on_cmd_vel(twist)
    port.replies.append(motion())
    node.on_timer()
    assert drives(port)[-1] == oi.drive_direct(100, 100)

    node.cmd_time -= node.cmd_timeout + 0.1
    port.replies.append(motion())
    node.on_timer()
    assert drives(port)[-1] == oi.drive_direct(0, 0)


def test_unchanged_command_is_not_resent(node, port):
    for _ in range(3):
        port.replies.append(motion())
        node.on_timer()
    assert len(drives(port)) == 1


def test_reconnects_after_repeated_short_reads(node, port):
    port.replies.append(motion())
    node.on_timer()
    for _ in range(MAX_MISSES):
        port.replies.append(b"\x00")
        node.on_timer()
    assert not node.linked

    port.replies += [bytes([oi.MODE_PASSIVE]), battery_reply(), bytes([oi.MODE_SAFE]), motion()]
    node.on_timer()
    assert node.linked
    assert node.misses == 0


def test_odometry_follows_encoders(node, port):
    port.replies.append(motion(0, 0))
    node.on_timer()
    port.replies.append(motion(500, 500))
    node.on_timer()
    assert node.odometry.x == pytest.approx(500 * node.odometry.metres_per_count)


def test_stop_leaves_oi_passive(node, port):
    port.replies.append(motion())
    node.on_timer()
    node.stop()
    assert port.writes[-1] == ([oi.OP_START], oi.BAUD)
    assert port.writes[-2][0] == oi.drive_direct(0, 0)


def test_offset_mode_bytes_are_compensated(port):
    rclpy.init()
    try:
        node = RoombaNode()
        node.ticks = 1
        # firmware reporting passive=2, safe=3
        port.replies += [bytes([2]), battery_reply(), bytes([3])]
        node.start(port)
        port.replies.append(motion(mode=3))
        node.on_timer()
        assert node.mode == oi.MODE_SAFE

        # wheel drop: OI falls back to passive, reported as 2
        port.replies.append(motion(mode=2))
        node.on_timer()
        assert node.mode == oi.MODE_PASSIVE

        twist = Twist()
        twist.linear.x = 0.1
        node.on_cmd_vel(twist)
        port.replies += [bytes([3]), motion(mode=3)]
        node.on_timer()
        assert node.mode == oi.MODE_SAFE
        assert drives(port)[-1] == oi.drive_direct(100, 100)
        node.destroy_node()
    finally:
        rclpy.shutdown()
