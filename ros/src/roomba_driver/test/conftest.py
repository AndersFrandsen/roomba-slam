import pytest

from roomba_driver import oi


class FakePort:
    """Records writes and answers reads from a queue of replies."""

    def __init__(self, replies=()):
        self.replies = list(replies)
        self.writes = []
        self.rx_baud = None

    def open_rx(self, baud):
        self.rx_baud = baud

    def close_rx(self):
        self.rx_baud = None

    def write(self, data, baud=oi.BAUD):
        self.writes.append((list(data), baud))

    def read(self, count, timeout=0.05):
        return self.replies.pop(0) if self.replies else b""

    def flush(self):
        pass


@pytest.fixture
def port():
    return FakePort()
