#!/usr/bin/env bash

# Bounded, read-only CPU topology, PSCI, and architectural-timer inventory.
# Do not add writes, dmesg, a complete command line, or CPU hotplug actions.

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
		name|compatible|device_type|enable-method|entry-method|method|status)
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

section cpu-masks
for name in possible present online offline; do
	file=/sys/devices/system/cpu/$name
	[ -r "$file" ] && printf '%s=%s\n' "$name" "$(tr '\n' ' ' < "$file")"
done

section cpuinfo-summary
grep -E '^(processor|CPU implementer|CPU part|Hardware)' /proc/cpuinfo 2>/dev/null || true

section cpu-topology
for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
	[ -d "$cpu" ] || continue
	printf 'cpu=%s' "${cpu##*/}"
	if [ -r "$cpu/online" ]; then
		printf ' online=%s' "$(tr '\n' ' ' < "$cpu/online")"
	else
		printf ' online=1'
	fi
	for name in physical_package_id core_id cluster_id; do
		file=$cpu/topology/$name
		[ -r "$file" ] && printf ' %s=%s' "$name" "$(tr '\n' ' ' < "$file")"
	done
	if [ -L "$cpu/clockevent" ]; then
		printf ' clockevent=%s' "$(readlink -f "$cpu/clockevent")"
	fi
	printf '\n'
done

section clocksource
for name in current_clocksource available_clocksource; do
	file=/sys/devices/system/clocksource/clocksource0/$name
	[ -r "$file" ] && printf '%s=%s\n' "$name" "$(tr '\n' ' ' < "$file")"
done

section clockevents
for event in /sys/devices/system/clockevents/clockevent[0-9]*; do
	[ -d "$event" ] || continue
	printf 'event=%s' "${event##*/}"
	for name in current_device name rating state; do
		file=$event/$name
		[ -r "$file" ] && printf ' %s=%s' "$name" "$(tr '\n' ' ' < "$file")"
	done
	printf '\n'
done

section cpu-idle-sysfs
for state in /sys/devices/system/cpu/cpu0/cpuidle/state[0-9]*; do
	[ -d "$state" ] || continue
	printf 'state=%s' "${state##*/}"
	for name in name desc latency residency usage time disable; do
		file=$state/$name
		[ -r "$file" ] && printf ' %s=%s' "$name" "$(tr '\n' ' ' < "$file")"
	done
	printf '\n'
done

section psci-device-tree
psci=/sys/firmware/devicetree/base/psci
for name in compatible method cpu_on cpu_off cpu_suspend affinity_info; do
	dump_property "$psci/$name" "$name"
done

section timer-device-tree
timer=/sys/firmware/devicetree/base/soc/timer
for name in compatible clock-frequency interrupts interrupt-names status; do
	dump_property "$timer/$name" "$name"
done

section cpu-device-tree
for cpu in /sys/firmware/devicetree/base/cpus/cpu@*; do
	[ -d "$cpu" ] || continue
	printf 'node=%s\n' "${cpu##*/}"
	for name in name compatible device_type reg clock-frequency enable-method \
		cpu-release-addr cpu-idle-states status; do
		dump_property "$cpu/$name" "$name"
	done
done

section idle-state-device-tree
for state in /sys/firmware/devicetree/base/cpus/idle-states/*; do
	[ -d "$state" ] || continue
	printf 'node=%s\n' "${state##*/}"
	for name in name compatible status entry-method arm,psci-suspend-param \
		entry-latency-us exit-latency-us min-residency-us; do
		dump_property "$state/$name" "$name"
	done
done

section power-policy
for name in state mem_sleep; do
	file=/sys/power/$name
	[ -r "$file" ] && printf '%s=%s\n' "$name" "$(tr '\n' ' ' < "$file")"
done

section timer-interrupts
grep -Ei 'arch_timer|arch_sys_timer|cpuxgpt|(^| )mt-gpt($| )' /proc/interrupts 2>/dev/null || true

section privilege-gate
if sudo -n true 2>/dev/null; then
	echo 'sudo_nopass=true'
else
	echo 'sudo_nopass=false'
fi
