"""pigpio bit-bang UART: DMA waveforms for TX, DMA sampling for RX."""

import time

import pigpio

from .oi import BAUD


WAKE_PULSE = 0.2


class SoftSerial:
    def __init__(self, pi, tx, rx, brc=None):
        self.pi = pi
        self.tx = tx
        self.rx = rx
        self.brc = brc
        self.rx_open = False
        pi.set_mode(tx, pigpio.OUTPUT)
        pi.write(tx, 1)
        if brc is not None:
            # BRC idles high, a low pulse wakes the Roomba
            pi.set_mode(brc, pigpio.OUTPUT)
            pi.write(brc, 1)
        pi.wave_clear()

    def wake(self):
        self.pi.write(self.brc, 0)
        time.sleep(WAKE_PULSE)
        self.pi.write(self.brc, 1)

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

    def read(self, count, timeout=0.05):
        buf = b""
        deadline = time.monotonic() + timeout
        while len(buf) < count and time.monotonic() < deadline:
            n, data = self.pi.bb_serial_read(self.rx)
            if n > 0:
                buf += bytes(data)
            else:
                time.sleep(0.002)
        return buf

    def flush(self):
        self.pi.bb_serial_read(self.rx)

    def close(self):
        self.close_rx()
        self.pi.set_mode(self.tx, pigpio.INPUT)
