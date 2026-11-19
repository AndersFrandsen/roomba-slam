from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare

# package, plugin, name, remappings
SERVERS = [
    ("nav2_controller", "nav2_controller::ControllerServer", "controller_server",
     [("cmd_vel", "cmd_vel_nav")]),
    ("nav2_planner", "nav2_planner::PlannerServer", "planner_server", []),
    ("nav2_behaviors", "behavior_server::BehaviorServer", "behavior_server",
     [("cmd_vel", "cmd_vel_nav")]),
    ("nav2_velocity_smoother", "nav2_velocity_smoother::VelocitySmoother", "velocity_smoother",
     [("cmd_vel", "cmd_vel_nav"), ("cmd_vel_smoothed", "cmd_vel")]),
    ("nav2_bt_navigator", "nav2_bt_navigator::BtNavigator", "bt_navigator", []),
    ("nav2_lifecycle_manager", "nav2_lifecycle_manager::LifecycleManager",
     "lifecycle_manager_navigation", []),
]


def generate_launch_description():
    params = LaunchConfiguration("params_file")

    return LaunchDescription([
        DeclareLaunchArgument(
            "params_file",
            default_value=PathJoinSubstitution([FindPackageShare("slam_bringup"), "config", "nav2.yaml"]),
        ),
        # one process for all servers saves a lot of RAM on the Pi
        ComposableNodeContainer(
            name="nav2_container",
            namespace="",
            package="rclcpp_components",
            executable="component_container_isolated",
            # the costmaps are sub-nodes and only see the container's params file
            parameters=[params],
            composable_node_descriptions=[
                ComposableNode(package=package, plugin=plugin, name=name,
                               parameters=[params], remappings=remappings)
                for package, plugin, name, remappings in SERVERS
            ],
            output="screen",
        ),
    ])
