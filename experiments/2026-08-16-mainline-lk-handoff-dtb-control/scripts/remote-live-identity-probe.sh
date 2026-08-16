#!/bin/sh
set -eu
export LC_ALL=C
BB=/bin/busybox
$BB printf "%s\\n" __GAEL_DTB_CONTROL_LIVE_BEGIN__
$BB printf "kernel_release="; $BB uname -r
$BB printf "architecture="; $BB uname -m
$BB printf "boot_id_sha256="; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d " " -f 1
$BB printf "cmdline="; $BB cat /proc/cmdline
$BB printf "cpu_possible="; $BB cat /sys/devices/system/cpu/possible
$BB printf "cpu_present="; $BB cat /sys/devices/system/cpu/present
$BB printf "cpu_online="; $BB cat /sys/devices/system/cpu/online
$BB printf "cpu_offline="; $BB cat /sys/devices/system/cpu/offline
$BB printf "model="; $BB tr "\\000" " " </sys/firmware/devicetree/base/model; $BB printf "\\n"
$BB printf "compatible="; $BB tr "\\000" "," </sys/firmware/devicetree/base/compatible; $BB printf "\\n"
$BB printf "%s\\n" __GAEL_ZONES_BASE64_BEGIN__
$BB dd if=/dev/mem bs=4096 skip=279739 count=4 2>/dev/null | $BB base64
$BB printf "%s\\n" __GAEL_ZONES_BASE64_END__
$BB printf "post_read_boot_id_sha256="; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d " " -f 1
$BB printf "%s\\n" __GAEL_DTB_CONTROL_LIVE_END__
