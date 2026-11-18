FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-build-without-rviz-plugin.patch"

# package.xml only says LGPL, the LICENSE file is 2.1
LICENSE = "LGPL-2.1-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=1803fa9c2c3ce8cb06b4861d75310742"

NO_RVIZ = "qtbase rviz-common rviz-default-plugins rviz-ogre-vendor rviz-rendering"
ROS_BUILD_DEPENDS:remove = "${NO_RVIZ}"
ROS_EXPORT_DEPENDS:remove = "${NO_RVIZ}"
# ceres is a static library, linked into the solver plugin
ROS_EXEC_DEPENDS:remove = "${NO_RVIZ} ceres-solver"

# only pulled in through rviz upstream
ROS_BUILD_DEPENDS += "rclcpp-components"
ROS_EXEC_DEPENDS += "rclcpp-components"

inherit pkgconfig
ROS_BUILDTOOL_DEPENDS += "rosidl-default-generators-native"
