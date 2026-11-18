# Host container

A ROS2 Jazzy container for the development host, with RViz, teleop, slam_toolbox's RViz panel and `map_saver_cli`. The host needs only Docker; `just ros` builds the image on first use.

```bash
just ros                       # bash shell
just ros <command>             # run one command
just rviz                      # RViz with map, scan, TF and the slam_toolbox panel
just ros ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

The repo is mounted at `/repo`, the working directory. The container runs as root, so files it writes (such as `maps/`) are owned by root.

`just` drops the quotes around its arguments. Wrap a command with quoted arguments in single quotes:

```bash
just ros 'ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: /home/root/maps/home}"'
```

## Discovery

The container uses CycloneDDS with host networking. `just ros` resolves `robobob-zero2w.local` (or `$ROBOT`) and adds it as a unicast peer in `cyclonedds.xml`, so discovery doesn't depend on multicast over WiFi. Both sides use the default `ROS_DOMAIN_ID`.

## Troubleshooting

- **RViz can't connect to the display:** `just ros` runs `xhost +SI:localuser:root` to let the container's root user use X. This needs `xhost` installed on the host.
- **Mesa or DRI errors (`failed to load driver: iris`):** the container has no GPU access. Use software rendering with `LIBGL_ALWAYS_SOFTWARE=1`, or pass the GPU with `--device /dev/dri`.
- **No scan points in RViz:** check `/scan` on the Pi. If the lidar spins but publishes nothing, restart the launch.

## References

- [ROS2 Jazzy docs](https://docs.ros.org/en/jazzy/)
- [CycloneDDS with ROS2](https://docs.ros.org/en/jazzy/Installation/RMW-Implementations/DDS-Implementations/Working-with-Eclipse-CycloneDDS.html)
- [RViz user guide](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html)
- [teleop_twist_keyboard](https://github.com/ros2/teleop_twist_keyboard)
