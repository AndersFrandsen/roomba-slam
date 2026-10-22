kas_image := "ghcr.io/siemens/kas/kas:5.5-debian-bookworm"
kas_work  := "/repo/yocto"

default:
    @just --list

# build base image for Pi Zero 2 W
build:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas build "$(just _cfg)"

# build image with ROS2 Jazzy
build-ros:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas build "$(just _cfg kas/ros.yml)"

# drop into a configured bitbake shell
shell:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas shell "$(just _cfg)"

# bitbake shell with meta-ros
shell-ros:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas shell "$(just _cfg kas/ros.yml)"

# kas config plus local WiFi credentials if set up
[private]
_cfg *extra:
    #!/usr/bin/env bash
    set -euo pipefail
    cfg="kas/robobob-zero2w.yml"
    for f in {{extra}}; do cfg="$cfg:$f"; done
    if [ -f yocto/kas/wifi.yml ]; then
        cfg="$cfg:kas/wifi.yml"
    else
        echo "warning: yocto/kas/wifi.yml missing, image will have no WiFi credentials" >&2
        echo "         cp yocto/kas/wifi.yml.example yocto/kas/wifi.yml" >&2
    fi
    echo "$cfg"

# ROS2 Jazzy shell on this machine
ros *args:
    #!/usr/bin/env bash
    set -euo pipefail
    robot="${ROBOT:-robobob-zero2w.local}"
    ip=$(getent ahostsv4 "$robot" | awk 'NR==1 {print $1}' || true)
    [ -n "$ip" ] || echo "warning: cannot resolve $robot, relying on multicast discovery" >&2
    docker build -q -t robobob-ros -f docker/Dockerfile.ros docker > /dev/null
    docker run --rm -it --net=host \
        -e ROBOT_IP="$ip" \
        -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v "$PWD:/repo" -w /repo \
        robobob-ros {{ if args == "" { "bash" } else { "bash -ic '" + args + "'" } }}

# flash SD card: just flash /dev/sdX [image], defaults to the newest build
flash disk image="":
    #!/usr/bin/env bash
    set -euo pipefail
    deploy=yocto/build/tmp/deploy/images/robobob-zero2w
    if [ -n "{{image}}" ]; then
        wic="$deploy/{{image}}-robobob-zero2w.rootfs.wic.bz2"
    else
        wic=$(ls -t "$deploy"/*-robobob-zero2w.rootfs.wic.bz2 | head -n 1)
    fi
    echo "flashing $(readlink -f "$wic") -> {{disk}}"
    sudo bzcat "$wic" | sudo dd of={{disk}} bs=4M conv=fsync status=progress

[private]
_kas +args:
    mkdir -p yocto/build yocto/downloads yocto/sstate-cache
    chmod 777 yocto yocto/build yocto/downloads yocto/sstate-cache
    docker run --rm -it \
        -v "$PWD:/repo" \
        -w "{{kas_work}}" \
        -e "DL_DIR={{kas_work}}/downloads" \
        -e "SSTATE_DIR={{kas_work}}/sstate-cache" \
        {{kas_image}} {{args}}
