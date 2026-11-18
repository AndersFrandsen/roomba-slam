# Yocto image

The image is built with Yocto scarthgap inside the official kas Docker image, so the host needs only Docker.

```bash
just build                 # base image (robobob-image)
just build-ros             # with ROS2 Jazzy (robobob-ros-image)

just flash /dev/sdX                    # newest build
just flash /dev/sdX robobob-image      # a specific image

just shell                 # bitbake shell, for debugging recipes
just shell-ros
```

Log in with `ssh root@robobob-zero2w.local`.

## WiFi

```bash
cp yocto/kas/wifi.yml.example yocto/kas/wifi.yml
```

Fill in SSID, password and country. `just build` picks it up when it exists; the file is gitignored. The Pi Zero 2 W is 2.4 GHz only.

## Images

| Image | Contents |
|-------|----------|
| `robobob-image` | SSH, pigpiod, chrony, `lidar-selftest`, `roomba-selftest` |
| `robobob-ros-image` | The above plus ROS2 Jazzy with CycloneDDS, rplidar_ros, roomba_driver, slam_bringup, slam_toolbox |

ROS installs to `/opt/ros/jazzy` and `/etc/profile.d/ros.sh` sources it on login.

## Layers

All layers are pinned by commit in `kas/`.

- `meta-raspberrypi` - BSP for the Pi Zero 2 W (64-bit)
- `meta-openembedded` - meta-oe, meta-python, meta-networking
- `meta-ros` - ROS2 Jazzy, added by `kas/ros.yml`
- `meta-robobob` - machine config, images, self-tests, pigpio and the ROS recipes

The image keeps the `poky` distro with sysvinit rather than meta-ros's `ros2` distro, which switches to systemd and connman.

slam_toolbox is skipped by meta-ros because its RViz panel needs Qt and X11. meta-robobob builds it without the panel, and SuiteSparse uses the reference BLAS from lapack instead of openblas.

## References

- [Yocto Project docs](https://docs.yoctoproject.org/)
- [kas](https://kas.readthedocs.io/)
- [meta-ros](https://github.com/ros/meta-ros)
- [meta-raspberrypi](https://github.com/agherzan/meta-raspberrypi)
