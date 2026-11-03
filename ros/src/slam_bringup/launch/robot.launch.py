import subprocess

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

LIDAR_MOTOR_GPIO = "18"


def lidar_motor(on):
    # rplidar_ros switches the motor via DTR, which the PL011 doesn't have
    def run(context):
        result = subprocess.run(["pigs", "w", LIDAR_MOTOR_GPIO, "1" if on else "0"],
                                capture_output=True, text=True)
        if result.returncode != 0:
            return [LogInfo(msg="lidar motor: pigs failed: " + result.stderr.strip())]
        return []
    return OpaqueFunction(function=run)


def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare("slam_bringup"), "config"])
    laser_args = ["laser_x", "laser_y", "laser_z", "laser_yaw"]

    return LaunchDescription(
        [DeclareLaunchArgument(name, default_value="0.0") for name in laser_args]
        + [
            lidar_motor(True),
            RegisterEventHandler(OnShutdown(on_shutdown=[lidar_motor(False)])),
            Node(
                package="rplidar_ros",
                executable="rplidar_composition",
                name="rplidar",
                parameters=[PathJoinSubstitution([config, "rplidar.yaml"])],
                output="screen",
            ),
            Node(
                package="roomba_driver",
                executable="roomba_driver",
                name="roomba_driver",
                parameters=[PathJoinSubstitution([config, "roomba.yaml"])],
                output="screen",
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="laser_tf",
                arguments=[
                    "--x", LaunchConfiguration("laser_x"),
                    "--y", LaunchConfiguration("laser_y"),
                    "--z", LaunchConfiguration("laser_z"),
                    "--yaw", LaunchConfiguration("laser_yaw"),
                    "--frame-id", "base_link",
                    "--child-frame-id", "laser",
                ],
            ),
        ]
    )
