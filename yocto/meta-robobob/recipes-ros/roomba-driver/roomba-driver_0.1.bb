SUMMARY = "Roomba 600 Open Interface driver node"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

FILESEXTRAPATHS:prepend := "${THISDIR}/../../../../ros/src:"
SRC_URI = "file://roomba_driver"
S = "${WORKDIR}/roomba_driver"

ROS_BPN = "roomba_driver"

inherit ros_distro_jazzy

RDEPENDS:${PN} = " \
    rclpy \
    geometry-msgs \
    nav-msgs \
    sensor-msgs \
    std-msgs \
    tf2-ros-py \
    python3-pigpio \
"

ROS_BUILD_TYPE = "ament_python"
inherit ros_${ROS_BUILD_TYPE}
