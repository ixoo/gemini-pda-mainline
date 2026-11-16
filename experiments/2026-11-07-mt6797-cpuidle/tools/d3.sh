#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Stage D3 of experiments/2026-11-07-mt6797-cpuidle ("Request D3"): the first
# SODI periods on mainline, one at a time from /sys/kernel/debug/sodi_once_ms,
# on the card root. Run as root, detached, with the cable out:
#
#   setsid nohup sh d3.sh [/path/to/mt6797-spm-sleep.ko] </dev/null >/dev/null 2>&1 &
#
# Without a path it loads the image's own module. It waits 30 s so the SSH
# session can end, then unloads the radios (Wi-Fi goes, so SSH goes), lets
# MTU3 power down at runtime (power/control "auto"; with the cable out the
# SSUSB clocks then gate), or with D3_UNBIND=1 unbinds the gadget instead
# (image 131), loads the module, waits for the desktop's idle blank, takes
# CPU1-9 offline and runs the periods, each followed by a memory hash. Then
# it puts everything back and Wi-Fi returns. The log is /var/tmp/d3.log,
# synced after every line.
#
# Hypothesis: the SODI program runs and returns on its timer in CG and PDN
# mode while the system is otherwise awake, with memory intact.
# Unique observation: the first SODI period on mainline, and whether PDN mode
# returns as CG mode does.
# Stops: a refusal or failed write; returned=0; a new WARNING, Oops, BUG or RCU
# stall; a wrong hash, after which the script syncs and powers off, since
# memory may be corrupt.
set -u

KO=${1:-}
LOG=/var/tmp/d3.log
MHZ=/tmp/cpu-mhz
MHZ_SHA=22a0acfc
FW=/lib/firmware/mediatek/mt6797/pcm_sodi.bin
FW_SHA=dda8cca1e110d57137afb8ef4957da758c19d38db45ea2bb30bc7133cc122ae4
SODI=/sys/kernel/debug/sodi_once_ms
PARAM=/sys/module/mt6797_spm_sleep/parameters
RADIOS=/usr/lib/systemd/system-sleep/gemini-radios
USB=11271000.usb
CPUS=/sys/devices/system/cpu
TAKEN=""
UNBOUND=""
RADIOS_DOWN=""
USB_CONTROL=""

exec >>"$LOG" 2>&1

log() {
	echo "$(date +%T) $*"
	sync
}

# Lines the kernel logged since the start of the run.
new_dmesg() {
	dmesg | tail -n +"$((DMESG0 + 1))"
}

restore() {
	if [ -n "$TAKEN" ]; then
		for cpu in $TAKEN; do
			echo 1 >"$CPUS/cpu$cpu/online" || log "cpu$cpu did not come back"
		done
		log "CPUs back: $(cat "$CPUS/online")"
	fi
	[ -w "$PARAM/sodi_pdn" ] && echo 0 >"$PARAM/sodi_pdn"
	if [ -n "$UNBOUND" ]; then
		echo "$USB" >/sys/bus/platform/drivers/mtu3/bind && log "gadget bound again"
	fi
	if [ -n "$USB_CONTROL" ]; then
		echo "$USB_CONTROL" >"/sys/bus/platform/devices/$USB/power/control" &&
			log "gadget power/control back to $USB_CONTROL"
	fi
	if [ -n "$RADIOS_DOWN" ]; then
		"$RADIOS" post suspend && log "radios back"
	fi
	log "taint at the end: $(cat /proc/sys/kernel/tainted)"
}

stop() {
	log "STOP: $*"
	new_dmesg | grep -E 'sodi|spm|WARNING|Oops|BUG|rcu' | tail -n 20
	restore
	log "done, stopped"
	exit 1
}

hash() {
	"$MHZ" 0 hash | awk '{print $2}'
}

check_dmesg() {
	if new_dmesg | grep -qE 'WARNING|Oops|BUG:|rcu.*stall|detected stalls'; then
		stop "a kernel warning, Oops or stall since the start"
	fi
}

# One period: write, read the wake line, check it and the memory hash.
period() {
	ms=$1
	mode=$2
	n0=$(dmesg | wc -l)
	if ! echo "$ms" >"$SODI"; then
		dmesg | tail -n +"$((n0 + 1))"
		stop "sodi_once_ms $ms ($mode) failed"
	fi
	line=$(dmesg | tail -n +"$((n0 + 1))" | grep "sodi $mode: returned" | tail -n 1)
	log "$ms ms $mode: ${line#*: }"
	dmesg | tail -n +"$((n0 + 1))" | grep "sodi $mode: dummy1" | sed 's/^/    /'
	case $line in
	*"returned=1 "*) ;;
	*) stop "no return from the $ms ms period" ;;
	esac
	r12=$(echo "$line" | sed -n 's/.* r12=\([0-9a-f]*\).*/\1/p')
	tout=$(echo "$line" | sed -n 's/.* timer_out=\([0-9a-f]*\).*/\1/p')
	slept=$(( 0x${tout:-0} * 1000 / 32768 ))
	log "    r12 $r12, slept $slept ms"
	[ $(( 0x${r12:-0} & 1 )) -eq 1 ] || log "    note: not a timer wake"
	h=$(hash)
	if [ "$h" != "$REF" ]; then
		log "STOP: hash $h after the $ms ms $mode period, reference $REF; powering off"
		new_dmesg | tail -n 30
		sync
		systemctl poweroff
		exit 1
	fi
	log "    hash equal"
	check_dmesg
}

# ---- checks before anything changes ----
DMESG0=$(dmesg | wc -l)
log "D3 start, $(uname -r), boot $(cat /proc/sys/kernel/random/boot_id), taint $(cat /proc/sys/kernel/tainted)"
[ "$(id -u)" -eq 0 ] || stop "not root"
if [ -n "$KO" ]; then
	[ -f "$KO" ] || stop "no module at $KO"
	log "module $(sha256sum "$KO" | cut -c1-16)…, vermagic $(modinfo -F vermagic "$KO")"
	case $(modinfo -F vermagic "$KO") in
	"$(uname -r) "*) ;;
	*) stop "the module's vermagic does not match $(uname -r)" ;;
	esac
else
	log "the image's module: $(modinfo -F filename mt6797-spm-sleep 2>/dev/null)"
fi
[ "$(sha256sum "$FW" | cut -d' ' -f1)" = "$FW_SHA" ] || stop "$FW missing or its hash differs"
case $(sha256sum "$MHZ" | cut -c1-8) in
"$MHZ_SHA") ;;
*) stop "$MHZ missing or not $MHZ_SHA" ;;
esac
for ps in /sys/class/power_supply/*; do
	[ "$(cat "$ps/type")" = Battery ] && continue
	[ "$(cat "$ps/online" 2>/dev/null)" = 1 ] && stop "external power on $(basename "$ps"): pull the cable"
done
[ -d /sys/module/mt6797_gate_unused ] || modprobe mt6797-gate-unused || stop "mt6797-gate-unused did not load"
log "battery $(cat /sys/class/power_supply/*/capacity 2>/dev/null | head -n 1) %"

log "waiting 30 s for the SSH session to end"
sleep 30

# ---- setup ----
"$RADIOS" pre suspend || stop "the radios did not unload"
RADIOS_DOWN=1
log "radios unloaded"
if [ "${D3_UNBIND:-0}" = 1 ]; then
	# Image 131 only: images with 0801 must not unbind MTU3
	echo "$USB" >/sys/bus/platform/drivers/mtu3/unbind || stop "the gadget did not unbind"
	UNBOUND=1
	log "gadget unbound"
else
	ctl=/sys/bus/platform/devices/$USB/power/control
	USB_CONTROL=$(cat "$ctl")
	echo auto >"$ctl" || stop "power/control not set"
	log "gadget power/control auto (was $USB_CONTROL), $(cat "/sys/bus/platform/devices/$USB/power/runtime_status") now"
	sleep 10
	log "gadget runtime $(cat "/sys/bus/platform/devices/$USB/power/runtime_status")"
fi

if [ -d /sys/module/mt6797_spm_sleep ]; then
	rmmod mt6797_spm_sleep || stop "the running SPM module did not unload"
fi
if [ -n "$KO" ]; then
	insmod "$KO" || stop "insmod failed"
else
	modprobe mt6797-spm-sleep || stop "modprobe failed"
fi
new_dmesg | grep -E 'mt6797-spm-sleep|pcm_' | sed 's/^/    /'
[ -e "$SODI" ] || stop "no $SODI: the SODI program was not loaded"

log "waiting up to 300 s for the idle blank; do not touch any input"
t=0
until [ "$(cat /sys/class/backlight/*/bl_power 2>/dev/null | head -n 1)" = 4 ]; do
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

# ---- the periods ----
REF=$(hash)
log "1. hash reference $REF"
log "2. CG mode"
period 100 cg
log "3."
period 1000 cg
log "4. ten periods"
for i in 1 2 3 4 5 6 7 8 9 10; do
	log "    period $i of 10"
	period 1000 cg
done
log "5. PDN mode"
echo 1 >"$PARAM/sodi_pdn" || stop "sodi_pdn not set"
period 100 pdn
period 1000 pdn
echo 0 >"$PARAM/sodi_pdn"

# ---- restore ----
log "6. restore"
restore
check_dmesg
log "done, PASS"
