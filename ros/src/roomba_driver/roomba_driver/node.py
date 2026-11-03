"""ROS 2 node driving the Roomba: cmd_vel in, odometry, TF, bumper, battery and OI mode out."""

import math
import time
import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry as OdometryMsg
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String, UInt8
from tf2_ros import TransformBroadcaster

from . import oi
from .odometry import Odometry, wheel_speeds

MAX_MISSES = 5
RECONNECT_PERIOD = 1.0

# OI charging state -> BatteryState power supply status
SUPPLY_STATUS = {
    0: BatteryState.POWER_SUPPLY_STATUS_DISCHARGING,
    1: BatteryState.POWER_SUPPLY_STATUS_CHARGING,
    2: BatteryState.POWER_SUPPLY_STATUS_CHARGING,
    3: BatteryState.POWER_SUPPLY_STATUS_CHARGING,
    4: BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING,
}


class RoombaNode(Node):
    def __init__(self):
        super().__init__("roomba_driver")
        self.tx_gpio = self.declare_parameter("tx_gpio", 23).value
        self.rx_gpio = self.declare_parameter("rx_gpio", 24).value
        wheel_diameter = self.declare_parameter("wheel_diameter", 0.072).value
        self.wheel_base = self.declare_parameter("wheel_base", 0.235).value
        rate = self.declare_parameter("rate", 20.0).value
        battery_period = self.declare_parameter("battery_period", 1.0).value
        self.cmd_timeout = self.declare_parameter("cmd_timeout", 0.5).value
        self.odom_frame = self.declare_parameter("odom_frame", "odom").value
        self.base_frame = self.declare_parameter("base_frame", "base_link").value

        self.odometry = Odometry(wheel_diameter, self.wheel_base)
        self.battery_every = max(1, int(round(rate * battery_period)))

        self.odom_pub = self.create_publisher(OdometryMsg, "odom", 10)
        self.bumper_pub = self.create_publisher(UInt8, "bumper", 10)
        self.battery_pub = self.create_publisher(BatteryState, "battery", 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.mode_pub = self.create_publisher(String, "oi_mode", latched)
        self.tf = TransformBroadcaster(self)
        self.create_subscription(Twist, "cmd_vel", self.on_cmd_vel, 10)

        self.port = None
        self.linked = False
        self.next_connect = 0.0
        self.mode = None
        self.mode_offset = 0
        self.sources = 0
        self.misses = 0
        self.ticks = 0
        self.last_poll = None
        self.cmd = (0, 0)
        self.cmd_time = None
        self.sent = None
        self.timer = self.create_timer(1.0 / rate, self.on_timer)

    def start(self, port):
        self.port = port
        self.next_connect = 0.0

    def stop(self):
        if self.port is not None and self.linked:
            oi.passive(self.port)
            self.linked = False

    def on_cmd_vel(self, msg):
        self.cmd = wheel_speeds(msg.linear.x, msg.angular.z, self.wheel_base)
        self.cmd_time = time.monotonic()

    def connect(self):
        self.mode_offset, switched = oi.connect(self.port)
        if switched:
            self.get_logger().info("switched OI from %d to %d baud" % (oi.BAUD_DEFAULT, oi.BAUD))
        if self.mode_offset:
            self.get_logger().info("OI reports modes %+d from the spec, compensating" % self.mode_offset)
        mode = oi.MODE_PASSIVE
        self.sources = oi.query(self.port, oi.BATTERY_PACKETS, oi.BATTERY_FORMAT)[-1]
        if self.sources:
            self.get_logger().warn("charging source present, staying passive")
        else:
            mode = oi.enter_safe(self.port) - self.mode_offset
        self.linked = True
        self.misses = 0
        self.sent = None
        self.last_poll = None
        self.odometry.reset_counts()
        self.set_mode(mode)

    def set_mode(self, mode):
        if mode == self.mode:
            return
        if self.mode == oi.MODE_SAFE:
            self.get_logger().warn("left safe mode (%s), wheel drop or charger?" % oi.mode_name(mode))
        else:
            self.get_logger().info("OI mode %s" % oi.mode_name(mode))
        self.mode = mode
        self.sent = None
        self.mode_pub.publish(String(data=oi.mode_name(mode)))

    def target(self, now):
        if self.cmd_time is None or now - self.cmd_time > self.cmd_timeout:
            return (0, 0)
        return self.cmd

    def on_timer(self):
        if self.port is None:
            return
        now = time.monotonic()
        if not self.linked:
            if now < self.next_connect:
                return
            try:
                self.connect()
            except (oi.NoResponse, oi.BadReply) as exc:
                self.get_logger().error(str(exc), throttle_duration_sec=10.0)
                self.next_connect = now + RECONNECT_PERIOD
                return

        battery = self.ticks % self.battery_every == 0
        self.ticks += 1
        packets = oi.MOTION_PACKETS + (oi.BATTERY_PACKETS if battery else ())
        fmt = oi.MOTION_FORMAT + (oi.BATTERY_FORMAT[1:] if battery else "")
        try:
            self.drive(now)
            values = oi.query(self.port, packets, fmt)
        except oi.BadReply as exc:
            # the bit-bang reader drops a byte now and then, skip that poll
            self.misses += 1
            if self.misses >= MAX_MISSES:
                self.get_logger().error("%s, %d polls in a row, reconnecting" % (exc, self.misses))
                self.linked = False
                self.next_connect = now
            return
        self.misses = 0

        bumps, left, right, mode = values[:4]
        dt = now - self.last_poll if self.last_poll is not None else 0.0
        self.last_poll = now
        self.odometry.update(left, right, dt)
        self.set_mode(mode - self.mode_offset)
        self.publish_odometry()
        self.bumper_pub.publish(UInt8(data=bumps))
        if battery:
            self.sources = values[-1]
            self.publish_battery(values[4:])

    def drive(self, now):
        target = self.target(now)
        if self.mode == oi.MODE_PASSIVE and target != (0, 0) and not self.sources:
            self.set_mode(oi.enter_safe(self.port) - self.mode_offset)
        if self.mode not in (oi.MODE_SAFE, oi.MODE_FULL):
            return
        if target != self.sent:
            self.port.write(oi.drive_direct(*target))
            self.sent = target

    def publish_odometry(self):
        stamp = self.get_clock().now().to_msg()
        odom = self.odometry
        qz = math.sin(odom.theta / 2.0)
        qw = math.cos(odom.theta / 2.0)

        msg = OdometryMsg()
        msg.header.stamp = stamp
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame
        msg.pose.pose.position.x = odom.x
        msg.pose.pose.position.y = odom.y
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.pose.covariance[0] = msg.pose.covariance[7] = 0.01
        msg.pose.covariance[14] = msg.pose.covariance[21] = msg.pose.covariance[28] = 1e6
        msg.pose.covariance[35] = 0.05
        msg.twist.twist.linear.x = odom.linear
        msg.twist.twist.angular.z = odom.angular
        self.odom_pub.publish(msg)

        tf = TransformStamped()
        tf.header.stamp = stamp
        tf.header.frame_id = self.odom_frame
        tf.child_frame_id = self.base_frame
        tf.transform.translation.x = odom.x
        tf.transform.translation.y = odom.y
        tf.transform.rotation.z = qz
        tf.transform.rotation.w = qw
        self.tf.sendTransform(tf)

    def publish_battery(self, values):
        state, mv, ma, temp, charge, capacity, sources = values
        msg = BatteryState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.voltage = mv / 1000.0
        msg.current = ma / 1000.0
        msg.temperature = float(temp)
        msg.charge = charge / 1000.0
        msg.capacity = capacity / 1000.0
        msg.percentage = charge / capacity if capacity else float("nan")
        msg.power_supply_status = SUPPLY_STATUS.get(state, BatteryState.POWER_SUPPLY_STATUS_UNKNOWN)
        msg.present = True
        self.battery_pub.publish(msg)


def main(args=None):
    import pigpio
    from .softserial import SoftSerial

    rclpy.init(args=args)
    node = RoombaNode()
    pi = pigpio.pi()
    if not pi.connected:
        node.get_logger().fatal("cannot connect to pigpiod, is it running?")
        node.destroy_node()
        rclpy.try_shutdown()
        return 1

    port = SoftSerial(pi, node.tx_gpio, node.rx_gpio)
    node.start(port)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # leave the OI passive, Safe mode blocks charging
        try:
            node.stop()
        except pigpio.error as exc:
            node.get_logger().error("stopping: %s" % exc)
        port.close()
        pi.stop()
        node.destroy_node()
        rclpy.try_shutdown()
    return 0
