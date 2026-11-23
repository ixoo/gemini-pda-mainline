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
#
# D5M_PCM_WDT=1 loads it with sodi_pcm_wdt=1 (0826): the PCM watchdog, in
# wake mode, ends a stuck period 2 s after its timer (stage D5p).
# D5M_RESET=0 skips the deliberate watchdog reset: after the three periods
# the CPUs come back and the script ends.
# D5M_ARGS="..." appends module parameters to the insmod line (stage D5aj),
# each read back into the log; with sodi_crumbs=1 the console log level is
# raised to 8 so the crumbs reach the RAM console. D5M_MM=1|2 writes
# sodi_mm_cg after the blank, as d4.sh's D4_MM.
# D5M_SETTLE=N waits N seconds after the CPUs go offline before period 1
# (stage D5ak); the default 0 keeps the start about 1 s after.
# D5M_MS=N runs N ms periods instead of 200 (stage D5al).
# D5M_USB_AUTO=1 sets the USB gadget's power/control to auto and waits 10 s,
# so with the cable out MTU3 runtime-suspends and the SSUSB clocks gate, as
# d4.sh does; the old value is put back at the end. D5M_GATE_UNUSED=1 loads
# mt6797-gate-unused if it is not loaded, as d4.sh does (stage D5am). Either
# way the script logs both states before insmod.
# D5M_HASH=1 runs d4.sh's memory reference, a cpu-mhz hash on CPU0, after the
# settle and before period 1, as d4.sh does before window C (stage D5an).
set -u

KO=${1:-}
LOG=/var/tmp/d5m.log
SODI=/sys/kernel/debug/sodi_once_ms
CPUS=/sys/devices/system/cpu
TAKEN=""
USB=/sys/bus/platform/devices/11271000.usb/power
USB_CONTROL=""

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
	usb_back
	log "done, stopped"
	exit 1
}

usb_back() {
	[ -n "$USB_CONTROL" ] && echo "$USB_CONTROL" >"$USB/control" &&
		log "gadget power/control back to $USB_CONTROL"
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

case ${D5M_GATE_UNUSED:-0} in
0) ;;
1) [ -d /sys/module/mt6797_gate_unused ] || modprobe mt6797-gate-unused ||
	stop "mt6797-gate-unused did not load" ;;
*) stop "D5M_GATE_UNUSED must be 0 or 1" ;;
esac
case ${D5M_USB_AUTO:-0} in
0) ;;
1)
	USB_CONTROL=$(cat "$USB/control") || stop "no gadget power/control"
	echo auto >"$USB/control" || stop "power/control not set"
	sleep 10
	;;
*) stop "D5M_USB_AUTO must be 0 or 1" ;;
esac
log "gadget power/control $(cat "$USB/control" 2>/dev/null), runtime $(cat "$USB/runtime_status" 2>/dev/null)${USB_CONTROL:+ (was $USB_CONTROL)}"
log "gate-unused $([ -d /sys/module/mt6797_gate_unused ] && echo loaded || echo absent)"

ARGS="sodi_idle=0 sodi_wake_src=0"
if [ "${D5M_NO_EVENT:-0}" = 1 ]; then
	grep -q 'sodi_no_event' "$KO" || stop "the module has no sodi_no_event parameter (0825)"
	ARGS="$ARGS sodi_no_event=1"
fi
if [ "${D5M_PCM_WDT:-0}" = 1 ]; then
	grep -q 'sodi_pcm_wdt' "$KO" || stop "the module has no sodi_pcm_wdt parameter (0826)"
	ARGS="$ARGS sodi_pcm_wdt=1"
fi
ARGS="$ARGS ${D5M_ARGS:-}"
case ${D5M_MM:-0} in
0) ;;
1 | 2) grep -q 'sodi_mm_cg' "$KO" || stop "the module has no sodi_mm_cg parameter (0837)" ;;
*) stop "D5M_MM must be 1 or 2" ;;
esac
case $ARGS in
*sodi_crumbs=1*) echo 8 >/proc/sys/kernel/printk || stop "could not raise the console log level" ;;
esac
log "insmod args: $ARGS"
log "wlan modules: $(lsmod | awk '/wlan|wmt|consys|gen4m/ {printf "%s ", $1}')"
# shellcheck disable=SC2086
insmod "$KO" $ARGS || stop "insmod failed"
[ -e "$SODI" ] || stop "no $SODI: the SODI program was not loaded"
[ "$(cat "$CPUS/cpuidle/current_driver" 2>/dev/null)" = mt6797_sodi ] &&
	stop "the cpuidle driver registered despite sodi_idle=0"
for p in $ARGS; do
	p=${p%%=*}
	log "$p $(cat "/sys/module/mt6797_spm_sleep/parameters/$p" 2>/dev/null || echo unreadable)"
done
log "printk $(cat /proc/sys/kernel/printk)"
log "sodi_wake_src $(printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_wake_src)")"

log "waiting up to 300 s for the idle blank; do not touch any input"
t=0
until blank; do
	t=$((t + 1))
	[ "$t" -gt 300 ] && stop "no blank within 300 s"
	sleep 1
done
if [ "${D5M_MM:-0}" != 0 ]; then
	echo "$D5M_MM" >/sys/module/mt6797_spm_sleep/parameters/sodi_mm_cg ||
		stop "sodi_mm_cg=$D5M_MM was refused"
	dmesg | grep -o 'sodi mm: .*' | tail -n 4 | sed 's/^/    /'
fi
for cpu in 9 8 7 6 5 4 3 2 1; do
	[ "$(cat "$CPUS/cpu$cpu/online" 2>/dev/null)" = 1 ] || continue
	echo 0 >"$CPUS/cpu$cpu/online" || stop "cpu$cpu did not go offline"
	TAKEN="$cpu $TAKEN"
done
log "online: $(cat "$CPUS/online")"
case ${D5M_SETTLE:-0} in
'' | *[!0-9]*) stop "D5M_SETTLE must be a whole number of seconds" ;;
0) ;;
*)
	log "settling ${D5M_SETTLE} s before period 1"
	sleep "$D5M_SETTLE"
	;;
esac
case ${D5M_MS:-200} in
'' | 0 | *[!0-9]*) stop "D5M_MS must be a whole number of ms, at least 1" ;;
esac
case ${D5M_HASH:-0} in
0) ;;
1)
	[ "$(sha256sum /tmp/cpu-mhz 2>/dev/null | cut -c1-8)" = 22a0acfc ] ||
		stop "/tmp/cpu-mhz missing or not 22a0acfc"
	log "hash $(/tmp/cpu-mhz 0 hash | awk '{print $2}')"
	;;
*) stop "D5M_HASH must be 0 or 1" ;;
esac
log "periods of ${D5M_MS:-200} ms"

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
	echo "${D5M_MS:-200}" >"$SODI" 2>/dev/null || continue
	n=$((n + 1))
	dmesg | grep 'sodi cg: returned' | tail -n 1 | sed 's/.*sodi cg: /    /'
	sync
done
[ "$(dmesg | grep -c 'sodi cg: returned=1')" -ge 3 ] || stop "a period did not return"
if [ "${D5M_RESET:-1}" = 0 ]; then
	for cpu in $TAKEN; do
		echo 1 >"$CPUS/cpu$cpu/online"
	done
	usb_back
	log "three periods returned; no deliberate reset (D5M_RESET=0); done"
	exit 0
fi
log "three periods returned; opening the watchdog, reset expected in about 31 s"

# From here the watchdog is ours and never pinged, and no period runs.
exec 3>/dev/watchdog0
sleep 120
log "no reset within 120 s"
