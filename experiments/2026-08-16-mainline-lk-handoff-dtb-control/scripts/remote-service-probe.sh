#!/bin/sh
set -eu
export LC_ALL=C
BB=/bin/busybox
$BB printf "%s\\n" __GAEL_SERVICE_BEGIN__
$BB printf "boot_id_sha256="; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d " " -f 1
$BB printf "uptime_seconds="; $BB cut -d " " -f 1 /proc/uptime
$BB printf "dev_mem="; if $BB test -e /dev/mem; then $BB printf "present\\n"; else $BB printf "absent\\n"; fi
$BB printf "pstore_files="; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf "block_mounts="; $BB grep -Ec "^/dev/(mmc|sd|nvme)" /proc/mounts || true
$BB printf "reboot_sha256="; $BB sha256sum /bin/reboot | $BB cut -d " " -f 1
$BB printf "%s\\n" __GAEL_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf "%s\\n" __GAEL_DMESG_BASE64_END__
$BB printf "post_probe_boot_id_sha256="; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d " " -f 1
$BB printf "%s\\n" __GAEL_SERVICE_END__
