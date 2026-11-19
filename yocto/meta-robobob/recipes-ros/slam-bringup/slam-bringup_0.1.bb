SUMMARY = "Launch files and parameters for the RoboBob robot"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

FILESEXTRAPATHS:prepend := "${THISDIR}/../../../../ros/src:"
SRC_URI = "file://slam_bringup"
S = "${WORKDIR}/slam_bringup"

ROS_BPN = "slam_bringup"

inherit ros_distro_jazzy

RDEPENDS:${PN} = " \
    launch \
    launch-ros \
    nav2-behaviors \
    nav2-bt-navigator \
    nav2-controller \
    nav2-lifecycle-manager \
    nav2-navfn-planner \
    nav2-planner \
    nav2-regulated-pure-pursuit-controller \
    nav2-velocity-smoother \
    rclcpp-components \
    roomba-driver \
    rplidar-ros \
    slam-toolbox \
    tf2-ros \
    pigpio \
"

ROS_BUILD_TYPE = "ament_python"
inherit ros_${ROS_BUILD_TYPE}
