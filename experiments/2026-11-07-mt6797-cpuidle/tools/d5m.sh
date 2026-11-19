#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Stage D5m of experiments/2026-11-07-mt6797-cpuidle ("Request D5m"): a
# deliberate watchdog reset with the SODI program idle after returned
# periods, to learn what the SPM's reset latches hold when the PCM's FSM
# state and r13 are known. Run as root, detached, on a fresh boot with no SODI
# module loaded:
#
#   setsid nohup sh d5m.sh /path/to/mt6797-spm-sleep.ko </dev/null >/dev/null 2>&1 &
#
# The module is loaded without its cpuidle driver (sodi_idle=0) and with the
# PCM timer as the only wake source, the configuration that has never hung.
# Once the screen blanks and CPU1-9 are offline, it runs three periods, logs
# the FSM state and r13 each left (the module reads them after the return),
# then opens /dev/watchdog0 and never pings it. The kernel stops pinging too,
# so the hardware watchdog resets the chip about 31 s later, with no period
# in flight. The owner catches the bootloader and selects boot2 without
# powering off; the latches are then read before any module loads. The log
# is /var/tmp/d5m.log. Each period's return line is logged and synced right
# after the period, so a hang can be placed in period 1, 2 or 3.
#
# D5M_NO_EVENT=1 loads the module with sodi_no_event=1 (0825): periods arm no
# resource event. The script logs whether the Wi-Fi driver is loaded; to run
# with the radios unloaded, remove the Wi-Fi and CONSYS modules first.
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

ARGS="sodi_idle=0 sodi_wake_src=0"
if [ "${D5M_NO_EVENT:-0}" = 1 ]; then
	grep -q 'sodi_no_event' "$KO" || stop "the module has no sodi_no_event parameter (0825)"
	ARGS="$ARGS sodi_no_event=1"
fi
log "wlan modules: $(lsmod | awk '/wlan|wmt|consys|gen4m/ {printf "%s ", $1}')"
# shellcheck disable=SC2086
insmod "$KO" $ARGS || stop "insmod failed"
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

# Three periods; each must return, or this is not the passing setup.
n=0
tries=0
while [ "$n" -lt 3 ]; do
	tries=$((tries + 1))
	[ "$tries" -gt 20 ] && stop "fewer than three periods in 20 tries"
	# The synced line comes a second before the period, so its write-back
	# does not refuse the period on MSDC (as in D5h).
	log "    period $((n + 1)), try $tries"
	sleep 1
	echo 200 >"$SODI" 2>/dev/null || continue
	n=$((n + 1))
	dmesg | grep 'sodi cg: returned' | tail -n 1 |
		sed 's/.*\(returned=[0-9]*\).*\(fsm=[0-9a-f]*\).* \(r13=[0-9a-f]*\).*/    \1 \2 \3/'
	sync
done
[ "$(dmesg | grep -c 'sodi cg: returned=1')" -ge 3 ] || stop "a period did not return"
log "three periods returned; opening the watchdog, reset expected in about 31 s"

# From here the watchdog is ours and never pinged, and no period runs.
exec 3>/dev/watchdog0
sleep 120
log "no reset within 120 s"
