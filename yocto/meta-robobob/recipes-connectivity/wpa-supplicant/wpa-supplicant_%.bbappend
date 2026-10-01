# Bake WiFi credentials into /etc/wpa_supplicant.conf
# Credentials come from WIFI_SSID / WIFI_PASSWORD, set in yocto/kas/wifi.yml

FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += "file://wpa_supplicant.conf.in"

WIFI_SSID ??= ""
WIFI_PASSWORD ??= ""
WIFI_COUNTRY ??= "DK"

do_install:append() {
    if [ -z "${WIFI_SSID}" ]; then
        bbwarn "WIFI_SSID is unset: image will ship without WiFi credentials. See yocto/kas/wifi.yml.example"
    else
        install -m 0600 ${WORKDIR}/wpa_supplicant.conf.in ${D}${sysconfdir}/wpa_supplicant.conf
        sed -i -e "s|@WIFI_COUNTRY@|${WIFI_COUNTRY}|" \
               -e "s|@WIFI_SSID@|${WIFI_SSID}|" \
               -e "s|@WIFI_PASSWORD@|${WIFI_PASSWORD}|" \
               ${D}${sysconfdir}/wpa_supplicant.conf
    fi
}

# Re-run do_install when the credentials change, otherwise sstate serves a stale
# rootfs with the old SSID baked in.
do_install[vardeps] += "WIFI_SSID WIFI_PASSWORD WIFI_COUNTRY"
