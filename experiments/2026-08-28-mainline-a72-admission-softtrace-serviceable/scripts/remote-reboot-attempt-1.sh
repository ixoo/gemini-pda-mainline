#!/bin/sh

# Return the exact completed attempt-1 boot to Gemian only when both its live
# boot identity and the inherited validated reboot wrapper are unchanged.
set -eu
export LC_ALL=C
BB=/bin/busybox
EXPECTED_BOOT_ID=fa6df396-c037-42cc-ba14-1ef98771cfe0
EXPECTED_REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7

live_boot_id=$($BB cat /proc/sys/kernel/random/boot_id)
# The awk program must receive its literal field expression.
# shellcheck disable=SC2016
live_reboot_sha256=$($BB sha256sum /bin/reboot | $BB awk '{ print $1 }')
$BB printf '%s\n' __GEMINI_A72_NATIVE_REBOOT_BEGIN__
$BB printf 'expected_boot_id=%s\n' "$EXPECTED_BOOT_ID"
$BB printf 'live_boot_id=%s\n' "$live_boot_id"
$BB printf 'expected_reboot_sha256=%s\n' "$EXPECTED_REBOOT_SHA256"
$BB printf 'live_reboot_sha256=%s\n' "$live_reboot_sha256"
if [ "$live_boot_id" != "$EXPECTED_BOOT_ID" ] ||
   [ "$live_reboot_sha256" != "$EXPECTED_REBOOT_SHA256" ]; then
	$BB printf '%s\n' request_authorized=no
	$BB printf '%s\n' __GEMINI_A72_NATIVE_REBOOT_END__
	exit 93
fi
$BB printf '%s\n' request_authorized=yes
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' sync_requested=no
$BB printf '%s\n' request_count=1
$BB printf '%s\n' __GEMINI_A72_NATIVE_REBOOT_END__
/bin/reboot
exit 94
