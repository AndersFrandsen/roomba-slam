# roomba_driver

rclpy node for the Roomba Open Interface over the pigpio software UART. It polls the OI at 20 Hz, drives the wheels from `cmd_vel` and publishes odometry. It is started by `slam_bringup`'s `robot.launch.py`.

## Topics

| Topic | Type | Notes |
|-------|------|-------|
| `/cmd_vel` (in) | `geometry_msgs/Twist` | Capped to `max_linear` and `max_angular`; wheels stop `cmd_timeout` after the last command |
| `/odom` | `nav_msgs/Odometry` | Plus TF `odom → base_link` |
| `/bumper` | `std_msgs/UInt8` | Raw OI packet 7: bit 0/1 bump right/left, bit 2/3 wheel drop right/left |
| `/battery` | `sensor_msgs/BatteryState` | Every `battery_period` |
| `/oi_mode` | `std_msgs/String` | Latched; `safe` while driving |

## Parameters

Set in `slam_bringup/config/roomba.yaml`.

| Parameter | Value | Notes |
|-----------|-------|-------|
| `tx_gpio`, `rx_gpio` | 23, 24 | |
| `brc_gpio` | 25 | Pulsed low to wake a sleeping Roomba |
| `wheel_diameter` | 0.0695 m | Calibrated |
| `wheel_base` | 0.2365 m | Calibrated |
| `rate` | 20 Hz | Sensor poll and odom rate |
| `battery_period` | 1.0 s | |
| `cmd_timeout` | 0.5 s | |
| `max_linear` | 0.3 m/s | |
| `max_angular` | 1.5 rad/s | |
| `odom_frame`, `base_frame` | `odom`, `base_link` | |

## Modes

The driver enters Safe mode at start, unless a charger is present. The firmware drops to Passive on a wheel drop, a cliff or the charger; the next non-zero `cmd_vel` brings it back to Safe. On exit it stops the wheels and leaves the Roomba in Passive so the battery charges.

This Roomba reports the OI mode one higher than the spec. The driver reads the mode right after START, where it must be Passive, and subtracts the offset.

## Waking

When the OI doesn't answer, the driver pulls BRC low for 200 ms and probes again on every tick for 5 s; the OI answers anywhere from at once to about 3 s after the pulse.

## Calibration

Drive with teleop and read `/odom`:

- `wheel_diameter`: drive a measured straight line (1 m or more) and scale by measured / reported distance.
- `wheel_base`: spin several full turns back to a mark and scale by reported / actual angle.

## Tests

```bash
just ros "cd ros && colcon build && colcon test && colcon test-result --verbose"
```

## References

- [Create 2 / Roomba 600 Open Interface spec (PDF)](https://cdn.hackaday.io/files/1835247851890816/2021-04-13_iRobot_Roomba_600_Open_Interface_Spec-3.pdf): opcodes, sensor packets, modes
- [REP 105](https://www.ros.org/reps/rep-0105.html): the `map`, `odom` and `base_link` frames
