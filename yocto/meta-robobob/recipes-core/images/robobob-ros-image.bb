require robobob-image.bb

SUMMARY = "RoboBobSLAM robot image with ROS2"

IMAGE_INSTALL:append = " \
    ros-core \
    ros-workspace \
    rmw-cyclonedds-cpp \
    demo-nodes-cpp \
    ros-env \
"
