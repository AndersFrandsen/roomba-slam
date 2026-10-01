kas_image := "ghcr.io/siemens/kas/kas:5.5-debian-bookworm"
kas_work  := "/repo/yocto"

default:
    @just --list

# build base image for Pi Zero 2 W
build:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas build "$(just _cfg)"

# drop into a configured bitbake shell
shell:
    #!/usr/bin/env bash
    set -euo pipefail
    just _kas shell "$(just _cfg)"

# kas config, plus local WiFi credentials if set up
[private]
_cfg:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f yocto/kas/wifi.yml ]; then
        echo "kas/robobob-zero2w.yml:kas/wifi.yml"
    else
        echo "warning: yocto/kas/wifi.yml missing, image will have no WiFi credentials" >&2
        echo "         cp yocto/kas/wifi.yml.example yocto/kas/wifi.yml" >&2
        echo "kas/robobob-zero2w.yml"
    fi

# flash SD card: just flash /dev/sdX
flash disk:
    sudo bzcat yocto/build/tmp/deploy/images/robobob-zero2w/robobob-image-robobob-zero2w.rootfs.wic.bz2 \
        | sudo dd of={{disk}} bs=4M conv=fsync status=progress

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
