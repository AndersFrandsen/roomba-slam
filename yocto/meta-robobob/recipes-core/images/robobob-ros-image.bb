require robobob-image.bb

SUMMARY = "RoboBobSLAM robot image with ROS2"

IMAGE_INSTALL:append = " \
    ros-core \
    ros-workspace \
    rmw-cyclonedds-cpp \
    demo-nodes-cpp \
    ros-env \
    tf2-ros \
    tf2-ros-py \
"

IMAGE_ROOTFS_EXTRA_SPACE = "2097152"
