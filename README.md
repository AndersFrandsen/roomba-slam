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
