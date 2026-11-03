import math

import pytest

from roomba_driver.odometry import COUNTS_PER_REV, Odometry, count_delta, wheel_speeds

DIAMETER = 0.072
BASE = 0.235


def test_count_delta_wraps():
    assert count_delta(65535, 0) == 1
    assert count_delta(0, 65535) == -1
    assert count_delta(65000, 300) == 836
    assert count_delta(100, 50) == -50


def test_straight_line():
    odom = Odometry(DIAMETER, BASE)
    odom.update(0, 0, 0.0)
    counts = int(COUNTS_PER_REV * 10)
    odom.update(counts, counts, 1.0)
    distance = counts * math.pi * DIAMETER / COUNTS_PER_REV
    assert odom.x == pytest.approx(distance)
    assert odom.y == pytest.approx(0.0)
    assert odom.theta == pytest.approx(0.0)
    assert odom.linear == pytest.approx(distance)


def test_straight_line_across_wrap():
    odom = Odometry(DIAMETER, BASE)
    odom.update(65500, 65500, 0.0)
    odom.update(100, 100, 0.05)
    assert odom.x == pytest.approx(136 * odom.metres_per_count)


def test_spin_in_place_quarter_turn():
    odom = Odometry(DIAMETER, BASE)
    odom.update(0, 0, 0.0)
    arc = BASE / 2.0 * math.pi / 2.0
    counts = arc / odom.metres_per_count
    steps = 50
    for i in range(1, steps + 1):
        n = int(round(counts * i / steps))
        odom.update((-n) % 65536, n, 0.05)
    assert odom.theta == pytest.approx(math.pi / 2.0, abs=0.01)
    assert math.hypot(odom.x, odom.y) == pytest.approx(0.0, abs=1e-3)


def test_reset_counts_ignores_jump():
    odom = Odometry(DIAMETER, BASE)
    odom.update(0, 0, 0.0)
    odom.reset_counts()
    odom.update(30000, 30000, 0.05)
    assert odom.x == 0.0


def test_wheel_speeds_forward_and_turn():
    assert wheel_speeds(0.2, 0.0, BASE) == (200, 200)
    right, left = wheel_speeds(0.0, 1.0, BASE)
    assert right == -left == round(BASE / 2.0 * 1000)


def test_wheel_speeds_clamp_keeps_ratio():
    right, left = wheel_speeds(1.0, 2.0, BASE)
    assert right == 500
    assert left / right == pytest.approx((1.0 - BASE) / (1.0 + BASE), abs=0.01)
