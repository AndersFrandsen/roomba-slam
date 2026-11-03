"""Differential-drive odometry and kinematics for the Roomba."""

import math

COUNTS_PER_REV = 508.8


def count_delta(previous, current):
    """Signed difference between two 16-bit encoder readings."""
    return (current - previous + 32768) % 65536 - 32768


def wheel_speeds(linear, angular, wheel_base, limit=500):
    """Twist in m/s and rad/s to (right, left) wheel speeds in mm/s.

    Both wheels are scaled down together so the turn radius survives clamping.
    """
    right = (linear + angular * wheel_base / 2.0) * 1000.0
    left = (linear - angular * wheel_base / 2.0) * 1000.0
    peak = max(abs(right), abs(left))
    if peak > limit:
        right *= limit / peak
        left *= limit / peak
    return int(round(right)), int(round(left))


class Odometry:
    def __init__(self, wheel_diameter, wheel_base):
        self.metres_per_count = math.pi * wheel_diameter / COUNTS_PER_REV
        self.wheel_base = wheel_base
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.linear = 0.0
        self.angular = 0.0
        self._counts = None

    def reset_counts(self):
        """Forget the last encoder reading, e.g. after the link dropped."""
        self._counts = None
        self.linear = 0.0
        self.angular = 0.0

    def update(self, left, right, dt):
        if self._counts is None:
            self._counts = (left, right)
            return
        d_left = count_delta(self._counts[0], left) * self.metres_per_count
        d_right = count_delta(self._counts[1], right) * self.metres_per_count
        self._counts = (left, right)

        distance = (d_left + d_right) / 2.0
        rotation = (d_right - d_left) / self.wheel_base
        heading = self.theta + rotation / 2.0
        self.x += distance * math.cos(heading)
        self.y += distance * math.sin(heading)
        self.theta = math.atan2(math.sin(self.theta + rotation), math.cos(self.theta + rotation))

        if dt > 0:
            self.linear = distance / dt
            self.angular = rotation / dt
