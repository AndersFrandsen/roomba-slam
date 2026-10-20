SUMMARY = "Roomba 600 Open Interface bring-up self-test"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://roomba_selftest.py"
S = "${WORKDIR}"

inherit allarch

RDEPENDS:${PN} = "python3-core python3-pigpio pigpio"

do_install() {
    install -D -m 0755 ${WORKDIR}/roomba_selftest.py ${D}${bindir}/roomba-selftest
}
