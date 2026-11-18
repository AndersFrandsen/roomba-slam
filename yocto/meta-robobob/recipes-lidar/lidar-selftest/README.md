# lidar-selftest

Bring-up check for the RPLIDAR A1, without ROS. Use it to verify wiring, UART config and motor control. Installed in both images.

```bash
lidar-selftest
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `/dev/ttyAMA0` | Serial port |
| `--motor-gpio` | `18` | GPIO line wired to MOTOCTL |

## Checks

1. Environment - `serial0` points at the PL011, no kernel console on the UART, no under-voltage
2. Port - opens and locks the serial port (fails if something else holds it)
3. Device info - model, firmware, hardware revision and serial number
4. Health - resets the lidar once if it reports an error
5. Motor off - scans with MOTOCTL low and warns if the head is still spinning
6. Motor on - drives MOTOCTL high, scans and checks rate, coverage and dropped bytes

## Example output

```
root@robobob-zero2w:~# lidar-selftest
env     serial0 -> /soc/serial@7e201000 (pl011)
port    /dev/ttyAMA0 115200 8N1 raw
info    model=0x18 fw=1.28 hw=5 serial=81839a86c0e09cc9a2e09df713513079
health  OK code=0x0000
motor   /dev/gpiochip0 pinctrl-bcm2835 line 18
scan    4534 nodes 16 revs 7.4 Hz coverage 36/36 valid 78% dropped 0.0%
PASS
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Pass |
| 10-13 | Port missing, permission denied, busy, termios setup failed |
| 20-22 | No response, framing error, short read |
| 30-31 | Health warning, health error |
| 40 | GPIO error |
| 50 | Scan did not start |
| 51 | Motor not spinning |
| 52 | Incomplete sweep |
| 53 | Too many dropped bytes |

The port is busy while `robot.launch.py` runs; stop it first.

## References

- [RPLIDAR A1 specifications](https://www.slamtec.com/en/Lidar/A1Spec)
- [rplidar_sdk](https://github.com/slamtec/rplidar_sdk), SLAMTEC's reference implementation of the serial protocol
