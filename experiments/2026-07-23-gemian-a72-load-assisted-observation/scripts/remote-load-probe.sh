#!/bin/sh

set -eu
export LC_ALL=C

readonly_cpu_limit=50000
readonly_ap_limit=50000
readonly_pmic_limit=60000
readonly_da9214_limit=80000
sample_interval=0.2
baseline_samples=5
interstage_samples=5
cooldown_samples=75
worker_pids=
observed_a72=no
abort_reason=
sample_index=0
current_stage=preflight
current_workers_requested=0
current_workers_alive_before=0
current_workers_alive_after=0
first_a72_stage=none
first_a72_uptime=none
first_a72_workers_alive_before=0
first_a72_workers_alive_after=0
trigger_attribution=none
deferred_signal_count=0
terminating=no
a72_bracket=unknown

fail()
{
	printf 'failure=%s\n' "$1"
	exit 2
}

flat_read()
{
	[ -r "$1" ] || fail "unreadable-${2}"
	value=$(cat "$1" 2>/dev/null) || fail "read-failed-${2}"
	case "$value" in
	*'
'*) fail "multiline-${2}" ;;
	esac
	printf '%s' "$value"
}

find_thermal_zone()
{
	wanted=$1
	for zone in /sys/class/thermal/thermal_zone*; do
		[ -d "$zone" ] || continue
		[ -r "$zone/type" ] || continue
		zone_type=$(cat "$zone/type" 2>/dev/null || true)
		if [ "$zone_type" = "$wanted" ]; then
			printf '%s' "$zone"
			return 0
		fi
	done
	return 1
}

defer_signal()
{
	deferred_signal_count=$((deferred_signal_count + 1))
}

cleanup_load()
{
	deferred_signal_count=0
	trap defer_signal HUP INT PIPE TERM
	cleanup_pids=$worker_pids
	worker_pids=
	for pid in $cleanup_pids; do
		kill "$pid" 2>/dev/null || true
	done
	for pid in $cleanup_pids; do
		while :; do
			wait_signal_count=$deferred_signal_count
			set +e
			wait "$pid" 2>/dev/null
			set -e
			if [ "$deferred_signal_count" -ne "$wait_signal_count" ] &&
				kill -0 "$pid" 2>/dev/null; then
				continue
			fi
			break
		done
	done
	current_workers_requested=0
	current_workers_alive_before=0
	current_workers_alive_after=0
	if [ "$terminating" = yes ]; then
		trap - HUP INT PIPE TERM
	else
		trap handle_signal HUP INT PIPE TERM
		if [ "$deferred_signal_count" -ne 0 ]; then
			handle_signal
		fi
	fi
}

cleanup_all()
{
	cleanup_load
}

handle_signal()
{
	terminating=yes
	trap - EXIT HUP INT PIPE TERM
	cleanup_load
	printf 'status=aborted reason=signal\n'
	exit 4
}

trap cleanup_all EXIT
trap handle_signal HUP INT PIPE TERM

kernel_release=$(uname -r)
[ "$kernel_release" = 3.18.41+ ] || fail wrong-kernel
[ "$(uname -m)" = aarch64 ] || fail wrong-architecture
[ "$(findmnt -n -o SOURCE / 2>/dev/null)" = /dev/mmcblk0p29 ] || fail wrong-root-findmnt
proc_root=$(awk '$2 == "/" { print $1; exit }' /proc/mounts)
[ "$proc_root" = rootfs ] || fail wrong-root-proc-mounts
[ "$(flat_read /sys/devices/system/cpu/possible possible)" = 0-9 ] || fail wrong-possible
[ "$(flat_read /sys/devices/system/cpu/present present)" = 0-9 ] || fail wrong-present
[ "$(id -u)" = 0 ] || fail not-root

cpu_zone=$(find_thermal_zone mtktscpu) || fail missing-cpu-zone
ap_zone=$(find_thermal_zone mtktsAP) || fail missing-ap-zone
pmic_zone=$(find_thermal_zone mtktspmic) || fail missing-pmic-zone
da9214_zone=$(find_thermal_zone tsda9214) || fail missing-da9214-zone

boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
case "$boot_id_sha256" in
????????????????????????????????????????????????????????????????) ;;
*) fail boot-id-hash ;;
esac

printf 'experiment=gemian-a72-load-assisted-observation\n'
printf 'kernel=%s\n' "$kernel_release"
printf 'architecture=aarch64\n'
printf 'root_findmnt=/dev/mmcblk0p29\n'
printf 'root_proc_mounts=rootfs\n'
printf 'possible=0-9\n'
printf 'present=0-9\n'
printf 'boot_id_sha256=%s\n' "$boot_id_sha256"
printf 'load_command=yes-to-dev-null\n'
printf 'stage_workers=0,1,2,4,8,10\n'
printf 'worker_active_deadline_seconds=3-plus-1-kill-grace\n'
printf 'sample_interval_seconds=%s\n' "$sample_interval"
printf 'cpu_temp_abort_millic=%s\n' "$readonly_cpu_limit"
printf 'ap_temp_abort_millic=%s\n' "$readonly_ap_limit"
printf 'pmic_temp_abort_millic=%s\n' "$readonly_pmic_limit"
printf 'da9214_temp_abort_millic=%s\n' "$readonly_da9214_limit"
printf 'thermal_zone_modes=vendor-enforcement-not-relied-upon\n'
printf 'state_changing_device_writes=none\n'
printf 'cpu_online_writes=none\n'
printf 'policy_writes=none\n'
printf 'partition_access=none\n'

require_hps()
{
	node=$1
	expected=$2
	actual=$(flat_read "/proc/hps/$node" "hps-$node") ||
		fail "hps-read-failed-$node"
	printf '%s=%s\n' "$node" "$actual"
	[ "$actual" = "$expected" ] || fail "hps-policy-mismatch-$node"
}

print_and_require_hps_policy()
{
	printf '__HPS_FIXED_SHOWS_BEGIN__\n'
	require_hps enabled 1
	require_hps init_state 1
	require_hps up_threshold 95
	require_hps up_times 3
	require_hps down_threshold 85
	require_hps down_times 1
	require_hps heavy_task_enabled 1
	require_hps rush_boost_enabled 1
	require_hps rush_boost_threshold 98
	require_hps rush_boost_times 1
	require_hps input_boost_enabled 1
	require_hps input_boost_cpu_num 2
	require_hps suspend_enabled 1
	require_hps tlp_times 1
	require_hps num_base_perf_serv 0
	require_hps num_limit_low_battery 0
	require_hps num_limit_power_serv 0
	require_hps num_limit_thermal 0
	require_hps num_limit_ultra_power_saving 0
	require_hps power_mode 0
	printf '__HPS_FIXED_SHOWS_END__\n'
}

print_and_require_hps_policy

check_unsigned()
{
	case "$1" in
	''|*[!0-9]*) fail "non-integer-$2" ;;
	esac
}

sample_once()
{
	sample_index=$((sample_index + 1))
	current_workers_alive_before=$(count_live_workers)
	uptime=$(awk '{ print $1 }' /proc/uptime) || {
		abort_reason='uptime-read'
		return 1
	}
	online_before=$(flat_read /sys/devices/system/cpu/online online-before) || {
		abort_reason='online-before-read'
		return 1
	}
	cpu8_before=$(flat_read /sys/devices/system/cpu/cpu8/online cpu8-before) || {
		abort_reason='cpu8-before-read'
		return 1
	}
	cpu9_before=$(flat_read /sys/devices/system/cpu/cpu9/online cpu9-before) || {
		abort_reason='cpu9-before-read'
		return 1
	}
	cpu_temp=$(flat_read "$cpu_zone/temp" cpu-temp) || {
		abort_reason='cpu-temp-read'
		return 1
	}
	ap_temp=$(flat_read "$ap_zone/temp" ap-temp) || {
		abort_reason='ap-temp-read'
		return 1
	}
	pmic_temp=$(flat_read "$pmic_zone/temp" pmic-temp) || {
		abort_reason='pmic-temp-read'
		return 1
	}
	da9214_temp=$(flat_read "$da9214_zone/temp" da9214-temp) || {
		abort_reason='da9214-temp-read'
		return 1
	}
	usb_online=$(flat_read /sys/class/power_supply/usb/online usb-online) || {
		abort_reason='usb-online-read'
		return 1
	}
	battery_status=$(flat_read /sys/class/power_supply/battery/status battery-status) || {
		abort_reason='battery-status-read'
		return 1
	}
	battery_capacity=$(flat_read /sys/class/power_supply/battery/capacity battery-capacity) || {
		abort_reason='battery-capacity-read'
		return 1
	}
	battery_health=$(flat_read /sys/class/power_supply/battery/health battery-health) || {
		abort_reason='battery-health-read'
		return 1
	}
	online_after=$(flat_read /sys/devices/system/cpu/online online-after) || {
		abort_reason='online-after-read'
		return 1
	}
	cpu8_after=$(flat_read /sys/devices/system/cpu/cpu8/online cpu8-after) || {
		abort_reason='cpu8-after-read'
		return 1
	}
	cpu9_after=$(flat_read /sys/devices/system/cpu/cpu9/online cpu9-after) || {
		abort_reason='cpu9-after-read'
		return 1
	}
	current_workers_alive_after=$(count_live_workers)

	check_unsigned "$cpu8_before" cpu8-before
	check_unsigned "$cpu9_before" cpu9-before
	check_unsigned "$cpu8_after" cpu8-after
	check_unsigned "$cpu9_after" cpu9-after
	check_unsigned "$cpu_temp" cpu-temp
	check_unsigned "$ap_temp" ap-temp
	check_unsigned "$pmic_temp" pmic-temp
	check_unsigned "$da9214_temp" da9214-temp

	case "$cpu8_before:$cpu8_after:$cpu9_before:$cpu9_after" in
	0:0:0:0) a72_bracket=stable-off ;;
	1:1:0:0|0:0:1:1|1:1:1:1) a72_bracket=stable-on ;;
	0:1:0:0|1:0:0:0|0:0:0:1|0:0:1:0|\
	0:1:0:1|1:0:1:0|0:1:1:0|1:0:0:1|\
	1:1:0:1|1:1:1:0|0:1:1:1|1:0:1:1)
		a72_bracket=changed
		;;
	*) fail invalid-a72-online-value ;;
	esac

	printf 'sample=%s uptime=%s stage=%s workers_requested=%s workers_alive_before=%s workers_alive_after=%s online_before=%s online_after=%s cpu8_before=%s cpu8_after=%s cpu9_before=%s cpu9_after=%s a72_bracket=%s cpu_temp=%s ap_temp=%s pmic_temp=%s da9214_temp=%s usb_online=%s battery_status=%s battery_capacity=%s battery_health=%s\n' \
		"$sample_index" "$uptime" "$current_stage" \
		"$current_workers_requested" "$current_workers_alive_before" \
		"$current_workers_alive_after" \
		"$online_before" "$online_after" \
		"$cpu8_before" "$cpu8_after" "$cpu9_before" "$cpu9_after" \
		"$a72_bracket" \
		"$cpu_temp" "$ap_temp" "$pmic_temp" "$da9214_temp" \
		"$usb_online" "$battery_status" "$battery_capacity" "$battery_health"

	if [ "$usb_online" != 1 ] || [ "$battery_status" != Full ] ||
		[ "$battery_capacity" != 100 ] || [ "$battery_health" != Good ]; then
		abort_reason=power-drift
		return 1
	fi
	if [ "$cpu_temp" -ge "$readonly_cpu_limit" ]; then
		abort_reason=cpu-temperature
		return 1
	fi
	if [ "$ap_temp" -ge "$readonly_ap_limit" ]; then
		abort_reason=ap-temperature
		return 1
	fi
	if [ "$pmic_temp" -ge "$readonly_pmic_limit" ]; then
		abort_reason=pmic-temperature
		return 1
	fi
	if [ "$da9214_temp" -ge "$readonly_da9214_limit" ]; then
		abort_reason=da9214-temperature
		return 1
	fi
	if [ "$cpu8_before" = 1 ] || [ "$cpu8_after" = 1 ] ||
		[ "$cpu9_before" = 1 ] || [ "$cpu9_after" = 1 ]; then
		if [ "$observed_a72" = no ]; then
			first_a72_stage=$current_stage
			first_a72_uptime=$uptime
			first_a72_workers_alive_before=$current_workers_alive_before
			first_a72_workers_alive_after=$current_workers_alive_after
		fi
		observed_a72=yes
	fi
	return 0
}

sample_loop()
{
	remaining=$1
	stop_on_a72=$2
	while [ "$remaining" -gt 0 ]; do
		if ! sample_once; then
			return 1
		fi
		if [ "$stop_on_a72" = yes ] && [ "$observed_a72" = yes ]; then
			return 10
		fi
		remaining=$((remaining - 1))
		if [ "$remaining" -gt 0 ]; then
			sleep "$sample_interval"
		fi
	done
	return 0
}

count_live_workers()
{
	live=0
	for pid in $worker_pids; do
		if kill -0 "$pid" 2>/dev/null; then
			live=$((live + 1))
		fi
	done
	printf '%s' "$live"
}

start_one_worker()
{
	deferred_signal_count=0
	trap defer_signal HUP INT PIPE TERM
	timeout --signal=TERM --kill-after=1s 3s yes >/dev/null &
	new_pid=$!
	worker_pids="$worker_pids $new_pid"
	trap handle_signal HUP INT PIPE TERM
	if [ "$deferred_signal_count" -ne 0 ]; then
		handle_signal
	fi
}

start_load()
{
	requested=$1
	current_workers_requested=$requested
	count=0
	while [ "$count" -lt "$requested" ]; do
		start_one_worker
		count=$((count + 1))
	done
	started_live=$(count_live_workers)
	if [ "$started_live" -ne "$requested" ]; then
		cleanup_load
		fail "stage-population-mismatch-$requested-$started_live"
	fi
}

sample_active_stage()
{
	while :; do
		current_workers_alive_before=$(count_live_workers)
		[ "$current_workers_alive_before" -gt 0 ] || return 0
		if ! sample_once; then
			return 1
		fi
		if [ "$observed_a72" = yes ]; then
			return 10
		fi
		sleep "$sample_interval"
	done
}

run_cooldown()
{
	current_stage=cooldown
	if sample_loop "$cooldown_samples" no; then
		return 0
	else
		cooldown_status=$?
	fi
	if [ "$cooldown_status" -eq 10 ]; then
		fail impossible-cooldown-status
	fi
	printf 'status=aborted reason=%s\n' "$abort_reason"
	exit 3
}

run_uptime_begin=$(awk '{ print $1 }' /proc/uptime) || fail uptime-begin
printf 'run_uptime_begin=%s\n' "$run_uptime_begin"
current_stage=baseline
if sample_loop "$baseline_samples" yes; then
	baseline_status=0
else
	baseline_status=$?
fi
if [ "$baseline_status" -eq 1 ]; then
	printf 'status=aborted reason=%s\n' "$abort_reason"
	exit 3
fi
if [ "$baseline_status" -eq 10 ]; then
	trigger_attribution=not-run-preexisting-a72
	printf 'load_escalation=not-started-preexisting-a72\n'
	run_cooldown
else
	[ "$baseline_status" -eq 0 ] || fail unexpected-baseline-status

	for stage in 1 2 4 8 10; do
		current_stage="policy-preload-$stage"
		print_and_require_hps_policy
		current_stage="preload-$stage"
		preload_gate_sample=1
		while [ "$preload_gate_sample" -le 2 ]; do
			if ! sample_once; then
				printf 'status=aborted reason=%s\n' "$abort_reason"
				exit 3
			fi
			if [ "$observed_a72" = yes ]; then
				trigger_attribution="delayed-before-load-$stage"
				printf 'load_escalation=stopped-before-stage stage=%s\n' \
					"$stage"
				break
			fi
			[ "$a72_bracket" = stable-off ] ||
				fail "preload-a72-bracket-not-stable-off-$stage"
			preload_gate_sample=$((preload_gate_sample + 1))
		done
		[ "$observed_a72" = no ] || break

		current_stage="load-$stage"
		printf 'stage_begin=%s uptime=%s\n' "$stage" \
			"$(awk '{ print $1 }' /proc/uptime)"
		start_load "$stage"
		if sample_active_stage; then
			stage_status=0
		else
			stage_status=$?
		fi
		cleanup_load
		printf 'stage_end=%s uptime=%s status=%s\n' "$stage" \
			"$(awk '{ print $1 }' /proc/uptime)" "$stage_status"
		if [ "$stage_status" -eq 1 ]; then
			printf 'status=aborted reason=%s\n' "$abort_reason"
			exit 3
		fi
		if [ "$stage_status" -eq 10 ]; then
			if [ "$first_a72_workers_alive_before" -eq "$stage" ] &&
				[ "$first_a72_workers_alive_after" -eq "$stage" ]; then
				trigger_attribution="active-full-load-$stage"
			elif [ "$first_a72_workers_alive_before" -gt 0 ] ||
				[ "$first_a72_workers_alive_after" -gt 0 ]; then
				trigger_attribution="active-partial-load-$stage"
			else
				trigger_attribution="delayed-during-load-label-$stage"
			fi
			printf 'load_escalation=stopped-after-a72-observation stage=%s\n' \
				"$stage"
			break
		fi
		[ "$stage_status" -eq 0 ] || fail unexpected-stage-status

		current_stage="interstage-$stage"
		if sample_loop "$interstage_samples" yes; then
			interstage_status=0
		else
			interstage_status=$?
		fi
		if [ "$interstage_status" -eq 1 ]; then
			printf 'status=aborted reason=%s\n' "$abort_reason"
			exit 3
		fi
		if [ "$interstage_status" -eq 10 ]; then
			trigger_attribution="delayed-after-load-$stage"
			printf 'load_escalation=stopped-during-interstage stage=%s\n' \
				"$stage"
			break
		fi
		[ "$interstage_status" -eq 0 ] || fail unexpected-interstage-status
	done
	run_cooldown
fi

if [ "$observed_a72" = yes ] && [ "$trigger_attribution" = none ]; then
	trigger_attribution=delayed-during-cooldown
fi
printf '__HPS_FIXED_SHOWS_FINAL_BEGIN__\n'
print_and_require_hps_policy
printf '__HPS_FIXED_SHOWS_FINAL_END__\n'
final_boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
[ "$final_boot_id_sha256" = "$boot_id_sha256" ] || fail boot-id-changed
run_uptime_end=$(awk '{ print $1 }' /proc/uptime) || fail uptime-end
final_online=$(flat_read /sys/devices/system/cpu/online final-online)
printf 'observed_a72=%s\n' "$observed_a72"
printf 'first_a72_stage=%s\n' "$first_a72_stage"
printf 'first_a72_uptime=%s\n' "$first_a72_uptime"
printf 'first_a72_workers_alive_before=%s\n' "$first_a72_workers_alive_before"
printf 'first_a72_workers_alive_after=%s\n' "$first_a72_workers_alive_after"
printf 'trigger_attribution=%s\n' "$trigger_attribution"
printf 'run_uptime_end=%s\n' "$run_uptime_end"
printf 'final_online=%s\n' "$final_online"
printf 'boot_id_stable=yes\n'
printf 'workers_cleaned=yes\n'
printf 'status=completed\n'
