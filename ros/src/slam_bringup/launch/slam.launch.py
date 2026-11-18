import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler)
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition

LOCALIZATION = {
    "mode": "localization",
    "map_start_at_dock": True,
    "scan_buffer_size": 3,
    "loop_match_minimum_chain_size": 3,
}


def slam_toolbox(context):
    config = os.path.join(get_package_share_directory("slam_bringup"), "config", "slam.yaml")
    map_file = LaunchConfiguration("map").perform(context)

    if map_file:
        executable = "localization_slam_toolbox_node"
        params = [config, dict(LOCALIZATION, map_file_name=map_file)]
    else:
        executable = "async_slam_toolbox_node"
        params = [config]

    node = LifecycleNode(
        package="slam_toolbox",
        executable=executable,
        name="slam_toolbox",
        namespace="",
        parameters=params + [{"use_sim_time": False}],
        output="screen",
    )

    def change_state(transition):
        return EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(node),
                                           transition_id=transition))

    return [
        node,
        change_state(Transition.TRANSITION_CONFIGURE),
        RegisterEventHandler(OnStateTransition(
            target_lifecycle_node=node, start_state="configuring", goal_state="inactive",
            entities=[change_state(Transition.TRANSITION_ACTIVATE)],
        )),
    ]


def generate_launch_description():
    robot = os.path.join(get_package_share_directory("slam_bringup"), "launch", "robot.launch.py")

    return LaunchDescription([
        # serialized pose graph without extension; empty starts a new map
        DeclareLaunchArgument("map", default_value=""),
        IncludeLaunchDescription(robot),
        OpaqueFunction(function=slam_toolbox),
    ])
