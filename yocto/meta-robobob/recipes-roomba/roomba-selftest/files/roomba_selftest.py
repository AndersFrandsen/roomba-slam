#!/usr/bin/env python3
"""Roomba 600 Open Interface bring-up self-test."""

import argparse
import struct
import sys
import time

import pigpio

OP_START = 128
OP_BAUD = 129
OP_SAFE = 131
OP_LEDS = 139
OP_SONG = 140
OP_PLAY = 141
OP_SENSORS = 142
OP_QUERY_LIST = 149

BAUD_DEFAULT = 115200
BAUD = 19200
BAUD_CODE_19200 = 7

PKT_BUTTONS = 18
PKT_OI_MODE = 35
BATTERY_PACKETS = (21, 22, 23, 24, 25, 26, 34)
BATTERY_FORMAT = ">BHhbHHB"

MODE_SAFE = 2
MODES = ["off", "passive", "safe", "full"]
CHARGING_STATES = ["not charging", "reconditioning", "full charging", "trickle", "waiting", "fault"]
BUTTONS = [(0, "CLEAN"), (1, "SPOT"), (2, "DOCK")]

LED_DEBRIS = 1 << 0

# C5 E5 G5, durations in 1/64 s
SONG = [72, 16, 76, 16, 79, 32]

EXIT_OK = 0
EXIT_PIGPIO = 10
EXIT_NO_RESPONSE = 20
EXIT_MODE = 21
EXIT_SHORT_READ = 22
EXIT_ON_DOCK = 30
EXIT_NO_BUTTON = 40


class Failure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class SoftSerial:
    # pigpio bit-bang UART: DMA waveforms for TX, DMA sampling for RX
    def __init__(self, pi, tx, rx):
        self.pi = pi
        self.tx = tx
        self.rx = rx
        self.rx_open = False
        pi.set_mode(tx, pigpio.OUTPUT)
        pi.write(tx, 1)
        pi.wave_clear()

    def open_rx(self, baud):
        # pigpiod keeps the reader open if a previous run died
        try:
            self.pi.bb_serial_read_close(self.rx)
        except pigpio.error:
            pass
        self.pi.bb_serial_read_open(self.rx, baud, 8)
        self.rx_open = True

    def close_rx(self):
        if self.rx_open:
            self.pi.bb_serial_read_close(self.rx)
            self.rx_open = False

    def write(self, data, baud=BAUD):
        self.pi.wave_add_serial(self.tx, baud, bytes(data))
        wid = self.pi.wave_create()
        try:
            self.pi.wave_send_once(wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.001)
        finally:
            self.pi.wave_delete(wid)

    def read(self, count, timeout=0.2):
        buf = b""
        deadline = time.monotonic() + timeout
        while len(buf) < count and time.monotonic() < deadline:
            n, data = self.pi.bb_serial_read(self.rx)
            if n > 0:
                buf += bytes(data)
            else:
                time.sleep(0.005)
        return buf

    def flush(self):
        self.pi.bb_serial_read(self.rx)

    def close(self):
        self.close_rx()
        self.pi.set_mode(self.tx, pigpio.INPUT)


def query(port, packets, size):
    port.flush()
    if len(packets) == 1:
        port.write([OP_SENSORS, packets[0]])
    else:
        port.write([OP_QUERY_LIST, len(packets)] + list(packets))
    data = port.read(size)
    if len(data) < size:
        raise Failure(EXIT_SHORT_READ, "sensor reply truncated: %d/%d bytes" % (len(data), size))
    return data


def probe(port):
    port.flush()
    port.write([OP_START])
    time.sleep(0.02)
    port.write([OP_SENSORS, PKT_OI_MODE])
    data = port.read(1)
    return data[0] if data and data[0] < len(MODES) else None


def connect(port):
    port.open_rx(BAUD)
    mode = probe(port)
    if mode is None:
        # fresh power-up: the OI listens at 115200, switch it down once, TX only
        port.write([OP_START, OP_BAUD, BAUD_CODE_19200], baud=BAUD_DEFAULT)
        time.sleep(0.1)
        mode = probe(port)
        if mode is None:
            raise Failure(EXIT_NO_RESPONSE, "no response at %d or %d baud, asleep? press CLEAN once"
                          % (BAUD, BAUD_DEFAULT))
        print("link    switched %d -> %d baud" % (BAUD_DEFAULT, BAUD))
    print("link    %d 8N1 mode=%s" % (BAUD, MODES[mode]))


def battery(port):
    size = struct.calcsize(BATTERY_FORMAT)
    state, mv, ma, temp, charge, capacity, sources = struct.unpack(
        BATTERY_FORMAT, query(port, BATTERY_PACKETS, size)
    )
    name = CHARGING_STATES[state] if state < len(CHARGING_STATES) else "unknown %d" % state
    percent = 100.0 * charge / capacity if capacity else 0.0
    print("battery %.2f V %d mA %d C %d/%d mAh (%.0f%%) %s"
          % (mv / 1000.0, ma, temp, charge, capacity, percent, name))
    if sources:
        docked = [n for bit, n in ((0, "internal charger"), (1, "home base")) if sources & (1 << bit)]
        print("battery charging source: %s" % ", ".join(docked))
    return sources


def enter_safe(port):
    port.write([OP_SAFE])
    time.sleep(0.05)
    mode = query(port, [PKT_OI_MODE], 1)[0]
    if mode != MODE_SAFE:
        raise Failure(EXIT_MODE, "expected safe mode, got %s" % MODES[min(mode, 3)])
    print("mode    safe")


def play_song(port):
    port.write([OP_SONG, 0, len(SONG) // 2] + SONG)
    port.write([OP_PLAY, 0])
    time.sleep(sum(SONG[1::2]) / 64.0 + 0.1)
    print("song    played")


def leds_and_buttons(port, seconds):
    print("button  press CLEAN, SPOT or DOCK (keep the Roomba on the floor)")
    start = time.monotonic()
    previous = 0
    misses = 0
    while True:
        t = time.monotonic() - start
        if t > seconds:
            raise Failure(EXIT_NO_BUTTON, "no button press within %d s" % seconds)

        debris = LED_DEBRIS if int(t * 4) % 2 == 0 else 0
        phase = (t % 2.0) / 2.0
        intensity = int(255 * (1 - abs(2 * phase - 1)))
        port.write([OP_LEDS, debris, 0, intensity])

        try:
            buttons, mode = query(port, [PKT_BUTTONS, PKT_OI_MODE], 2)
        except Failure:
            # the bit-bang reader drops a byte now and then, skip that poll
            misses += 1
            if misses > 5:
                raise
            continue
        misses = 0
        # a wheel drop drops us back to passive, where CLEAN would start a cycle
        if mode != MODE_SAFE:
            raise Failure(EXIT_MODE, "left safe mode (%s), wheel drop?" % MODES[min(mode, 3)])
        pressed = buttons & ~previous
        previous = buttons
        names = [name for bit, name in BUTTONS if pressed & (1 << bit)]
        if names:
            print("button  %s" % " ".join(names))
            return
        time.sleep(0.05)


def run(args):
    pi = pigpio.pi()
    if not pi.connected:
        raise Failure(EXIT_PIGPIO, "cannot connect to pigpiod, is it running?")
    port = None
    linked = False
    try:
        port = SoftSerial(pi, args.tx_gpio, args.rx_gpio)
        print("port    tx=GPIO%d rx=GPIO%d" % (args.tx_gpio, args.rx_gpio))

        connect(port)
        linked = True

        if battery(port):
            raise Failure(EXIT_ON_DOCK, "lift the Roomba off the dock, safe mode exits while charging")

        enter_safe(port)
        play_song(port)
        leds_and_buttons(port, 20)
        print("PASS")
        return EXIT_OK
    finally:
        # leave the OI in passive so the Roomba charges and sleeps normally
        if linked:
            try:
                port.write([OP_LEDS, 0, 0, 0])
                port.write([OP_START])
            except pigpio.error:
                pass
        if port is not None:
            port.close()
        pi.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Roomba OI bring-up self-test")
    parser.add_argument("--tx-gpio", type=int, default=23)
    parser.add_argument("--rx-gpio", type=int, default=24)
    args = parser.parse_args(argv)

    try:
        return run(args)
    except Failure as exc:
        print("FAIL    %s" % exc)
        return exc.code
    except pigpio.error as exc:
        print("FAIL    pigpio: %s" % exc)
        return EXIT_PIGPIO


if __name__ == "__main__":
    sys.exit(main())
