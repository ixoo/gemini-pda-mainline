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
# D4_NO_EVENT=1 sets sodi_no_event, so periods arm no resource event (0825,
# stage D5n).
# D4_PCM_WDT=1 sets sodi_pcm_wdt: the PCM watchdog, in wake mode, ends a
# stuck period 2 s after its timer (0826, stage D5p).
# D4_IM_WAIT=1 sets sodi_im_wait (refuse a period whose IM fetch has not
# settled) and D4_IM_REUSE=1 sets sodi_im_reuse (IM slave mode for a resident
# program); both 0827, stage D5q.
# D4_R7_VENDOR=1 sets sodi_r7_vendor: r7 starts from the vendor's
# POWER_ON_VAL1, 0x00015820 (0830, stage D5r).
# D4_VEC_CLEAR=1 sets sodi_vec_clear: PCM_EVENT_VECTOR_EN is written 0 before
# each kick (0831).
# D4_OBS=1 sets sodi_obs (0833, stage D5s) and needs D4_NO_EVENT=1, so DRAM
# never enters self-refresh while CPU8 runs. CPU8 stays online as the
# observer; every task, IRQ and unbound workqueue is moved to CPU0, so CPU8
# wakes nothing on CPU0 during a period, and moved back at the end. CPU8's
# cpufreq policy, if any, is pinned at its lowest frequency for the run, so
# no A72 rail changes during it. After a
# stuck period the module prints its samples and stops (0834); the TOPRGU
# watchdog then resets the system, since its pinging thread, watchdogd, must
# be confined to CPU0 too (the script stops otherwise).
# D4_OBS_NOREAD=1 (with D4_OBS=1) sets sodi_obs_noread: the observer only
# counts its ticks in a period and reads the SPM only once one is stuck
# (0835, stage D5u).
# D4_MARK=1 sets sodi_mark: SW_DEBUG and SW_RSV_0 start each kick at
# 0x5a5a0000 plus the kick count, read after a reset (0836, stage D5u).
# D4_MM=1 logs the MMSYS gates in the vendor's SODI check after the blank;
# D4_MM=2 also closes those four gates (0837, stage D5y).
# D4_NO_MP2=1 sets sodi_no_mp2: MP2_AXI_CONFIG is left alone (0838, D5z).
# D4_MASK_PPI=1 sets sodi_mask_ppi: CPU0's SGIs and PPIs are disabled for each
# period, the backstop timer's included (0839, D5aa).
# D4_ACINACTM_LATE=1 sets sodi_acinactm_late: ACINACTM is set just before WFI
# and cleared right after, as the vendor's driver does (0840, D5ab).
# D4_CRUMBS=1 sets sodi_crumbs: a kernel line at each stage of a period, kept
# by the RAM console through a reset (0841, D5ac). It needs D4_MASK_PPI=1.
# D4_VARIANT=N sets sodi_variant: the program is loaded with test patches in
# RAM (1: no clock cut, 2: no master pause; 0842, D5ad).
# D4_KEEP_26M=1 sets sodi_keep_26m: SW_FLAG bit 15 as in the vendor's SODI
# flags, so 26 MHz and infra stay forced awake in the period (0843, D5ae).
# D4_SMI_ASYNC=1 sets sodi_smi_async: SMI_COMMON_ASYNC_DCM is set in the M4U
# for each period and restored after it (0838, stage D5z).
# D4_PIN_KHZ=N pins CPU0's cpufreq policy at N kHz (min = max) for the
# windows and restores it after (stage D5l).
# D4_TIMER_CAP=1 sets sodi_timer_cap, so each period ends before CPU0's next
# local timer event (0821, stage D5f).
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
POLICY=/sys/devices/system/cpu/cpufreq/policy0
PIN_MIN=""
PIN_MAX=""
USB_CONTROL=""
OBS_MASK=""
OBS_POL=""
OBS_POL_MIN=""
OBS_POL_MAX=""

exec >>"$LOG" 2>&1

log() {
	echo "$(date +%T) $*"
	sync
}

# The ttyS0 transmit count; without /proc/tty/driver/serial (D5z), the UART's
# interrupt count from /proc/interrupts.
uart_tx() {
	t=$(grep '^0:' /proc/tty/driver/serial 2>/dev/null | grep -o 'tx:[0-9]*')
	[ -n "$t" ] || t=$(grep -m1 -E '11002000|serial|uart' /proc/interrupts |
		awk '{ n = 0; for (k = 2; k <= NF && $k ~ /^[0-9]+$/; k++) n += $k; print "irqs:" n }')
	echo "${t:-tx:-}"
}

smi_val() {
	printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_smi_async_val)"
}

new_dmesg() {
	dmesg | tail -n +"$((DMESG0 + 1))"
}

restore() {
	if [ -n "$PIN_MIN" ]; then
		echo "$PIN_MIN" >"$POLICY/scaling_min_freq"
		echo "$PIN_MAX" >"$POLICY/scaling_max_freq"
		log "cpufreq policy0 back to $(cat "$POLICY/scaling_min_freq")-$(cat "$POLICY/scaling_max_freq") kHz"
	fi
	if [ -n "$TAKEN" ]; then
		for cpu in $TAKEN; do
			echo 1 >"$CPUS/cpu$cpu/online" || log "cpu$cpu did not come back"
		done
		log "CPUs back: $(cat "$CPUS/online")"
	fi
	if [ -n "$OBS_POL" ]; then
		echo "$OBS_POL_MAX" >"$OBS_POL/scaling_max_freq"
		echo "$OBS_POL_MIN" >"$OBS_POL/scaling_min_freq"
		log "CPU8 policy back to $(cat "$OBS_POL/scaling_min_freq")-$(cat "$OBS_POL/scaling_max_freq") kHz"
	fi
	if [ -n "$OBS_MASK" ]; then
		obs_affinity "$OBS_MASK"
		log "tasks, IRQs and workqueues back to mask $OBS_MASK"
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

# Every task, IRQ and unbound workqueue to the CPUs in mask $1
obs_affinity() {
	echo "$1" >/proc/irq/default_smp_affinity
	for f in /proc/irq/*/smp_affinity; do
		echo "$1" >"$f" 2>/dev/null
	done
	echo "$1" >/sys/devices/virtual/workqueue/cpumask
	for p in /proc/[0-9]*; do
		taskset -a -p "$1" "${p#/proc/}" >/dev/null 2>&1
	done
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
# 1 s (past the synced refusal line), ten at most in a row. Sets R12 and
# SLEPT for the caller.
period() {
	tries=0
	# Synced once before the period's attempts: a reset after this line and
	# before the period's result came inside the period, not between periods
	# (D5h). The second lets the card's MSDC clock gate off again after the
	# sync; synced right before the attempt, every attempt was refused.
	log "    start, cpu0 $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo -) kHz"
	sleep 1
	while :; do
		n0=$(dmesg | wc -l)
		echo 2000 >"$SODI" && break
		if dmesg | tail -n +"$((n0 + 1))" | grep -q 'refused'; then
			tries=$((tries + 1))
			REFUSED=$((REFUSED + 1))
			log "    $(dmesg | tail -n +"$((n0 + 1))" | grep -o 'sodi: .*refused' | tail -n 1)"
			[ "$tries" -ge 10 ] && stop "ten refusals in a row"
			sleep 1
			continue
		fi
		dmesg | tail -n +"$((n0 + 1))"
		dmesg | tail -n +"$((n0 + 1))" | grep -q 'stuck=1' &&
			stop "the IM fetch was not ready; period refused before the kick (D5q)"
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
	im=$(echo "$out" | grep -o 'im fsm.*' | tail -n 1)
	[ -n "$im" ] && log "    $im"
	io=$(echo "$out" | grep -o 'io val0.*' | tail -n 1)
	[ -n "$io" ] && log "    $io"
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
		10:scp 13:pcm_wdt 14:usb_cdsc 15:usb_pdn 16:c2k_wdt 17:sec_eint 18:ccif1 \
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
# A module whose cpuidle driver is registered (0816 on) holds itself and
# cannot be unloaded: it needs a fresh boot before the next run.
if [ -d /sys/module/mt6797_spm_sleep ] &&
	[ "$(cat /sys/module/mt6797_spm_sleep/refcnt)" != 0 ]; then
	stop "the running SPM module is in use (its cpuidle driver); boot fresh first"
fi
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
[ "${D4_TIMER_CAP:-0}" = 1 ] && level="$level sodi_timer_cap=1"
[ "${D4_NO_EVENT:-0}" = 1 ] && level="$level sodi_no_event=1"
if [ "${D4_PCM_WDT:-0}" = 1 ]; then
	grep -q 'sodi_pcm_wdt' "$KO" || stop "the module has no sodi_pcm_wdt parameter (0826)"
	level="$level sodi_pcm_wdt=1"
fi
[ "${D4_IM_WAIT:-0}" = 1 ] && level="$level sodi_im_wait=1"
[ "${D4_IM_REUSE:-0}" = 1 ] && level="$level sodi_im_reuse=1"
if [ "${D4_R7_VENDOR:-0}" = 1 ]; then
	grep -q 'sodi_r7_vendor' "$KO" || stop "the module has no sodi_r7_vendor parameter (0830)"
	level="$level sodi_r7_vendor=1"
fi
if [ "${D4_VEC_CLEAR:-0}" = 1 ]; then
	grep -q 'sodi_vec_clear' "$KO" || stop "the module has no sodi_vec_clear parameter (0831)"
	level="$level sodi_vec_clear=1"
fi
if [ "${D4_OBS:-0}" = 1 ]; then
	grep -q 'sodi_obs' "$KO" || stop "the module has no sodi_obs parameter (0833)"
	[ "${D4_NO_EVENT:-0}" = 1 ] || stop "D4_OBS=1 needs D4_NO_EVENT=1"
	command -v taskset >/dev/null || stop "no taskset"
	[ "$(cat "$CPUS/cpu8/online" 2>/dev/null)" = 1 ] || stop "CPU8 is offline"
	level="$level sodi_obs=1"
	if [ "${D4_OBS_NOREAD:-0}" = 1 ]; then
		grep -q 'sodi_obs_noread' "$KO" || stop "the module has no sodi_obs_noread parameter (0835)"
		level="$level sodi_obs_noread=1"
	fi
fi
if [ "${D4_MARK:-0}" = 1 ]; then
	grep -q 'sodi_mark' "$KO" || stop "the module has no sodi_mark parameter (0836)"
	level="$level sodi_mark=1"
fi
if [ "${D4_NO_MP2:-0}" = 1 ]; then
	grep -q 'sodi_no_mp2' "$KO" || stop "the module has no sodi_no_mp2 parameter (0838)"
	level="$level sodi_no_mp2=1"
fi
if [ "${D4_MASK_PPI:-0}" = 1 ]; then
	grep -q 'sodi_mask_ppi' "$KO" || stop "the module has no sodi_mask_ppi parameter (0839)"
	level="$level sodi_mask_ppi=1"
fi
if [ "${D4_ACINACTM_LATE:-0}" = 1 ]; then
	grep -q 'sodi_acinactm_late' "$KO" || stop "the module has no sodi_acinactm_late parameter (0840)"
	level="$level sodi_acinactm_late=1"
fi
if [ "${D4_CRUMBS:-0}" = 1 ]; then
	grep -q 'sodi_crumbs' "$KO" || stop "the module has no sodi_crumbs parameter (0841)"
	# A print can leave a self-IPI pending; masked, it cannot end WFI (0839)
	[ "${D4_MASK_PPI:-0}" = 1 ] || stop "D4_CRUMBS needs D4_MASK_PPI=1"
	level="$level sodi_crumbs=1"
fi
if [ "${D4_KEEP_26M:-0}" = 1 ]; then
	grep -q 'sodi_keep_26m' "$KO" || stop "the module has no sodi_keep_26m parameter (0843)"
	level="$level sodi_keep_26m=1"
fi
case ${D4_VARIANT:-0} in
0) ;;
1 | 2)
	grep -q 'sodi_variant' "$KO" || stop "the module has no sodi_variant parameter (0842)"
	level="$level sodi_variant=$D4_VARIANT"
	;;
*) stop "D4_VARIANT must be 1 or 2" ;;
esac
if [ "${D4_SMI_ASYNC:-0}" = 1 ]; then
	grep -q 'sodi_smi_async' "$KO" || stop "the module has no sodi_smi_async parameter (0838)"
	level="$level sodi_smi_async=1"
fi
case ${D4_MM:-0} in
0) ;;
1 | 2) grep -q 'sodi_mm_cg' "$KO" || stop "the module has no sodi_mm_cg parameter (0837)" ;;
*) stop "D4_MM must be 1 or 2" ;;
esac
case $level in
*sodi_im_*) grep -q 'sodi_im_reuse' "$KO" || stop "the module has no sodi_im_* parameters (0827)" ;;
esac
# shellcheck disable=SC2086 # empty parameters must vanish
insmod "$KO" ${D4_WAKE:+sodi_wake_src=$D4_WAKE} $level || stop "insmod failed"
# Each parameter set at insmod, as the module reads it back
for p in $level; do
	p=${p%%=*}
	log "$p $(cat "/sys/module/mt6797_spm_sleep/parameters/$p" 2>/dev/null || echo unreadable)"
done
log "sodi_wake_src $(printf '%08x' "$(cat /sys/module/mt6797_spm_sleep/parameters/sodi_wake_src)")"
new_dmesg | grep -E 'mt6797-spm-sleep|pcm_' | sed 's/^/    /'
[ -e "$SODI" ] || stop "no $SODI: the SODI program was not loaded"
if [ "${D4_OBS:-0}" = 1 ]; then
	new_dmesg | grep -q 'sodi obs: sampling on CPU8' || stop "the observer did not start"
fi

log "waiting up to 300 s for the idle blank; do not touch any input"
t=0
until [ "$(cat /sys/class/backlight/*/bl_power 2>/dev/null | head -n 1)" = 4 ]; do
	t=$((t + 1))
	[ "$t" -gt 300 ] && stop "no blank within 300 s"
	sleep 1
done
log "blanked"
if [ "${D4_MM:-0}" != 0 ]; then
	if echo "$D4_MM" >/sys/module/mt6797_spm_sleep/parameters/sodi_mm_cg; then
		new_dmesg | grep -o 'sodi mm: .*' | sed 's/^/    /'
	else
		new_dmesg | grep -o 'sodi mm: .*' | sed 's/^/    /'
		[ "$D4_MM" = 2 ] && stop "the MMSYS gates were not closed"
		log "the MMSYS gates were not read"
	fi
fi

for cpu in 9 8 7 6 5 4 3 2 1; do
	[ "$cpu" = 8 ] && [ "${D4_OBS:-0}" = 1 ] && continue
	[ "$(cat "$CPUS/cpu$cpu/online" 2>/dev/null)" = 1 ] || continue
	echo 0 >"$CPUS/cpu$cpu/online" || stop "cpu$cpu did not go offline"
	TAKEN="$cpu $TAKEN"
done
if [ "${D4_OBS:-0}" = 1 ]; then
	OBS_MASK=$(cat /proc/irq/default_smp_affinity)
	obs_affinity 1
	if [ -d "$CPUS/cpu8/cpufreq" ]; then
		pol=$CPUS/cpu8/cpufreq
		OBS_POL_MIN=$(cat "$pol/scaling_min_freq")
		OBS_POL_MAX=$(cat "$pol/scaling_max_freq")
		OBS_POL=$pol
		lo=$(cat "$pol/cpuinfo_min_freq")
		echo "$lo" >"$pol/scaling_min_freq"
		echo "$lo" >"$pol/scaling_max_freq"
		[ "$(cat "$pol/scaling_cur_freq")" = "$lo" ] || stop "CPU8's policy did not pin at $lo kHz"
		log "CPU8 policy pinned at $lo kHz (was $OBS_POL_MIN-$OBS_POL_MAX)"
	else
		log "CPU8 has no cpufreq policy"
	fi
	wd=$(pgrep -x watchdogd | head -n 1)
	[ -n "$wd" ] || stop "no watchdogd thread: nothing would reset a stuck period"
	wdc=$(awk '/^Cpus_allowed_list:/ {print $2}' "/proc/$wd/status")
	[ "$wdc" = 0 ] || stop "watchdogd may run on CPUs $wdc, so CPU8 could keep a stuck system alive"
	log "observer: watchdogd confined to CPU0"
	log "observer: tasks on CPU8 after the move (its per-CPU threads stay): $(ps -eo psr= | awk '$1 == 8' | wc -l)"
fi
log "online: $(cat "$CPUS/online")"
sleep 5
if [ -n "${D4_PIN_KHZ:-}" ]; then
	grep -qw "$D4_PIN_KHZ" "$POLICY/scaling_available_frequencies" ||
		stop "$D4_PIN_KHZ kHz is not an OPP of policy0"
	PIN_MIN=$(cat "$POLICY/scaling_min_freq")
	PIN_MAX=$(cat "$POLICY/scaling_max_freq")
	echo "$D4_PIN_KHZ" >"$POLICY/scaling_max_freq"
	echo "$D4_PIN_KHZ" >"$POLICY/scaling_min_freq"
	sleep 1
	[ "$(cat "$POLICY/scaling_cur_freq")" = "$D4_PIN_KHZ" ] ||
		stop "policy0 did not pin at $D4_PIN_KHZ kHz"
	log "cpufreq policy0 pinned at $D4_PIN_KHZ kHz (was $PIN_MIN-$PIN_MAX)"
fi
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
log "C: pings arriving, 60 periods; ttyS0 $(uart_tx)"
early_c=0
pkt_c=0
for i in $(seq 1 60); do
	blank || { log "C: the screen lit, window ends"; break; }
	period
	early && early_c=$((early_c + 1))
	[ $(( (0x$R12 >> 5) & 1 | (0x${STA6:-0} >> 19) & 1 )) -eq 1 ] && pkt_c=$((pkt_c + 1))
	if [ "${D4_SMI_ASYNC:-0}" = 1 ]; then
		log "C: after period $i: ttyS0 $(uart_tx), smi async saved $(smi_val)"
	else
		log "C: after period $i: ttyS0 $(uart_tx)"
	fi
done
log "C: ttyS0 $(uart_tx)"
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
