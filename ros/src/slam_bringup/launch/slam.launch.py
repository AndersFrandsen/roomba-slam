from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bringup = FindPackageShare("slam_bringup")
    toolbox = FindPackageShare("slam_toolbox")

    return LaunchDescription([
        IncludeLaunchDescription(PathJoinSubstitution([bringup, "launch", "robot.launch.py"])),
        IncludeLaunchDescription(
            PathJoinSubstitution([toolbox, "launch", "online_async_launch.py"]),
            launch_arguments={
                "slam_params_file": PathJoinSubstitution([bringup, "config", "slam.yaml"]),
                "use_sim_time": "false",
            }.items(),
        ),
    ])
