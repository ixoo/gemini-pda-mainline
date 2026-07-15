#!/usr/bin/env bash

# Read-only Gemini CPU/DVFS/thermal/idle/power evidence collector. Run on the
# device through SSH; it never changes a governor, frequency, voltage, CPU
# online state, cpuidle state, thermal mode, or suspend state.

set -u
export LC_ALL=C

heading() {
	printf '\n===== %s =====\n' "$1"
}

read_file() {
	local path="$1"
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	tr '\0' ',' < "$path" | sed 's/,$//'
	printf '\n'
}

heading "running kernel and CPU topology"
uname -a
for path in /sys/devices/system/cpu/{possible,present,online,offline}; do
	read_file "$path"
done
printf '\n[proc/cpuinfo model and topology]\n'
grep -E '^(processor|BogoMIPS|Features|CPU implementer|CPU architecture|CPU variant|CPU part|CPU revision):' \
	/proc/cpuinfo 2>/dev/null || true

heading "CPU frequency policies"
for path in /sys/devices/system/cpu/cpufreq/policy* \
	/sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
	[[ -d "$path" ]] || continue
	printf '[%s]\n' "$path"
	for property in affected_cpus related_cpus scaling_driver scaling_governor \
		available_governors available_frequencies cpuinfo_min_freq cpuinfo_max_freq \
		cpuinfo_transition_latency scaling_min_freq scaling_max_freq \
		scaling_cur_freq; do
		read_file "$path/$property"
	done
	for property in up_threshold down_threshold hispeed_freq go_hispeed_load \
		target_loads min_sample_time timer_rate; do
		read_file "$path/interactive/$property"
	done
done

printf '\n[legacy vendor cpufreq procfs]\n'
for path in /proc/cpufreq /proc/cpufreq/* /proc/cpufreq/*/*; do
	[[ -r "$path" && ! -d "$path" ]] || continue
	printf '[%s]\n' "$path"
	sed -n '1,120p' "$path" 2>/dev/null || true
done

heading "cpuidle states (CPU0)"
for path in /sys/devices/system/cpu/cpu0/cpuidle/state*; do
	[[ -d "$path" ]] || continue
	printf '[%s]\n' "$path"
	for property in name desc latency residency usage time disable; do
		read_file "$path/$property"
	done
done

heading "thermal zones"
for path in /sys/class/thermal/thermal_zone*; do
	[[ -d "$path" ]] || continue
	printf '[%s]\n' "$path"
	for property in type temp mode policy available_policies; do
		read_file "$path/$property"
	done
	for trip in "$path"/trip_point_*_temp; do
		[[ -r "$trip" ]] || continue
		read_file "$trip"
		base="${trip%_temp}"
		read_file "${base}_type"
	done
done

heading "power supplies"
for path in /sys/class/power_supply/*; do
	[[ -d "$path" ]] || continue
	printf '[%s]\n' "$path"
	for property in type online status capacity health voltage_now current_now \
		voltage_max_design charge_full charge_full_design; do
		read_file "$path/$property"
	done
done

heading "system power and suspend metadata"
for path in /sys/power/state /sys/power/mem_sleep /sys/power/disk \
	/sys/power/pm_async; do
	read_file "$path"
done

heading "relevant interrupts"
grep -Ei '(^|[[:space:]])(mtk-thermal|thermal|spm|cpufreq|dvfs|Afe_ISR|arch_timer|timer|wdt|pmic_wrap)' \
	/proc/interrupts 2>/dev/null || true

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(cpufreq|dvfs|dvfsp|thermal|mtkts|spm|sodi|dpidle|mcdi|idle|psci|power domain)' || true
