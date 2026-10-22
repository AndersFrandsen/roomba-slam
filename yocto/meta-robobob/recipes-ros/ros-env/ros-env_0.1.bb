SUMMARY = "ROS2 shell environment for login shells"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ros.sh"
S = "${WORKDIR}"

inherit allarch

RDEPENDS:${PN} = "ros-workspace"

do_install() {
    install -D -m 0644 ${WORKDIR}/ros.sh ${D}${sysconfdir}/profile.d/ros.sh
}
