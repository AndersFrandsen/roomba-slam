import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    launch_dir = os.path.join(get_package_share_directory("slam_bringup"), "launch")

    return LaunchDescription([
        # serialized pose graph without extension; empty maps while navigating
        DeclareLaunchArgument("map", default_value=""),
        IncludeLaunchDescription(os.path.join(launch_dir, "slam.launch.py"),
                                 launch_arguments={"map": LaunchConfiguration("map")}.items()),
        IncludeLaunchDescription(os.path.join(launch_dir, "nav2.launch.py")),
    ])
