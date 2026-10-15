# Roomba SLAM

## Project Overview

RoboBob SLAM converts the 600-series vacuum into a SLAM-capable vacuum cleaner. A Raspberry Pi Zero 2 W reads LiDAR (Light Detection and Ranging) and drives the Roomba via its Open Interface (OI) serial protocol, running ROS2 nodes on a Yocto-built Linux image.

**Hardware stack:**
- **Robot base:** iRobot Roomba 600 (Create 2 OI compatible)
- **Compute power:** Raspberry Pi Zero 2 W (BCM2710A1, Cortex-A53 quad-core, 512MB RAM)
- **Lidar:** SLAMTEC RPLIDAR A1 (model A1M8) - 360°, 12m range, 5.5Hz-10Hz scan rate, UART/USB

## Repository Layout (draft)

```
yocto/          # Yocto build environment (kas config, custom layer)
  meta-robobob/ # Project-specific layer: recipes, machine configs, images
ros/            # ROS2 workspace
  src/
    roomba_driver/   # Roomba OI serial node
    rplidar_ros/     # Submodule or recipe for SLAMTEC driver
```

## Yocto Build

The target OS is built with Yocto. Builds run inside the official kas Docker image - no local Yocto or kas install needed, only Docker.

```bash
# Phase 1 - base image
just build

# Flash SD card
just flash /dev/sdX

# Drop into a bitbake shell (debug recipes, run bitbake commands manually)
just shell
```

**Yocto layers:**
- `meta-raspberrypi` - BSP for the Raspberry Pi Zero 2 W target
- `meta-openembedded` - dependencies
- `meta-robobob` - project image recipe and machine customizations

## LiDAR Self-Test

Use `lidar-selftest`, a bring-up check for the RPLIDAR A1. Does not rely on ROS. Use it to verify wiring, UART config and motor control.

**Wiring on the Raspberry Pi Zero 2 W:**

| Signal | Pi pin |
|--------|--------|
| LIDAR RX | GPIO14 (TX) |
| LIDAR TX | GPIO15 (RX) |
| LIDAR MOTOCTL | GPIO18 |

With `dtoverlay=disable-bt` the lidar is on `/dev/ttyAMA0` at 115200 8N1.

**Checks:**
1. Environment - `serial0` points at the PL011, no kernel console on the UART, no under-voltage
2. Port - opens and locks the serial port (fails if something else holds it)
3. Device info - model, firmware, hardware revision and serial number
4. Health - resets the lidar once if it reports an error
5. Motor off - scans with MOTOCTL low and warns if the head is still spinning
6. Motor on - drives MOTOCTL high, scans and checks 

```bash
# run with defaults (/dev/ttyAMA0, motor on GPIO18)
lidar-selftest
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `/dev/ttyAMA0` | Serial port |
| `--motor-gpio` | `18` | GPIO line wired to MOTOCTL |

**Example output:**

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

**Exit codes:**

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
