#!/usr/bin/env bash

# Read-only, sanitized inventory of Gemini/Gemian hardware userspace.

set -u
export LC_ALL=C

heading() {
  printf '\n===== %s =====\n' "$1"
}

heading "selected Android build properties"
if [[ -r /system/build.prop ]]; then
  grep -E '^(ro\.build\.id|ro\.build\.version\.release|ro\.product\.(model|brand|name|device|cpu\.abi|cpu\.abilist)|ro\.board\.platform|ro\.mediatek\.(chip_ver|platform|version\.(branch|release|sdk)|project\.path))=' /system/build.prop || true
fi

heading "MT6797 HALs"
for path in /system/vendor/lib/hw/*.mt6797.so /system/vendor/lib64/hw/*.mt6797.so; do
  [[ -e "${path}" ]] || continue
  target="$(readlink "${path}" 2>/dev/null || true)"
  bytes="$(stat -Lc '%s' "${path}" 2>/dev/null || printf unavailable)"
  digest="$(sha256sum "${path}" 2>/dev/null | awk '{print $1}')"
  needed="$(readelf -d "${path}" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' | paste -sd, -)"
  printf '%s|bytes=%s|sha256=%s|link=%s|needed=%s\n' \
    "${path}" "${bytes}" "${digest:-unavailable}" "${target}" "${needed}"
done

heading "selected vendor executables and libraries"
find /system/vendor/bin /system/vendor/lib /system/vendor/lib64 -maxdepth 1 -type f -printf '%p|%s\n' 2>/dev/null \
  | grep -Ei '/(ccci|md_|emd|mtk|wmt|wifi|wlan|ril|radio|gsm|gps|agps|sensor|thermal|power|battery|charger|camera|audio|nvram|spm|factory|meta|atci|mobile_log|lib(cam|mtk|ccci|ril|nvram|bluetooth|thermal|m4u|ion_mtk|gralloc|ged|dpframework|gpu))' \
  | sort || true

heading "relevant Gemian packages"
dpkg-query -W 2>/dev/null \
  | grep -Ei '^(lxc-android|libhybris|drihybris|glamor-hybris|xserver-xorg-video-hwcomposer|pulseaudio-module-droid|ofono|telepathy-ofono|libgrilio|connman-plugin-suspend-wmtwifi|repowerd|gemian-leds|hybris-usb|gemian-modular-kernel)(:[^[:space:]]+)?[[:space:]]' \
  | sort || true

heading "active hardware-stack process names"
ps -eo comm= 2>/dev/null \
  | grep -Ei '^(lxc-start|connmand|ofonod|gemian-leds|repowerd|Xorg|pulseaudio|surfaceflinger|cameraserver|sensorservice|ccci|mtk|wmt)' \
  | sort -u || true
