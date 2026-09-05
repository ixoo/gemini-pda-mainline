#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck disable=SC2016 # Awk fields are intentionally literal.
# Close the consumed no-workload session; no temperature or frequency read.
set -eu
BB=/bin/busybox
[ "$($BB uname -r)" = 7.1.3-gemini-thermal-snapshot ]
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = ac3d28c7-69fe-4ccb-8145-cad85cbd0653 ]
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-7 ]
[ "$($BB cat /sys/devices/system/cpu/offline)" = 8-9 ]
record=$($BB od -An -tx1 -v /sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity | $BB tr -d '[:space:]')
[ "$record" = 7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552 ]
status=$($BB cat /sys/bus/platform/devices/a72-admission-controller/gemini_admission/status | $BB sha256sum)
[ "${status%% *}" = 6a5fd459cd5b7ed4e309dd4942e116428980f6229c9ee434240c4c70396d43eb ]
[ "$($BB cat /sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot_status)" = 'abi=1 attempts=3 limit=3' ]
[ "$($BB dmesg | $BB grep -Fc GEMINI_A72_FREQUENCY_OBSERVATION_V1)" = 0 ]
[ "$($BB awk '$1 ~ /^\/dev\// {n++} END {print n+0}' /proc/mounts)" = 0 ]
$BB printf '%s\n' __THERMAL_ATTRIBUTION_SHUTDOWN_BEGIN__
$BB printf '%s\n' source_boot_id=ac3d28c7-69fe-4ccb-8145-cad85cbd0653
$BB printf '%s\n' kernel_release=7.1.3-gemini-thermal-snapshot
$BB printf 'record_identity=%s\n' "$record"
$BB printf '%s\n' cpu_online=0-7 cpu_offline=8-9 snapshot_attempts=3 frequency_attempts=0
$BB printf '%s\n' lifecycle=unchanged-pristine block_mounts=0 shutdown_requested=yes
$BB printf '%s\n' __THERMAL_ATTRIBUTION_SHUTDOWN_END__
$BB sync
$BB poweroff -f
