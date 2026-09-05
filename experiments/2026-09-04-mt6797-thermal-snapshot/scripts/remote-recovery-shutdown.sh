#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck disable=SC2016 # Awk fields are intentionally literal.
# Close the consumed attribution session; no temperature or frequency read.
set -eu
BB=/bin/busybox
[ "$($BB uname -r)" = 7.1.3-gemini-thermal-snapshot ]
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = 056703de-bf29-4956-891e-ff69d19fdd68 ]
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-9 ]
[ "$($BB cat /sys/devices/system/cpu/offline)" = "" ]
record=$($BB od -An -tx1 -v /sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity | $BB tr -d '[:space:]')
[ "$record" = 7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552 ]
status=$($BB cat /sys/bus/platform/devices/a72-admission-controller/gemini_admission/status | $BB sha256sum)
[ "${status%% *}" = 8aac24ee30576659fe7d4ffb5e58d17dab087165bf1dc3e6f6d800593e310044 ]
[ "$($BB cat /sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot_status)" = 'abi=1 attempts=3 limit=3' ]
[ "$($BB dmesg | $BB grep -Fc GEMINI_A72_FREQUENCY_OBSERVATION_V1)" = 3 ]
[ "$($BB awk '$1 ~ /^\/dev\// {n++} END {print n+0}' /proc/mounts)" = 0 ]
$BB printf '%s\n' __THERMAL_RECOVERY_SHUTDOWN_BEGIN__
$BB printf '%s\n' source_boot_id=056703de-bf29-4956-891e-ff69d19fdd68
$BB printf '%s\n' kernel_release=7.1.3-gemini-thermal-snapshot
$BB printf 'record_identity=%s\n' "$record"
$BB printf '%s\n' cpu_online=0-9 cpu_offline= snapshot_attempts=3 frequency_attempts=3
$BB printf '%s\n' lifecycle=unchanged-terminal block_mounts=0 shutdown_requested=yes
$BB printf '%s\n' __THERMAL_RECOVERY_SHUTDOWN_END__
$BB sync
$BB poweroff -f
