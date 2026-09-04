#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck disable=SC2016
# Awk field expressions below are deliberately single-quoted.
# Exactly one admitted snapshot read. Arguments are a validated boot UUID and 1..3.
set -eu
BB=/bin/busybox
[ "$#" = 2 ] || exit 2
boot=$1
attempt=$2
case "$attempt" in 1|2|3) ;; *) exit 2 ;; esac
[ "$($BB uname -r)" = 7.1.3-gemini-thermal-snapshot ]
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$boot" ]
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-7 ]
[ "$($BB cat /sys/devices/system/cpu/offline)" = 8-9 ]
sysfs_options=$($BB awk '$2 == "/sys" {print $4}' /proc/mounts)
case ",$sysfs_options," in *,ro,*) ;; *) exit 2 ;; esac
case ",$sysfs_options," in *,rw,*) exit 2 ;; esac
record=$($BB od -An -tx1 -v /sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity | $BB tr -d '[:space:]')
[ "$record" = 7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552 ]
status=$($BB cat /sys/bus/platform/devices/a72-admission-controller/gemini_admission/status | $BB sha256sum | $BB awk '{print $1}')
[ "$status" = 6a5fd459cd5b7ed4e309dd4942e116428980f6229c9ee434240c4c70396d43eb ]
count=0
snapshot=
for item in /sys/bus/platform/devices/*/mt6797_temperature_snapshot; do
    [ -r "$item" ] || continue
    count=$((count + 1))
    snapshot=$item
done
[ "$count" = 1 ]
[ "$snapshot" = /sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot ]
[ "$($BB stat -c '%a' "$snapshot")" = 400 ]
[ "$($BB stat -c '%a' "${snapshot}_status")" = 400 ]
[ "$($BB cat "${snapshot}_status")" = "abi=1 attempts=$((attempt - 1)) limit=3" ]
$BB printf '%s\n' __THERMAL_SNAPSHOT_READ_BEGIN__
$BB printf 'boot_id=%s\nrequested_attempt=%s\n' "$boot" "$attempt"
$BB printf '%s\n' __THERMAL_SNAPSHOT_RECORD_BEGIN__
$BB cat "$snapshot"
$BB printf '%s\n' __THERMAL_SNAPSHOT_RECORD_END__
$BB printf 'observer_status='; $BB cat "${snapshot}_status"
$BB printf 'boot_id_after='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf '%s\n' __THERMAL_SNAPSHOT_READ_END__
