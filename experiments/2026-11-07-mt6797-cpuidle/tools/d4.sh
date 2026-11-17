#!/bin/sh
# SPDX-License-Identifier: MIT
#
# Stage D4 of experiments/2026-11-07-mt6797-cpuidle ("Request D4"): SODI
# periods ended by device interrupts, with Wi-Fi joined, the vendor's SODI
# wake sources and SYS_CIRQ (0804). Run as root, detached, cable out:
#
#   setsid nohup sh d4.sh /path/to/mt6797-spm-sleep.ko </dev/null >/dev/null 2>&1 &
#
# D4_WAKE=0x... sets the module's sodi_wake_src (within the vendor set; the
# default leaves APXGPT out, 0805). D4_CIRQ_LEVEL=1 sets sodi_cirq_level, so
# level SPIs (the WLAN interrupt among them) are recorded in SYS_CIRQ (0806).
# D4_IDLE=0 loads the module with sodi_idle=0, so its cpuidle driver is not
# registered (0819, stage D5d). D4_STATES=1 loads it with sodi_idle_states=1,
# the WFI state alone (0820, stage D5e).
# No period starts while the screen is lit: SODI with the display scanning
# out is not part of D4.
#
# Wi-Fi stays up. The script waits for the desktop's idle blank, takes
# CPU1-9 offline and runs three windows of 2000 ms periods:
#   C  inbound ping: it waits up to 300 s for ICMP echo requests (the
#      custodian pings the device from the laptop, once a second, for about
#      three minutes), then runs 60 periods back to back while they arrive;
#   A  quiet: once the pings have stopped, 20 periods;
#   B  key: up to 300 s of periods; the owner presses one key once when the
#      custodian says so; the window ends at the first period a key ends.
# Each period is logged with its wake reason and the SYS_CIRQ status. The
# log is /var/tmp/d4.log, synced after every line.
#
# Hypothesis: with the full wake set and SYS_CIRQ, an inbound packet and a
# key press each end a SODI period early, and memory stays intact.
# Unique observation: the first device wakes from SODI on mainline, which
# wake source each one uses, and the natural wake rate with Wi-Fi joined.
# Stops: a failed write that is not a refusal; ten refusals in a row;
# five periods in a row ended at once by the same source other than the timer;
# returned=0; a new WARNING, Oops, BUG or RCU stall; a wrong hash, after
# which the script syncs and powers off, since memory may be corrupt.
set -u

KO=${1:-}
LOG=/var/tmp/d4.log
MHZ=/tmp/cpu-mhz
MHZ_SHA=22a0acfc
FW=/lib/firmware/mediatek/mt6797/pcm_sodi.bin
FW_SHA=dda8cca1e110d57137afb8ef4957da758c19d38db45ea2bb30bc7133cc122ae4
FW_SUSPEND=/lib/firmware/mediatek/mt6797/pcm_suspend.bin
FW_SUSPEND_SHA=d6e8a0b8851e78e95891c995605ffbf210eade56583b14cf6b4a67e7d770f4e0
SODI=/sys/kernel/debug/sodi_once_ms
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

in_echos() {
	awk '/^Icmp:/ { if (!n++) { for (i = 2; i <= NF; i++) if ($i == "InEchos") c = i } else print $c }' /proc/net/snmp
}

# One 2000 ms period. A refusal (a gate briefly running) is retried after
# 0.5 s, ten at most in a row. Sets R12 and SLEPT for the caller.
period() {
	tries=0
	while :; do
		n0=$(dmesg | wc -l)
		echo 2000 >"$SODI" && break
		if dmesg | tail -n +"$((n0 + 1))" | grep -q 'refused'; then
			tries=$((tries + 1))
			REFUSED=$((REFUSED + 1))
			log "    $(dmesg | tail -n +"$((n0 + 1))" | grep -o 'sodi: .*refused' | tail -n 1)"
			[ "$tries" -ge 10 ] && stop "ten refusals in a row"
			sleep 0.5
			continue
		fi
		dmesg | tail -n +"$((n0 + 1))"
		stop "sodi_once_ms failed without a refusal"
	done
	out=$(dmesg | tail -n +"$((n0 + 1))")
	line=$(echo "$out" | grep "sodi cg: returned" | tail -n 1)
	case $line in
	*"returned=1 "*) ;;
	*) log "$line"; stop "no return from a period" ;;
	esac
	R12=$(echo "$line" | sed -n 's/.* r12=\([0-9a-f]*\).*/\1/p')
	tout=$(echo "$line" | sed -n 's/.* timer_out=\([0-9a-f]*\).*/\1/p')
	SLEPT=$(( 0x${tout:-0} * 1000 / 32768 ))
	sta=$(echo "$out" | grep "sodi cirq:" | tail -n 1 | sed -n 's/.*cirq: \([0-9]*\) lines.* sta=\(.*\)/\1 lines, sta \2/p')
	# CIRQ status words 3 and 6: SPI 170 (EINT parent) is word 3 bit 2,
	# SPI 283 (WLAN HIF) word 6 bit 19
	STA3=$(echo "$sta" | awk '{print $7}')
	STA6=$(echo "$sta" | awk '{print $10}')
	log "    r12 $R12, slept $SLEPT ms; $(wake_names "$R12"); cirq $sta"
	if [ "$SLEPT" -eq 0 ] && [ "$R12" = "$LAST_R12" ]; then
		INSTANT=$((INSTANT + 1))
	else
		INSTANT=0
	fi
	LAST_R12=$R12
	[ "$INSTANT" -ge 4 ] && stop "five periods in a row ended at once by r12 $R12: a source no one triggered"
}

# The wake sources named in r12 (SPM_WAKEUP_EVENT_MASK bit names).
wake_names() {
	v=$((0x${1:-0}))
	names=""
	for pair in 0:timer 2:keypad 4:apxgpt 5:conn2ap 6:eint 7:conn_wdt 8:ccif0 \
		10:scp 14:usb_cdsc 15:usb_pdn 16:c2k_wdt 17:sec_eint 18:ccif1 \
		20:afe 22:cirq 24:csyspwreq 25:md_wdt 26:cldma 27:sej; do
		bit=${pair%%:*}
		[ $(( (v >> bit) & 1 )) -eq 1 ] && names="$names ${pair#*:}"
	done
	echo "wake:${names:- none}"
}

early() {
	[ "$SLEPT" -lt 1900 ]
}

blank() {
	[ "$(cat /sys/class/backlight/*/bl_power 2>/dev/null | head -n 1)" = 4 ]
}

# ---- checks before anything changes ----
DMESG0=$(dmesg | wc -l)
REFUSED=0
INSTANT=0
LAST_R12=""
log "D4 start, $(uname -r), boot $(cat /proc/sys/kernel/random/boot_id), taint $(cat /proc/sys/kernel/tainted)"
[ "$(id -u)" -eq 0 ] || stop "not root"
[ -f "$KO" ] || stop "no module at '$KO'"
log "module $(sha256sum "$KO" | cut -c1-16)…, vermagic $(modinfo -F vermagic "$KO")"
case $(modinfo -F vermagic "$KO") in
"$(uname -r) "*) ;;
*) stop "the module's vermagic does not match $(uname -r)" ;;
esac
grep -q 'sodi cirq' "$KO" || stop "the module has no SYS_CIRQ (0804)"
grep -q 'sodi_wake_src' "$KO" || stop "the module has no sodi_wake_src (0805)"
if [ "${D4_CIRQ_LEVEL:-0}" = 1 ]; then
	grep -q 'sodi_cirq_level' "$KO" || stop "the module has no sodi_cirq_level (0806)"
fi
[ "$(sha256sum "$FW" | cut -d' ' -f1)" = "$FW_SHA" ] || stop "$FW missing or its hash differs"
[ "$(sha256sum "$FW_SUSPEND" | cut -d' ' -f1)" = "$FW_SUSPEND_SHA" ] ||
	stop "$FW_SUSPEND missing or its hash differs"
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
ctl=/sys/bus/platform/devices/$USB/power/control
USB_CONTROL=$(cat "$ctl")
echo auto >"$ctl" || stop "power/control not set"
sleep 10
log "gadget power/control auto (was $USB_CONTROL), runtime $(cat "/sys/bus/platform/devices/$USB/power/runtime_status")"

if [ -d /sys/module/mt6797_spm_sleep ]; then
	rmmod mt6797_spm_sleep || stop "the running SPM module did not unload"
fi
level=""
[ "${D4_CIRQ_LEVEL:-0}" = 1 ] && level=sodi_cirq_level=1
[ "${D4_IDLE:-1}" = 0 ] && level="$level sodi_idle=0"
[ "${D4_STATES:-2}" = 1 ] && level="$level sodi_idle_states=1"
# shellcheck disable=SC2086 # empty parameters must vanish
insmod "$KO" ${D4_WAKE:+sodi_wake_src=$D4_WAKE} $level || stop "insmod failed"
[ -n "$level" ] && log "sodi_cirq_level $(cat /sys/module/mt6797_spm_sleep/parameters/sodi_cirq_level)"
log "sodi_wake_src $(printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_wake_src)")"
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
REF=$(hash)
log "hash reference $REF"
grep -iE 'eint|aw9523|keyboard' /proc/interrupts | sed 's/^/    before: /'

# ---- C: inbound ping ----
log "C: waiting up to 300 s for inbound pings (ping the device now)"
e0=$(in_echos)
t=0
until [ "$(in_echos)" -gt "$e0" ]; do
	t=$((t + 1))
	[ "$t" -gt 300 ] && stop "no inbound ping within 300 s"
	sleep 1
done
e0=$(in_echos)
log "C: pings arriving, 60 periods"
early_c=0
pkt_c=0
for i in $(seq 1 60); do
	blank || { log "C: the screen lit, window ends"; break; }
	period
	early && early_c=$((early_c + 1))
	[ $(( (0x$R12 >> 5) & 1 | (0x${STA6:-0} >> 19) & 1 )) -eq 1 ] && pkt_c=$((pkt_c + 1))
done
log "C: $early_c of 60 ended early, $pkt_c by conn2ap or the WLAN line; echo requests in the window $(( $(in_echos) - e0 ))"
check_hash "window C"
check_dmesg

# ---- A: quiet ----
log "A: waiting for the pings to stop"
t=0
e1=$(in_echos)
while sleep 5; do
	e2=$(in_echos)
	[ "$e2" -eq "$e1" ] && break
	e1=$e2
	t=$((t + 5))
	[ "$t" -gt 300 ] && stop "pings still arriving after 300 s"
done
log "A: 20 periods"
early_a=0
for i in $(seq 1 20); do
	blank || { log "A: the screen lit, window ends"; break; }
	period
	early && early_a=$((early_a + 1))
	check_hash "period $i of A"
done
log "A: $early_a of 20 ended early"
check_dmesg

# ---- B: a key ----
log "B: press one key once (up to 300 s)"
key=0
start=$(date +%s)
while [ $(( $(date +%s) - start )) -lt 300 ]; do
	if ! blank; then
		log "B: the screen lit with no key wake seen"
		break
	fi
	period
	check_hash "a period of B"
	if early && [ $(( (0x$R12 >> 6) & 1 | (0x$R12 >> 2) & 1 | (0x${STA3:-0} >> 2) & 1 )) -eq 1 ]; then
		key=1
		log "B: a key ended the period"
		break
	fi
done
sleep 2
grep -iE 'eint|aw9523|keyboard' /proc/interrupts | sed 's/^/    after: /'
[ "$key" = 1 ] || log "B: no key wake within the window"
check_dmesg

# ---- restore ----
log "refusals in all: $REFUSED"
restore
check_dmesg
log "done (C $early_c early, $pkt_c by packet; A $early_a early; B key $key)"
