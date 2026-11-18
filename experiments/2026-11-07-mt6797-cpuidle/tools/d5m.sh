#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Stage D5m of experiments/2026-11-07-mt6797-cpuidle ("Request D5m"): a
# deliberate watchdog reset while the SODI program sits in its main wait, to
# learn what the SPM's reset latches hold for that known position. Run as
# root, detached, on a fresh boot with no SODI module loaded:
#
#   setsid nohup sh d5m.sh /path/to/mt6797-spm-sleep.ko </dev/null >/dev/null 2>&1 &
#
# The module is loaded without its cpuidle driver (sodi_idle=0) and with the
# PCM timer as the only wake source, the configuration that has never hung.
# Once the screen blanks and CPU1-9 are offline, the script opens
# /dev/watchdog0 and never pings it, so the kernel stops pinging too and the
# hardware watchdog resets the chip about 31 s later. Meanwhile it runs
# 2000 ms SODI periods back to back, so the reset almost surely lands in a
# period's main wait. The owner catches the bootloader and selects boot2
# without powering off; the latches are then read before any module loads.
# The log is /var/tmp/d5m.log; nothing is synced after the watchdog opens,
# since a card write would refuse the periods.
set -u

KO=${1:-}
LOG=/var/tmp/d5m.log
SODI=/sys/kernel/debug/sodi_once_ms
CPUS=/sys/devices/system/cpu
TAKEN=""

exec >>"$LOG" 2>&1

log() {
	echo "$(date +%T) $*"
	sync
}

stop() {
	log "STOP: $*"
	for cpu in $TAKEN; do
		echo 1 >"$CPUS/cpu$cpu/online"
	done
	log "done, stopped"
	exit 1
}

blank() {
	[ "$(cat /sys/class/backlight/*/bl_power 2>/dev/null | head -n 1)" = 4 ]
}

log "D5m start, $(uname -r), boot $(cat /proc/sys/kernel/random/boot_id), taint $(cat /proc/sys/kernel/tainted)"
[ "$(id -u)" -eq 0 ] || stop "not root"
[ -f "$KO" ] || stop "no module at '$KO'"
case $(modinfo -F vermagic "$KO") in
"$(uname -r) "*) ;;
*) stop "the module's vermagic does not match $(uname -r)" ;;
esac
grep -q 'sodi_idle_states' "$KO" || stop "the module has no sodi_idle parameter (0819)"
[ -d /sys/module/mt6797_spm_sleep ] && stop "an SPM module is loaded: boot fresh first"
[ -c /dev/watchdog0 ] || stop "no /dev/watchdog0"
log "watchdog0 $(cat /sys/class/watchdog/watchdog0/state 2>/dev/null), timeout $(cat /sys/class/watchdog/watchdog0/timeout 2>/dev/null) s"

log "waiting 30 s for the SSH session to end"
sleep 30

insmod "$KO" sodi_idle=0 sodi_wake_src=0 || stop "insmod failed"
[ -e "$SODI" ] || stop "no $SODI: the SODI program was not loaded"
[ "$(cat "$CPUS/cpuidle/current_driver" 2>/dev/null)" = mt6797_sodi ] &&
	stop "the cpuidle driver registered despite sodi_idle=0"
log "sodi_wake_src $(printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_wake_src)")"

log "waiting up to 300 s for the idle blank; do not touch any input"
t=0
until blank; do
	t=$((t + 1))
	[ "$t" -gt 300 ] && stop "no blank within 300 s"
	sleep 1
done
for cpu in 9 8 7 6 5 4 3 2 1; do
	[ "$(cat "$CPUS/cpu$cpu/online" 2>/dev/null)" = 1 ] || continue
	echo 0 >"$CPUS/cpu$cpu/online" || stop "cpu$cpu did not go offline"
	TAKEN="$cpu $TAKEN"
done
log "online: $(cat "$CPUS/online")"

# One trial period first: it must return, or this is not the passing setup.
sleep 1
echo 2000 >"$SODI" || stop "the trial period did not run"
dmesg | grep -q 'sodi cg: returned=1' || stop "the trial period did not return"
log "trial period returned; opening the watchdog, reset expected in about 31 s"

# From here the watchdog is ours and never pinged. Periods run back to back
# until the reset; a refused period is retried after the MSDC idle delay.
exec 3>/dev/watchdog0
while :; do
	echo 2000 >"$SODI" 2>/dev/null || sleep 0.1
done
