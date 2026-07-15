#!/usr/bin/env bash

# Bounded, read-only MT6797 thermal/AUXADC inventory. This script never
# writes procfs/sysfs, changes a thermal policy, enables a clock, or touches a
# physical register through /dev/mem.

set -u
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }

read_text() {
	[ -r "$1" ] || return 0
	tr '\000' ' ' < "$1"
}

dump_property() {
	local file=$1
	local label=$2
	[ -r "$file" ] || return 0
	printf '  %s=' "$label"
	case "$label" in
		name|compatible|clock-names|status|type|mode|policy)
			read_text "$file"
			printf '\n'
			;;
		*)
			od -An -tx1 -v "$file" | tr -d ' \n'
			printf '\n'
			;;
	esac
}

section identity
uname -a 2>/dev/null || true

section thermal-zones
for zone in /sys/class/thermal/thermal_zone[0-9]*; do
	[ -d "$zone" ] || continue
	printf 'zone=%s' "${zone##*/}"
	for name in type mode policy temp trip_point_0_temp trip_point_0_type \
		trip_point_1_temp trip_point_1_type; do
		file=$zone/$name
		[ -r "$file" ] && printf ' %s=%s' "$name" "$(tr '\n' ' ' < "$file")"
	done
	printf '\n'
done

section cpu-thermal-proc
for name in mtktscpu mtkts1 mtkts2 mtkts4; do
	file=/proc/mtktz/$name
	[ -r "$file" ] || continue
	printf '%s:\n' "$name"
	# These are bounded proc entries; do not traverse or dump the whole procfs.
	head -n 120 "$file" 2>/dev/null || true
done

section thermal-driver-proc
for name in tzcpu tzcpu_read_temperature tzcpu_fastpoll \
	tzcpu_Tj_out_via_HW_pin tzcpu_talking_flag; do
	file=/proc/driver/thermal/$name
	[ -r "$file" ] || continue
	printf '%s:\n' "$name"
	head -n 120 "$file" 2>/dev/null || true
done

section thermal-device-tree
for node in \
	/sys/firmware/devicetree/base/soc/therm_ctrl@1100b000 \
	/sys/firmware/devicetree/base/soc/adc_hw@11001000 \
	/sys/firmware/devicetree/base/soc/efusec@10206000; do
	[ -d "$node" ] || continue
	printf 'node=%s\n' "${node##*/}"
	for name in name compatible reg interrupts interrupt-names clocks clock-names \
		status; do
		dump_property "$node/$name" "$name"
	done
done

section thermal-clocks
for clock in infra_therm infra_auxadc; do
	base=/sys/kernel/debug/clk/$clock
	[ -d "$base" ] || continue
	printf 'clock=%s' "$clock"
	for name in clk_rate clk_enable_count clk_prepare_count clk_accuracy; do
		file=$base/$name
		[ -r "$file" ] && printf ' %s=%s' "$name" "$(tr '\n' ' ' < "$file")"
	done
	printf '\n'
done

section thermal-interrupts
grep -Ei '(^|[[:space:]])(mtk-thermal|mtk_cpuxgpt|mt-gpt)([[:space:]]|$)' \
	/proc/interrupts 2>/dev/null || true

section thermal-symbols
# Keep symbol names only; addresses are intentionally omitted.
if [ -r /proc/kallsyms ]; then
	awk '($3 ~ /(^|_)(thermal|mtkts|tscpu|auxadc|AUXADC|THERM)/) { print $3 }' \
		/proc/kallsyms | sort -u | head -n 240
else
	echo 'kallsyms=unreadable'
fi

section privilege-gate
if sudo -n true 2>/dev/null; then
	echo 'sudo_nopass=true'
else
	echo 'sudo_nopass=false'
fi
