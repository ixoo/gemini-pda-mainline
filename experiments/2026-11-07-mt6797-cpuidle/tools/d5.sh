#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Stage D5 of experiments/2026-11-07-mt6797-cpuidle ("Request D5"): SODI as
# CPU0's idle state (0816), on an image with CONFIG_CPU_IDLE and the menu
# governor. Run as root, detached, cable out, Wi-Fi joined and quiet:
#
#   setsid nohup sh d5.sh /path/to/mt6797-spm-sleep.ko </dev/null >/dev/null 2>&1 &
#
# The script waits for the desktop's idle blank, takes CPU1-9 offline and
# runs four windows of D5_WINDOW seconds (default 180) with the SODI state
# off, on, off, on (cpu0/cpuidle/state1/disable). Each window logs the
# battery's charge counter, the state's usage and time, the module's
# counters (/sys/kernel/debug/sodi_idle) and the interrupt counts. The log
# is /var/tmp/d5.log, synced after every line. Nobody touches the device
# and no SSH connection is made until the log says "done".
#
# Hypothesis: with the screen dark and CPU0 alone, the menu governor enters
# SODI by itself, memory stays intact, and the current falls against the off
# windows by the share of time spent in SODI.
# Unique observation: autonomous SODI residency, its entry and exit cost,
# why entries are refused, which lines end the periods, and the current.
# Stops: the module's "stopped" counter set (a period with no return); a
# new WARNING, Oops, BUG or RCU stall; the screen lit or CPU1-9 back, which
# ends the run; a wrong hash, after which the script syncs and powers off.
set -u

KO=${1:-}
WINDOW=${D5_WINDOW:-180}
LOG=/var/tmp/d5.log
MHZ=/tmp/cpu-mhz
MHZ_SHA=22a0acfc
FW=/lib/firmware/mediatek/mt6797/pcm_sodi.bin
FW_SHA=dda8cca1e110d57137afb8ef4957da758c19d38db45ea2bb30bc7133cc122ae4
FW_SUSPEND=/lib/firmware/mediatek/mt6797/pcm_suspend.bin
FW_SUSPEND_SHA=d6e8a0b8851e78e95891c995605ffbf210eade56583b14cf6b4a67e7d770f4e0
STATS=/sys/kernel/debug/sodi_idle
STATE=/sys/devices/system/cpu/cpu0/cpuidle/state1
USB=11271000.usb
CPUS=/sys/devices/system/cpu
TAKEN=""
USB_CONTROL=""

exec >>"$LOG" 2>&1

log() {
	echo "$(date +%T) $*"
	sync
}

new_dmesg() {
	dmesg | tail -n +"$((DMESG0 + 1))"
}

restore() {
	[ -w "$STATE/disable" ] && echo 1 >"$STATE/disable" && log "SODI state off"
	if [ -n "$TAKEN" ]; then
		for cpu in $TAKEN; do
			echo 1 >"$CPUS/cpu$cpu/online" || log "cpu$cpu did not come back"
		done
		log "CPUs back: $(cat "$CPUS/online")"
	fi
	if [ -n "$USB_CONTROL" ]; then
		echo "$USB_CONTROL" >"/sys/bus/platform/devices/$USB/power/control" &&
			log "gadget power/control back to $USB_CONTROL"
	fi
	log "taint at the end: $(cat /proc/sys/kernel/tainted)"
}

stop() {
	log "STOP: $*"
	[ -r "$STATS" ] && sed 's/^/    /' "$STATS"
	new_dmesg | grep -E 'sodi|spm|WARNING|Oops|BUG|rcu' | tail -n 20
	restore
	log "done, stopped"
	exit 1
}

hash() {
	"$MHZ" 0 hash | awk '{print $2}'
}

check_hash() {
	h=$(hash)
	if [ "$h" != "$REF" ]; then
		echo 1 >"$STATE/disable"
		log "STOP: hash $h after $1, reference $REF; powering off"
		new_dmesg | tail -n 30
		sync
		systemctl poweroff
		exit 1
	fi
	log "    hash equal"
}

check_dmesg() {
	if new_dmesg | grep -qE 'WARNING|Oops|BUG:|rcu.*stall|detected stalls'; then
		stop "a kernel warning, Oops or stall since the start"
	fi
}

blank() {
	[ "$(cat /sys/class/backlight/*/bl_power 2>/dev/null | head -n 1)" = 4 ]
}

stopped() {
	[ "$(sed -n 's/^stopped //p' "$STATS")" != 0 ]
}

# One window with the SODI state off (1) or on (0).
window() {
	name=$1
	echo "$2" >"$STATE/disable" || stop "state1/disable not written"
	sleep 10
	c0=$(cat "$GAUGE/charge_counter")
	t0=$(date +%s)
	u0=$(cat "$STATE/usage")
	r0=$(cat "$STATE/time")
	i0=$(awk '/^ *[0-9]+:/ { s += $2 } END { print s }' /proc/interrupts)
	log "$name start, SODI usage $u0"
	t=0
	while [ "$t" -lt "$WINDOW" ]; do
		sleep 10
		t=$((t + 10))
		blank || stop "the screen lit in window $name"
		[ "$(cat "$CPUS/online")" = 0 ] || stop "CPUs came back in window $name"
		stopped && stop "a SODI period did not return in window $name"
		# In SODI windows, a synced line every 10 s dates a reset to 10 s.
		if [ "$2" = 0 ]; then
			log "    $name +$t s: SODI usage $(cat "$STATE/usage"), time $(cat "$STATE/time") us," \
				"$(grep -E '^(tried|entered|stopped|error) ' "$STATS" | tr '\n' ' ')"
		fi
	done
	c1=$(cat "$GAUGE/charge_counter")
	t1=$(date +%s)
	u1=$(cat "$STATE/usage")
	r1=$(cat "$STATE/time")
	i1=$(awk '/^ *[0-9]+:/ { s += $2 } END { print s }' /proc/interrupts)
	dt=$((t1 - t0))
	# charge_counter in uAh: mA = duAh * 3600 / dt / 1000
	log "$name: $dt s, $(( (c0 - c1) * 36 / dt / 10 )) mA by the charge counter," \
		"SODI entries $((u1 - u0)), SODI time $(( (r1 - r0) / 1000 )) ms," \
		"interrupts $((i1 - i0)), battery $(cat "$GAUGE/capacity") %"
	if [ "$2" = 0 ]; then
		sed 's/^/    /' "$STATS"
		grep -E '^ *[0-9]+:' /proc/interrupts | awk '$2 > 0' | sed 's/^/    irq /'
	fi
	check_hash "window $name"
	check_dmesg
}

# ---- checks before anything changes ----
DMESG0=$(dmesg | wc -l)
log "D5 start, $(uname -r), boot $(cat /proc/sys/kernel/random/boot_id), taint $(cat /proc/sys/kernel/tainted)"
[ "$(id -u)" -eq 0 ] || stop "not root"
[ -f "$KO" ] || stop "no module at '$KO'"
log "module $(sha256sum "$KO" | cut -c1-16)…, vermagic $(modinfo -F vermagic "$KO")"
case $(modinfo -F vermagic "$KO") in
"$(uname -r) "*) ;;
*) stop "the module's vermagic does not match $(uname -r)" ;;
esac
grep -q 'sodi_idle_max_ms' "$KO" || stop "the module has no SODI idle state (0816)"
[ -d "$CPUS/cpuidle" ] || stop "this kernel has no cpuidle core (CONFIG_CPU_IDLE)"
[ "$(sha256sum "$FW" | cut -d' ' -f1)" = "$FW_SHA" ] || stop "$FW missing or its hash differs"
[ "$(sha256sum "$FW_SUSPEND" | cut -d' ' -f1)" = "$FW_SUSPEND_SHA" ] ||
	stop "$FW_SUSPEND missing or its hash differs"
case $(sha256sum "$MHZ" | cut -c1-8) in
"$MHZ_SHA") ;;
*) stop "$MHZ missing or not $MHZ_SHA" ;;
esac
GAUGE=""
for ps in /sys/class/power_supply/*; do
	if [ "$(cat "$ps/type")" = Battery ]; then
		[ -r "$ps/charge_counter" ] && GAUGE=$ps
		continue
	fi
	[ "$(cat "$ps/online" 2>/dev/null)" = 1 ] && stop "external power on $(basename "$ps"): pull the cable"
done
[ -n "$GAUGE" ] || stop "no battery with a charge counter"
[ -d /sys/module/mt6797_gate_unused ] || modprobe mt6797-gate-unused || stop "mt6797-gate-unused did not load"
# A module whose cpuidle driver is registered (0816 on) holds itself and
# cannot be unloaded: it needs a fresh boot before the next run.
if [ -d /sys/module/mt6797_spm_sleep ] &&
	[ "$(cat /sys/module/mt6797_spm_sleep/refcnt)" != 0 ]; then
	stop "the running SPM module is in use (its cpuidle driver); boot fresh first"
fi
log "battery $(cat "$GAUGE/capacity") %"

log "waiting 30 s for the SSH session to end"
sleep 30

# ---- setup ----
ctl=/sys/bus/platform/devices/$USB/power/control
USB_CONTROL=$(cat "$ctl")
echo auto >"$ctl" || stop "power/control not set"
sleep 10
log "gadget power/control auto (was $USB_CONTROL), runtime $(cat "/sys/bus/platform/devices/$USB/power/runtime_status")"

if [ -d /sys/module/mt6797_spm_sleep ]; then
	rmmod mt6797_spm_sleep || stop "the running SPM module did not unload"
fi
insmod "$KO" || stop "insmod failed"
new_dmesg | grep -E 'mt6797-spm-sleep|pcm_' | sed 's/^/    /'
log "cpuidle driver $(cat "$CPUS/cpuidle/current_driver"), governor $(cat "$CPUS/cpuidle/current_governor_ro" 2>/dev/null || cat "$CPUS/cpuidle/current_governor")"
[ "$(cat "$STATE/name" 2>/dev/null)" = SODI ] || stop "no SODI state at $STATE"
[ "$(cat "$STATE/disable")" = 1 ] || stop "the SODI state is not off after loading"
[ -r "$STATS" ] || stop "no $STATS"
log "sodi_cirq_level $(cat /sys/module/mt6797_spm_sleep/parameters/sodi_cirq_level)," \
	"sodi_wake_src $(printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_wake_src)")," \
	"exit latency $(cat "$STATE/latency") us, residency $(cat "$STATE/residency") us"

log "waiting up to 300 s for the idle blank; do not touch any input"
t=0
until blank; do
	t=$((t + 1))
	[ "$t" -gt 300 ] && stop "no blank within 300 s"
	sleep 1
done
log "blanked"

for cpu in 9 8 7 6 5 4 3 2 1; do
	[ "$(cat "$CPUS/cpu$cpu/online" 2>/dev/null)" = 1 ] || continue
	echo 0 >"$CPUS/cpu$cpu/online" || stop "cpu$cpu did not go offline"
	TAKEN="$cpu $TAKEN"
done
log "online: $(cat "$CPUS/online")"
sleep 5
REF=$(hash)
log "hash reference $REF"

# ---- windows ----
window off1 1
window on1 0
window off2 1
window on2 0

# ---- restore ----
restore
check_dmesg
log "done"
