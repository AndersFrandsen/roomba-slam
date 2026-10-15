#!/usr/bin/env python3
"""RPLIDAR A1 bring-up self-test."""

import argparse
import collections
import fcntl
import glob
import os
import select
import struct
import sys
import termios
import time

SYNC1 = 0xA5
SYNC2 = 0x5A

# opcodes from the SLAMTEC interface protocol (LR001)
CMD_STOP = 0x25
CMD_RESET = 0x40
CMD_SCAN = 0x20
CMD_GET_INFO = 0x50
CMD_GET_HEALTH = 0x52

# expected response descriptors: (payload length, send mode, data type)
# send mode 1 means the device keeps streaming until told to stop
DESC_INFO = (20, 0, 0x04)
DESC_HEALTH = (3, 0, 0x06)
DESC_SCAN = (5, 1, 0x81)

HEALTH_WARNING = 1
HEALTH_ERROR = 2

# coverage is counted in 10 degree bins
BINS = 36
BIN_DEGREES = 360.0 / BINS

EXIT_OK = 0
EXIT_PORT_MISSING = 10
EXIT_PERMISSION = 11
EXIT_BUSY = 12
EXIT_TERMIOS = 13
EXIT_NO_BYTES = 20
EXIT_FRAMING = 21
EXIT_SHORT_READ = 22
EXIT_HEALTH_WARNING = 30
EXIT_HEALTH_ERROR = 31
EXIT_GPIO = 40
EXIT_SCAN_NOT_STARTED = 50
EXIT_MOTOR_STUCK = 51
EXIT_INCOMPLETE_SWEEP = 52
EXIT_DESYNC = 53

# pass/fail thresholds, tuned loosely around 5.5 Hz and ~360 nodes per rev
LIMITS = {
    "min_nodes": 600,
    "min_revolutions": 2,
    "min_coverage": 34,
    "min_valid_fraction": 0.20,
    "max_drop_fraction": 0.02,
    "stuck_coverage": 4,
}

Node = collections.namedtuple("Node", "start quality angle dist")


class ProtocolError(Exception):
    pass


class FrameError(Exception):
    pass


class Failure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def build_request(cmd):
    return bytes((SYNC1, cmd))


def parse_descriptor(buf):
    if len(buf) != 7:
        raise ProtocolError("descriptor must be 7 bytes, got %d" % len(buf))
    if buf[0] != SYNC1 or buf[1] != SYNC2:
        raise ProtocolError("bad sync %#04x %#04x" % (buf[0], buf[1]))
    # 30 bit length, top 2 bits are the send mode
    word = struct.unpack("<I", buf[2:6])[0]
    return word & 0x3FFFFFFF, word >> 30, buf[6]


def parse_info(payload):
    if len(payload) != 20:
        raise ProtocolError("info payload must be 20 bytes, got %d" % len(payload))
    firmware = struct.unpack("<H", payload[1:3])[0]
    return {
        "model": payload[0],
        "firmware": "%d.%02d" % (firmware >> 8, firmware & 0xFF),
        "hardware": payload[3],
        "serial": payload[4:20].hex(),
    }


def parse_health(payload):
    if len(payload) != 3:
        raise ProtocolError("health payload must be 3 bytes, got %d" % len(payload))
    return payload[0], struct.unpack("<H", payload[1:3])[0]


def parse_node(raw):
    # byte 0: quality(6) | !S | S, where S marks the first node of a revolution
    # byte 1-2: angle in q6 degrees, with a check bit that is always 1 in bit 0
    # byte 3-4: distance in q2 mm, 0 means no return
    if len(raw) != 5:
        raise FrameError("node must be 5 bytes, got %d" % len(raw))
    start = raw[0] & 1
    if start == (raw[0] >> 1) & 1:
        raise FrameError("start flag not complementary")
    if not raw[1] & 1:
        raise FrameError("check bit clear")
    angle_q6 = (raw[2] << 7) | (raw[1] >> 1)
    distance_q2 = struct.unpack("<H", raw[3:5])[0]
    return Node(bool(start), raw[0] >> 2, angle_q6 / 64.0, distance_q2 / 4.0)


def feed(buf):
    # the scan stream has no sync bytes, so on a bad frame slide one byte and retry
    nodes = []
    dropped = 0
    i = 0
    while len(buf) - i >= 5:
        try:
            nodes.append(parse_node(buf[i:i + 5]))
        except FrameError:
            i += 1
            dropped += 1
            continue
        i += 5
    return nodes, buf[i:], dropped


def analyse(samples, dropped=0, received=0):
    nodes = [node for _, node in samples]
    starts = [stamp for stamp, node in samples if node.start]
    angles = [node.angle for node in nodes if node.angle < 360.0]
    occupied = {int(angle // BIN_DEGREES) for angle in angles}

    scan_hz = 0.0
    if len(starts) > 1:
        span = starts[-1] - starts[0]
        if span > 0:
            scan_hz = (len(starts) - 1) / span

    return {
        "nodes": len(nodes),
        "revolutions": len(starts),
        "coverage": len(occupied),
        "valid_fraction": (sum(1 for n in nodes if n.dist > 0) / len(nodes)) if nodes else 0.0,
        "drop_fraction": (dropped / received) if received else 0.0,
        "scan_hz": scan_hz,
        "angle_span": (max(angles) - min(angles)) if angles else 0.0,
    }


def verdict(metrics):
    limits = LIMITS

    if metrics["nodes"] == 0:
        return False, ["no scan nodes decoded"], EXIT_SCAN_NOT_STARTED

    # a stalled motor still produces nodes, but all at roughly the same angle
    if metrics["coverage"] < limits["stuck_coverage"]:
        return False, [
            "motor not spinning: %d/%d bins, angle span %.1f deg"
            % (metrics["coverage"], BINS, metrics["angle_span"])
        ], EXIT_MOTOR_STUCK

    if metrics["drop_fraction"] > limits["max_drop_fraction"]:
        return False, [
            "excessive desync: %.1f%% of bytes dropped" % (100 * metrics["drop_fraction"])
        ], EXIT_DESYNC

    reasons = []
    if metrics["nodes"] < limits["min_nodes"]:
        reasons.append("insufficient data: %d nodes < %d" % (metrics["nodes"], limits["min_nodes"]))
    if metrics["revolutions"] < limits["min_revolutions"]:
        reasons.append(
            "too few revolutions: %d < %d" % (metrics["revolutions"], limits["min_revolutions"])
        )
    if metrics["coverage"] < limits["min_coverage"]:
        reasons.append(
            "incomplete sweep: %d/%d bins < %d" % (metrics["coverage"], BINS, limits["min_coverage"])
        )
    if metrics["valid_fraction"] < limits["min_valid_fraction"]:
        reasons.append(
            "no valid ranges: %.0f%% of nodes had a return, need %.0f%%"
            % (100 * metrics["valid_fraction"], 100 * limits["min_valid_fraction"])
        )

    if reasons:
        return False, reasons, EXIT_INCOMPLETE_SWEEP
    return True, [], EXIT_OK


# linux gpio character device uapi (v2), see include/uapi/linux/gpio.h
GPIO_GET_CHIPINFO_IOCTL = 0x8044B401
GPIO_V2_GET_LINE_IOCTL = 0xC250B407
GPIO_V2_LINE_SET_VALUES_IOCTL = 0xC010B40F
GPIO_V2_LINE_FLAG_OUTPUT = 1 << 3


def open_port(path):
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except FileNotFoundError:
        raise Failure(EXIT_PORT_MISSING, "%s does not exist" % path)
    except PermissionError:
        raise Failure(EXIT_PERMISSION, "%s permission denied" % path)
    # flock so we fail fast instead of fighting rplidar_ros or getty for the port
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise Failure(EXIT_BUSY, "%s is held by another process" % path)
    return fd


def configure_port(fd):
    try:
        attrs = termios.tcgetattr(fd)
        cc = list(attrs[6])
        cc[termios.VMIN] = 0
        cc[termios.VTIME] = 0
        # raw 115200 8N1, no flow control, no echo
        cflag = termios.CS8 | termios.CREAD | termios.CLOCAL
        termios.tcsetattr(
            fd, termios.TCSANOW,
            [0, 0, cflag, 0, termios.B115200, termios.B115200, cc],
        )
        termios.tcflush(fd, termios.TCIOFLUSH)
    except termios.error as exc:
        raise Failure(EXIT_TERMIOS, "termios setup failed: %s" % exc)


def read_exact(fd, count, deadline):
    buf = b""
    while len(buf) < count:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return buf
        ready, _, _ = select.select([fd], [], [], remaining)
        if not ready:
            return buf
        buf += os.read(fd, count - len(buf))
    return buf


def drain(fd, seconds):
    end = time.monotonic() + seconds
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return
        ready, _, _ = select.select([fd], [], [], remaining)
        if not ready:
            return
        os.read(fd, 4096)


def request_response(fd, cmd, expect, timeout=1.0, read_payload=True):
    sent = build_request(cmd)
    os.write(fd, sent)
    deadline = time.monotonic() + timeout
    desc = read_exact(fd, 7, deadline)
    if not desc:
        raise Failure(EXIT_NO_BYTES, "no response to command %#04x" % cmd)
    # our own request coming back means TX is looped to RX somewhere
    if desc.startswith(sent):
        raise Failure(EXIT_FRAMING, "local echo detected (raw %s)" % desc.hex())
    if len(desc) < 7:
        raise Failure(EXIT_SHORT_READ, "descriptor truncated: %s" % desc.hex())
    try:
        got = parse_descriptor(desc)
    except ProtocolError as exc:
        raise Failure(EXIT_FRAMING, "%s (raw %s)" % (exc, desc.hex()))
    if got != expect:
        raise Failure(
            EXIT_FRAMING,
            "descriptor mismatch: got %s want %s (raw %s)" % (got, expect, desc.hex()),
        )
    if not read_payload:
        return b""
    payload = read_exact(fd, got[0], deadline)
    if len(payload) < got[0]:
        raise Failure(EXIT_SHORT_READ, "payload truncated: %d/%d bytes" % (len(payload), got[0]))
    return payload


def stop_scan(fd):
    os.write(fd, build_request(CMD_STOP))
    time.sleep(0.02)
    drain(fd, 0.1)


def reset_device(fd):
    os.write(fd, build_request(CMD_RESET))
    # the A1 prints a boot banner after reset, wait it out and throw it away
    time.sleep(0.8)
    drain(fd, 0.3)


def probe_environment():
    notes = []
    # 7e201000 is the PL011, 7e215040 the mini-uart (baud follows core clock)
    try:
        with open("/proc/device-tree/aliases/serial0", "rb") as handle:
            alias = handle.read().rstrip(b"\x00").decode("ascii", "replace")
        if "7e201000" in alias:
            notes.append("serial0 -> %s (pl011)" % alias)
        elif "7e215040" in alias:
            notes.append("WARNING serial0 -> %s (mini-uart, disable-bt not active)" % alias)
        else:
            notes.append("serial0 -> %s" % alias)
    except OSError:
        notes.append("serial0 alias unavailable")
    try:
        with open("/proc/cmdline") as handle:
            for token in handle.read().split():
                if token.startswith("console=") and ("serial" in token or "ttyAMA" in token):
                    notes.append("WARNING kernel console on %s" % token)
    except OSError:
        pass
    for path in sorted(glob.glob("/sys/class/hwmon/hwmon*/in0_lcrit_alarm")):
        try:
            with open(path) as handle:
                if handle.read().strip() == "1":
                    notes.append("WARNING under-voltage detected")
        except OSError:
            pass
    return notes


def find_gpiochip():
    for path in sorted(glob.glob("/dev/gpiochip*")):
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError:
            continue
        try:
            # struct gpiochip_info: name[32], label[32], lines
            info = bytearray(68)
            fcntl.ioctl(fd, GPIO_GET_CHIPINFO_IOCTL, info)
            label = info[32:64].split(b"\x00")[0].decode("ascii", "replace")
            lines = struct.unpack_from("<I", info, 64)[0]
            # the main SoC bank, not the firmware-owned expander chip
            if label.startswith("pinctrl-bcm") and lines >= 54:
                return path, label
        except OSError:
            pass
        finally:
            os.close(fd)
    return None, None


class MotorLine:
    def __init__(self, chip, offset):
        self.chip = chip
        self.offset = offset
        self.fd = None

    def __enter__(self):
        try:
            chip_fd = os.open(self.chip, os.O_RDWR)
        except OSError as exc:
            raise Failure(EXIT_GPIO, "cannot open %s: %s" % (self.chip, exc))
        try:
            # struct gpio_line_request: offsets[64] @0, consumer[32] @256,
            # config.flags @288, num_lines @560, fd @588
            req = bytearray(592)
            struct.pack_into("<I", req, 0, self.offset)
            consumer = b"lidar-selftest"
            req[256:256 + len(consumer)] = consumer
            struct.pack_into("<Q", req, 288, GPIO_V2_LINE_FLAG_OUTPUT)
            struct.pack_into("<I", req, 560, 1)
            fcntl.ioctl(chip_fd, GPIO_V2_GET_LINE_IOCTL, req, True)
            self.fd = struct.unpack_from("<i", req, 588)[0]
        except OSError as exc:
            raise Failure(EXIT_GPIO, "GPIO%d request failed: %s" % (self.offset, exc))
        finally:
            os.close(chip_fd)
        self.set(0)
        return self

    def set(self, value):
        # struct gpio_line_values: bits, mask
        try:
            fcntl.ioctl(
                self.fd, GPIO_V2_LINE_SET_VALUES_IOCTL, struct.pack("<QQ", 1 if value else 0, 1)
            )
        except OSError as exc:
            raise Failure(EXIT_GPIO, "GPIO%d set failed: %s" % (self.offset, exc))

    def __exit__(self, *exc_info):
        if self.fd is not None:
            try:
                fcntl.ioctl(self.fd, GPIO_V2_LINE_SET_VALUES_IOCTL, struct.pack("<QQ", 0, 1))
            except OSError:
                pass
            os.close(self.fd)
            self.fd = None
        return False


def run_scan(fd, seconds):
    request_response(fd, CMD_SCAN, DESC_SCAN, timeout=2.0, read_payload=False)
    samples = []
    buf = b""
    dropped = 0
    received = 0
    end = time.monotonic() + seconds
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([fd], [], [], remaining)
        if not ready:
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            continue
        now = time.monotonic()
        received += len(chunk)
        buf += chunk
        nodes, buf, lost = feed(buf)
        dropped += lost
        samples.extend((now, node) for node in nodes)
    return samples, dropped, received


def run(args):
    for note in probe_environment():
        print("env     %s" % note)

    fd = open_port(args.port)
    motor = None
    try:
        configure_port(fd)
        print("port    %s 115200 8N1 raw" % args.port)

        # the device may still be streaming from a previous run
        stop_scan(fd)

        info = parse_info(request_response(fd, CMD_GET_INFO, DESC_INFO))
        print("info    model=%#04x fw=%s hw=%d serial=%s"
              % (info["model"], info["firmware"], info["hardware"], info["serial"]))
        if info["model"] == 0:
            raise Failure(EXIT_FRAMING, "implausible device info: model byte is zero")

        status, code = parse_health(request_response(fd, CMD_GET_HEALTH, DESC_HEALTH))
        if status == HEALTH_ERROR:
            print("health  ERROR code=%#06x, resetting" % code)
            reset_device(fd)
            status, code = parse_health(request_response(fd, CMD_GET_HEALTH, DESC_HEALTH))
        print("health  %s code=%#06x" % (["OK", "WARNING", "ERROR"][min(status, 2)], code))
        if status == HEALTH_ERROR:
            raise Failure(EXIT_HEALTH_ERROR, "device health error, code %#06x" % code)
        if status == HEALTH_WARNING:
            raise Failure(EXIT_HEALTH_WARNING, "device health warning, code %#06x" % code)

        chip, label = find_gpiochip()
        if not chip:
            raise Failure(EXIT_GPIO, "no pinctrl-bcm gpiochip found")

        motor = MotorLine(chip, args.motor_gpio).__enter__()
        print("motor   %s %s line %d" % (chip, label, args.motor_gpio))

        # with MOTOCTL low the head should be still; a full sweep here means
        # the motor is powered some other way and the GPIO isn't in control
        samples, dropped, received = run_scan(fd, 1.5)
        stop_scan(fd)
        idle = analyse(samples, dropped, received)
        if idle["coverage"] >= 30:
            print("WARN    motor spins with GPIO%d low: MOTOCTL may not be wired to it"
                  % args.motor_gpio)

        motor.set(1)
        time.sleep(2.0)

        samples, dropped, received = run_scan(fd, 3.0)
        metrics = analyse(samples, dropped, received)
        print("scan    %d nodes %d revs %.1f Hz coverage %d/%d valid %.0f%% dropped %.1f%%"
              % (metrics["nodes"], metrics["revolutions"], metrics["scan_hz"],
                 metrics["coverage"], BINS, 100 * metrics["valid_fraction"],
                 100 * metrics["drop_fraction"]))

        ok, reasons, code = verdict(metrics)
        if not ok:
            for reason in reasons:
                print("FAIL    scan: %s" % reason)
            return code
        print("PASS")
        return EXIT_OK
    finally:
        # always leave the lidar idle and the motor off
        try:
            stop_scan(fd)
        except OSError:
            pass
        if motor is not None:
            motor.__exit__(None, None, None)
        try:
            termios.tcflush(fd, termios.TCIOFLUSH)
        except termios.error:
            pass
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description="RPLIDAR A1 bring-up self-test")
    parser.add_argument("--port", default="/dev/ttyAMA0")
    parser.add_argument("--motor-gpio", type=int, default=18)
    args = parser.parse_args(argv)

    try:
        return run(args)
    except Failure as exc:
        print("FAIL    %s" % exc)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
