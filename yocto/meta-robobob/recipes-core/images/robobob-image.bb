SUMMARY = "RoboBobSLAM robot image"
LICENSE = "MIT"

inherit core-image

IMAGE_FEATURES:append = " ssh-server-openssh"

IMAGE_INSTALL:append = " lidar-selftest roomba-selftest"
