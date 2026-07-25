#!/bin/sh

set -eu
export LC_ALL=C

section() { printf '\n__GEMIAN_%s__\n' "$1"; }
dump_file() {
	path=$1
	printf '\n-- %s --\n' "$path"
	if [ -r "$path" ]; then
		cat "$path" 2>&1 || printf 'read-failed\n'
	else
		printf 'absent-or-unreadable\n'
	fi
}
dump_cpu_leaf() {
	cpu=$1
	leaf=$2
	path="/sys/devices/system/cpu/$cpu/$leaf"
	if [ -r "$path" ]; then
		printf '%s=' "$leaf"
		cat "$path"
	fi
}

section IDENTITY
printf 'kernel='; uname -r
printf 'architecture='; uname -m
printf 'root='; findmnt -n -o SOURCE /
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
printf 'cmdline='; sed 's/androidboot\.serialno=[^ ]*/androidboot.serialno=REDACTED/' /proc/cmdline
printf 'possible='; cat /sys/devices/system/cpu/possible
printf 'present='; cat /sys/devices/system/cpu/present
printf 'online='; cat /sys/devices/system/cpu/online
printf 'offline='; cat /sys/devices/system/cpu/offline
printf 'isolated='; cat /sys/devices/system/cpu/isolated 2>/dev/null || printf '\n'
printf 'uptime='; cat /proc/uptime
printf 'power_ac='; cat /sys/class/power_supply/ac/online
printf 'power_usb='; cat /sys/class/power_supply/usb/online
printf 'battery_present='; cat /sys/class/power_supply/battery/present
printf 'battery_status='; cat /sys/class/power_supply/battery/status
printf 'battery_capacity='; cat /sys/class/power_supply/battery/capacity
printf 'battery_health='; cat /sys/class/power_supply/battery/health

section CPUINFO_FILTERED
grep -E '^(processor|model name|BogoMIPS|Features|CPU implementer|CPU architecture|CPU variant|CPU part|CPU revision)[[:space:]]*:' /proc/cpuinfo || true

section CPU_TOPOLOGY
for cpu_dir in /sys/devices/system/cpu/cpu[0-9]*; do
	cpu=${cpu_dir##*/}
	printf '\n[%s]\n' "$cpu"
	for leaf in \
		online cpu_capacity cpu_capacity_orig \
		topology/core_id topology/physical_package_id \
		topology/thread_siblings_list topology/core_siblings_list \
		cpufreq/cpuinfo_cur_freq cpufreq/cpuinfo_min_freq cpufreq/cpuinfo_max_freq \
		cpufreq/scaling_cur_freq cpufreq/scaling_min_freq cpufreq/scaling_max_freq \
		cpufreq/scaling_governor cpufreq/scaling_available_governors; do
		dump_cpu_leaf "$cpu" "$leaf"
	done
done

section KERNEL_CONFIG
if [ -r /proc/config.gz ]; then
	zcat /proc/config.gz | grep -E '^(# )?CONFIG_(SMP|NR_CPUS|HOTPLUG_CPU|SCHED|FAIR|CFS|RT_GROUP|CGROUP|CPUSETS|HMP|HPS|ENERGY|EAS|WALT|ARCH_SCALE|FREQ_INVARIANT|CPU_FREQ|CPU_IDLE|ARM_PSCI|MTK_HPS|MTK_PPM|MTK_CPU|MT_CPU|MTK_SCHED|MT_SCHED|MIGRATION|NO_HZ|IRQ_TIME|SCHEDSTATS)' || true
else
	printf 'proc-config=absent\n'
fi

section HPS
for path in /proc/hps/*; do
	[ -f "$path" ] || continue
	dump_file "$path"
done

section PPM
for path in \
	/proc/ppm/enabled /proc/ppm/mode /proc/ppm/root_cluster \
	/proc/ppm/policy_status /proc/ppm/dump_policy_list \
	/proc/ppm/dump_cluster_0_dvfs_table /proc/ppm/dump_cluster_1_dvfs_table \
	/proc/ppm/dump_cluster_2_dvfs_table \
	/proc/ppm/policy/hica_power_state /proc/ppm/policy/hica_is_limit_big_freq \
	/proc/ppm/policy/userlimit_min_cpu_core /proc/ppm/policy/userlimit_max_cpu_core \
	/proc/ppm/policy/userlimit_min_cpu_freq /proc/ppm/policy/userlimit_max_cpu_freq \
	/proc/ppm/policy/forcelimit_cpu_core /proc/ppm/policy/sysboost_core \
	/proc/ppm/policy/sysboost_freq /proc/ppm/policy/thermal_cur_power \
	/proc/ppm/policy/thermal_limit /proc/ppm/policy/perfserv_min_perf_idx \
	/proc/ppm/policy/perfserv_max_perf_idx /proc/ppm/policy/perfserv_perf_idx; do
	dump_file "$path"
done

section CPUFREQ_VENDOR
for path in \
	/proc/cpufreq/enable_cpuhvfs /proc/cpufreq/enable_hw_gov \
	/proc/cpufreq/cpufreq_idvfs_mode /proc/cpufreq/cpufreq_power_mode \
	/proc/cpufreq/MT_CPU_DVFS_LL/cpufreq_freq \
	/proc/cpufreq/MT_CPU_DVFS_LL/cpufreq_oppidx \
	/proc/cpufreq/MT_CPU_DVFS_L/cpufreq_freq \
	/proc/cpufreq/MT_CPU_DVFS_L/cpufreq_oppidx \
	/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_freq \
	/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_oppidx \
	/proc/cpufreq/MT_CPU_DVFS_CCI/cpufreq_freq \
	/proc/cpufreq/MT_CPU_DVFS_CCI/cpufreq_oppidx; do
	dump_file "$path"
done

section EEM_BIG_CLUSTER
for path in \
	/proc/eem/EEM_DET_2L/eem_status /proc/eem/EEM_DET_2L/eem_cur_volt \
	/proc/eem/EEM_DET_L/eem_status /proc/eem/EEM_DET_L/eem_cur_volt \
	/proc/eem/EEM_DET_BIG/eem_status /proc/eem/EEM_DET_BIG/eem_cur_volt \
	/proc/eem/EEM_DET_CCI/eem_status /proc/eem/EEM_DET_CCI/eem_cur_volt; do
	dump_file "$path"
done

section SCHED_SYSCTL
for path in /proc/sys/kernel/sched_*; do
	[ -f "$path" ] || continue
	dump_file "$path"
done
dump_file /proc/sys/kernel/numa_balancing
dump_file /proc/irq/default_smp_affinity
dump_file /proc/mtk_sched/affinity_status

section CPUSET_MOUNTS
grep -E '(/dev/cpuset|/sys/fs/cgroup/cpuset)' /proc/mounts || printf 'no-known-cpuset-mount\n'
if [ -e /dev/cpuset ]; then
	find /dev/cpuset -maxdepth 2 -type d 2>/dev/null | sort
else
	printf 'dev_cpuset=absent\n'
fi

section CPUSETS
for group in '' background system-background foreground foreground/boost top-app lxc lxc/android; do
	dir="/sys/fs/cgroup/cpuset${group:+/$group}"
	[ -d "$dir" ] || continue
	printf '\n[%s]\n' "${group:-root}"
	for leaf in cpuset.cpus cpuset.effective_cpus cpuset.mems cpuset.sched_load_balance cpuset.sched_relax_domain_level; do
		if [ -r "$dir/$leaf" ]; then
			printf '%s=' "$leaf"
			cat "$dir/$leaf"
		fi
	done
done

section SCHED_DEBUG
dump_file /proc/sched_debug
dump_file /proc/schedstat
dump_file /sys/kernel/debug/sched_features

section NATURAL_HPS_SAMPLES
sample=1
while [ "$sample" -le 20 ]; do
	uptime_value=$(cut -d ' ' -f 1 /proc/uptime)
	online_value=$(cat /sys/devices/system/cpu/online)
	offline_value=$(cat /sys/devices/system/cpu/offline)
	hps_state=$(tr '\n' ';' </proc/hps/state 2>/dev/null) || hps_state=unavailable
	ppm_state=$(tr '\n' ';' </proc/ppm/policy/hica_power_state 2>/dev/null) || ppm_state=unavailable
	printf 'sample=%s uptime=%s online=%s offline=%s hps_state=%s ppm_state=%s\n' \
		"$sample" "$uptime_value" "$online_value" "$offline_value" \
		"$hps_state" "$ppm_state"
	sample=$((sample + 1))
	sleep 1
done

section DMESG_FILTERED
dmesg | grep -Ei '(^|[^a-z])(cpu[0-9]|smp|psci|hps|ppm|cpufreq|dvfs|idvfs|bigi|sched|hmp|eas)([^a-z]|$)' | tail -n 1200 || true

section COMPLETE
printf 'device_writes=none\n'
