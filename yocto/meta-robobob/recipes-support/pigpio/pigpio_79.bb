SUMMARY = "pigpio GPIO library and daemon"
HOMEPAGE = "https://github.com/joan2937/pigpio"
LICENSE = "Unlicense"
LIC_FILES_CHKSUM = "file://UNLICENCE;md5=61287f92700ec1bdf13bc86d8228cd13"

SRC_URI = " \
    git://github.com/joan2937/pigpio.git;protocol=https;branch=master \
    file://pigpiod.init \
"
SRCREV = "c33738a320a3e28824af7807edafda440952c05d"
S = "${WORKDIR}/git"

inherit cmake python3-dir update-rc.d

INITSCRIPT_NAME = "pigpiod"
INITSCRIPT_PARAMS = "defaults 90"

EXTRA_OECMAKE = "-DCMAKE_DISABLE_FIND_PACKAGE_Python=TRUE"

do_install:append() {
    rm -rf ${D}${prefix}/man
    install -D -m 0755 ${WORKDIR}/pigpiod.init ${D}${sysconfdir}/init.d/pigpiod
    install -D -m 0644 ${S}/pigpio.py ${D}${PYTHON_SITEPACKAGES_DIR}/pigpio.py
}

PACKAGES =+ "python3-pigpio"
FILES:python3-pigpio = "${PYTHON_SITEPACKAGES_DIR}/pigpio.py"
RDEPENDS:python3-pigpio = "python3-core python3-io python3-threading"

FILES_SOLIBSDEV = ""
FILES:${PN} += "${libdir}/*.so"
INSANE_SKIP:${PN} += "dev-so"
