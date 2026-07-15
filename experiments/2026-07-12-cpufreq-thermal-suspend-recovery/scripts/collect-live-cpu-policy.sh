#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Read-only vendor CPU/DVFS policy capture.  Do not add writes to /proc/cpufreq.

set -euo pipefail

printf 'validation=vendor-cpu-policy-live\n'
printf 'kernel='; uname -a
printf 'online='; cat /sys/devices/system/cpu/online 2>/dev/null || printf 'unavailable'
printf '\npresent='; cat /sys/devices/system/cpu/present 2>/dev/null || printf 'unavailable'
printf '\npossible='; cat /sys/devices/system/cpu/possible 2>/dev/null || printf 'unavailable'
printf '\n'

printf 'sysfs_cpufreq_policies='
find /sys/devices/system/cpu/cpufreq -mindepth 1 -maxdepth 1 -type d \
	-name 'policy*' -print 2>/dev/null | sort | tr '\n' ' '
printf '\n'

for path in \
	/proc/cpufreq/cpufreq_freq \
	/proc/cpufreq/cpufreq_oppidx \
	/proc/cpufreq/cpufreq_idvfs_mode \
	/proc/cpufreq/cpufreq_power_mode \
	/proc/cpufreq/cpufreq_turbo_mode \
	/proc/cpufreq/cpufreq_volt \
	/proc/cpufreq/enable_cpuhvfs \
	/proc/cpufreq/enable_hw_gov; do
	[ -r "$path" ] || continue
	printf '%s=' "${path#/proc/cpufreq/}"
	tr '\n' ' ' <"$path"
	printf '\n'
done

for cluster in B CCI L LL; do
	dir="/proc/cpufreq/MT_CPU_DVFS_${cluster}"
	[ -d "$dir" ] || continue
	printf 'cluster=%s\n' "$cluster"
	for name in cpufreq_freq cpufreq_oppidx cpufreq_turbo_mode cpufreq_volt; do
		[ -r "$dir/$name" ] || continue
		printf '%s=' "$name"
		tr '\n' ' ' <"$dir/$name"
		printf '\n'
	done
done

printf 'dmesg_dvfs_tail=\n'
dmesg 2>/dev/null | grep -Ei 'cpufreq|DVFS|EEM|PTP|Bigi|ARMPLL|cpu.*freq' \
	| tail -n 40 || true
