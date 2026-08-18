#!/bin/sh
set -eu
export LC_ALL=C
BB=/bin/busybox

$BB printf '%s\n' __DA921X_LKRO_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf 'cmdline='; $BB cat /proc/cmdline
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'udc_devices='; $BB find /sys/class/udc -mindepth 1 -maxdepth 1 2>/dev/null | $BB wc -l
$BB printf 'gpio_matrix_keyboards='; $BB grep -c 'Name="gpio-matrix-keypad"' /proc/bus/input/devices || true
$BB printf 'da921x_i2c_clients='; $BB find /sys/bus/i2c/devices -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf 'reboot_sha256='; $BB sha256sum /bin/reboot | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_LKRO_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf '%s\n' __DA921X_LKRO_DMESG_BASE64_END__
$BB printf 'post_probe_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_LKRO_END__
