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
    rplidar-ros \
    roomba-driver \
    slam-bringup \
    slam-toolbox \
    nav2-behaviors \
    nav2-bt-navigator \
    nav2-controller \
    nav2-lifecycle-manager \
    nav2-navfn-planner \
    nav2-planner \
    nav2-regulated-pure-pursuit-controller \
    nav2-velocity-smoother \
"

IMAGE_ROOTFS_EXTRA_SPACE = "2097152"
