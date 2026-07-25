#!/bin/sh

set -eu
export LC_ALL=C

observer_root=${GEMINI_OBSERVER_TEST_ROOT:-}
sample_count=${GEMINI_OBSERVER_SAMPLES:-180}
sample_interval=${GEMINI_OBSERVER_INTERVAL:-1}
healthy_battery_state='battery_present=1;battery_status=Full;battery_capacity=100;battery_health=Good'

case "$observer_root" in
''|/*) ;;
*)
	printf 'error: GEMINI_OBSERVER_TEST_ROOT must be empty or absolute\n' >&2
	exit 2
	;;
esac

case "$sample_count" in
''|*[!0-9]*)
	printf 'error: GEMINI_OBSERVER_SAMPLES must be an integer\n' >&2
	exit 2
	;;
esac
case "$sample_interval" in
''|*[!0-9]*)
	printf 'error: GEMINI_OBSERVER_INTERVAL must be an integer\n' >&2
	exit 2
	;;
esac
if [ "$sample_count" -lt 1 ] || [ "$sample_count" -gt 900 ]; then
	printf 'error: GEMINI_OBSERVER_SAMPLES must be between 1 and 900\n' >&2
	exit 2
fi
if [ "$sample_interval" -gt 60 ]; then
	printf 'error: GEMINI_OBSERVER_INTERVAL must be between 0 and 60\n' >&2
	exit 2
fi
if [ $((sample_count * sample_interval)) -gt 900 ]; then
	printf 'error: requested sample duration exceeds 900 seconds\n' >&2
	exit 2
fi

section()
{
	printf '\n__GEMIAN_A72_%s__\n' "$1"
}

resolve_path()
{
	printf '%s%s' "$observer_root" "$1"
}

read_flat()
{
	read_flat_logical=$1
	read_flat_actual=$(resolve_path "$read_flat_logical")
	if [ -n "$observer_root" ] && [ -n "${sample:-}" ]; then
		read_flat_failure_fixture=$(resolve_path "/test/sample-$sample-read-failed")
		if [ -r "$read_flat_failure_fixture" ] &&
			grep -Fqx "$read_flat_logical" "$read_flat_failure_fixture"; then
			printf 'read-failed'
			return 0
		fi
	fi
	if [ ! -r "$read_flat_actual" ]; then
		printf 'absent-or-unreadable'
		return 0
	fi
	if read_flat_value=$(awk '
		BEGIN { separator = "" }
		{ printf "%s%s", separator, $0; separator = ";" }
		END { print "" }
	' "$read_flat_actual" 2>/dev/null); then
		printf '%s' "$read_flat_value"
	else
		printf 'read-failed'
	fi
}

dump_safe_path()
{
	dump_logical=$1
	dump_actual=$(resolve_path "$dump_logical")
	printf '\n-- %s --\n' "$dump_logical"
	if [ -n "$observer_root" ]; then
		dump_failure_fixture=$(resolve_path /test/dump-safe-read-failed)
		if [ -r "$dump_failure_fixture" ] &&
			grep -Fqx "$dump_logical" "$dump_failure_fixture"; then
			printf 'read-failed\n'
			fail_stop read-failed-safe-context
		fi
	fi
	if [ ! -r "$dump_actual" ]; then
		printf 'absent-or-unreadable\n'
		return 0
	fi
	if ! awk '{ print }' "$dump_actual" 2>&1; then
		printf 'read-failed\n'
		fail_stop read-failed-safe-context
	fi
}

metadata_only()
{
	metadata_logical=$1
	metadata_actual=$(resolve_path "$metadata_logical")
	if [ ! -e "$metadata_actual" ] && [ ! -L "$metadata_actual" ]; then
		printf '%s absent\n' "$metadata_logical"
		return 0
	fi
	if metadata_value=$(ls -ldn "$metadata_actual" 2>/dev/null); then
		set -- $metadata_value
		printf '%s present mode=%s uid=%s gid=%s content_read=no\n' \
			"$metadata_logical" "${1:-unknown}" "${3:-unknown}" "${4:-unknown}"
	else
		printf '%s present metadata=unavailable content_read=no\n' "$metadata_logical"
	fi
}

redacted_cmdline()
{
	cmdline_actual=$(resolve_path /proc/cmdline)
	if [ ! -r "$cmdline_actual" ]; then
		printf 'absent-or-unreadable'
		return 0
	fi
	sed \
		-e 's/androidboot\.serialno=[^ ]*/androidboot.serialno=REDACTED/g' \
		-e 's/androidboot\.uniqueno=[^ ]*/androidboot.uniqueno=REDACTED/g' \
		"$cmdline_actual"
}

root_findmnt_source()
{
	if [ -n "$observer_root" ]; then
		read_flat /test/findmnt-root-source
		return 0
	fi
	if ! command -v findmnt >/dev/null 2>&1; then
		printf 'absent-or-unreadable'
		return 0
	fi
	if root_findmnt_value=$(findmnt -n -o SOURCE / 2>/dev/null); then
		if [ -n "$root_findmnt_value" ]; then
			printf '%s' "$root_findmnt_value"
		else
			printf 'absent-or-unreadable'
		fi
	else
		printf 'read-failed'
	fi
}

root_proc_mounts_source()
{
	mounts_actual=$(resolve_path /proc/mounts)
	if [ ! -r "$mounts_actual" ]; then
		printf 'absent-or-unreadable'
		return 0
	fi
	if root_proc_value=$(awk '
		$2 == "/" { print $1; found = 1; exit }
		END { if (!found) print "not-found" }
	' "$mounts_actual" 2>/dev/null); then
		printf '%s' "$root_proc_value"
	else
		printf 'read-failed'
	fi
}

kernel_release()
{
	if [ -n "$observer_root" ]; then
		read_flat /test/uname-r
	else
		uname -r
	fi
}

machine_architecture()
{
	if [ -n "$observer_root" ]; then
		read_flat /test/uname-m
	else
		uname -m
	fi
}

power_state()
{
	printf 'ac=%s;usb=%s;battery_present=%s;battery_status=%s;battery_capacity=%s;battery_health=%s' \
		"$(read_flat /sys/class/power_supply/ac/online)" \
		"$(read_flat /sys/class/power_supply/usb/online)" \
		"$(read_flat /sys/class/power_supply/battery/present)" \
		"$(read_flat /sys/class/power_supply/battery/status)" \
		"$(read_flat /sys/class/power_supply/battery/capacity)" \
		"$(read_flat /sys/class/power_supply/battery/health)"
}

sample_power_state()
{
	sample_power_stage=$1
	if [ -n "$observer_root" ]; then
		sample_power_fixture=$(resolve_path "/test/sample-$sample-power-$sample_power_stage")
		if [ -r "$sample_power_fixture" ]; then
			read_flat "/test/sample-$sample-power-$sample_power_stage"
			return 0
		fi
	fi
	power_state
}

gate_fail()
{
	gate_failure_code=$1
	gate_failure_detail=${2:-}
	case "$gate_failure_code" in
	''|*[!a-z0-9._-]*) gate_failure_code=invalid-internal-gate-code ;;
	esac
	printf 'failure=%s\n' "$gate_failure_code"
	if [ -n "$gate_failure_detail" ]; then
		printf 'error: pre-sample Gemian gate failed: %s (%s)\n' \
			"$gate_failure_code" "$gate_failure_detail" >&2
	else
		printf 'error: pre-sample Gemian gate failed: %s\n' "$gate_failure_code" >&2
	fi
	exit 3
}

fail_stop()
{
	failure_code=$1
	case "$failure_code" in
	''|*[!a-z0-9._-]*) failure_code=invalid-internal-failure-code ;;
	esac
	printf 'failure=%s\n' "$failure_code"
	printf 'error: collector fail-stop: %s\n' "$failure_code" >&2
	exit 4
}

require_observable_read()
{
	require_observable_name=$1
	require_observable_value=$2
	if [ "$require_observable_value" = read-failed ]; then
		fail_stop "read-failed-$require_observable_name"
	fi
}

require_sample_read()
{
	require_sample_name=$1
	require_sample_value=$2
	case "$require_sample_value" in
	read-failed) fail_stop "read-failed-$require_sample_name" ;;
	absent-or-unreadable) fail_stop "required-read-unavailable-$require_sample_name" ;;
	esac
}

require_stable_healthy_power()
{
	require_power_label=$1
	require_power_value=$2
	require_power_expected=$3
	case "$require_power_value" in
	*read-failed*|*absent-or-unreadable*)
		fail_stop "$require_power_label-unobservable"
		;;
	esac
	case "$require_power_value" in
	"ac=0;usb=1;$healthy_battery_state"|\
	"ac=1;usb=0;$healthy_battery_state"|\
	"ac=1;usb=1;$healthy_battery_state") ;;
	"ac=0;usb=0;$healthy_battery_state")
		fail_stop "$require_power_label-external-power-unhealthy"
		;;
	ac=0\;usb=0\;battery_present=*|ac=0\;usb=1\;battery_present=*|\
	ac=1\;usb=0\;battery_present=*|ac=1\;usb=1\;battery_present=*)
		fail_stop "$require_power_label-battery-unhealthy"
		;;
	*) fail_stop "$require_power_label-unobservable" ;;
	esac
	[ "$require_power_value" = "$require_power_expected" ] ||
		fail_stop "$require_power_label-state-changed"
}

# Only generic identity and power files are read before this gate.  No vendor
# procfs/debugfs callback or DA9214 transaction occurs unless every condition
# below is exact and stable.
gate_kernel=$(kernel_release)
gate_architecture=$(machine_architecture)
gate_root_findmnt=$(root_findmnt_source)
gate_root_proc_mounts=$(root_proc_mounts_source)
gate_possible=$(read_flat /sys/devices/system/cpu/possible)
gate_present=$(read_flat /sys/devices/system/cpu/present)
gate_boot_id_first=$(read_flat /proc/sys/kernel/random/boot_id)
gate_power_first=$(power_state)
if [ -z "$observer_root" ]; then
	sleep 1
fi
if [ -n "$observer_root" ] && [ -r "$(resolve_path /test/boot-id-second)" ]; then
	gate_boot_id_second=$(read_flat /test/boot-id-second)
else
	gate_boot_id_second=$(read_flat /proc/sys/kernel/random/boot_id)
fi
if [ -n "$observer_root" ] && [ -r "$(resolve_path /test/power-second)" ]; then
	gate_power_second=$(read_flat /test/power-second)
else
	gate_power_second=$(power_state)
fi

[ "$gate_kernel" = '3.18.41+' ] || gate_fail gate-kernel-mismatch "kernel=$gate_kernel"
[ "$gate_architecture" = aarch64 ] || gate_fail gate-architecture-mismatch "architecture=$gate_architecture"
case "$gate_root_findmnt" in
''|read-failed|absent-or-unreadable|not-found)
	gate_fail gate-root-findmnt-unavailable
	;;
esac
[ "$gate_root_findmnt" = /dev/mmcblk0p29 ] ||
	gate_fail gate-root-findmnt-mismatch "findmnt_root=$gate_root_findmnt"
case "$gate_root_proc_mounts" in
''|read-failed|absent-or-unreadable|not-found)
	gate_fail gate-root-proc-mounts-unavailable
	;;
esac
[ "$gate_root_proc_mounts" = rootfs ] ||
	gate_fail gate-root-proc-mounts-mismatch "proc_mounts_root=$gate_root_proc_mounts"
[ "$gate_possible" = 0-9 ] || gate_fail gate-possible-mismatch "possible=$gate_possible"
[ "$gate_present" = 0-9 ] || gate_fail gate-present-mismatch "present=$gate_present"
printf '%s\n' "$gate_boot_id_first" | \
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || \
	gate_fail gate-boot-id-malformed
[ "$gate_boot_id_second" = "$gate_boot_id_first" ] || gate_fail gate-boot-id-changed
case "$gate_power_first;$gate_power_second" in
*read-failed*|*absent-or-unreadable*) gate_fail gate-power-unobservable ;;
esac
[ "$gate_power_second" = "$gate_power_first" ] || gate_fail gate-power-state-changed
case "$gate_power_first" in
"ac=0;usb=1;$healthy_battery_state"|\
"ac=1;usb=0;$healthy_battery_state"|\
"ac=1;usb=1;$healthy_battery_state") ;;
"ac=0;usb=0;$healthy_battery_state")
	gate_fail gate-external-power-absent "$gate_power_first"
	;;
ac=0\;usb=0\;battery_present=*|ac=0\;usb=1\;battery_present=*|\
ac=1\;usb=0\;battery_present=*|ac=1\;usb=1\;battery_present=*)
	gate_fail gate-battery-unhealthy "$gate_power_first"
	;;
*) gate_fail gate-power-unobservable ;;
esac

section IDENTITY
printf 'format=gemian-a72-readonly-discovery-v2\n'
printf 'captured_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'identity_gate=pass\n'
printf 'power_gate=pass\n'
printf 'kernel=%s\n' "$gate_kernel"
printf 'architecture=%s\n' "$gate_architecture"
printf 'root_findmnt_source=%s\n' "$gate_root_findmnt"
printf 'root_proc_mounts_source=%s\n' "$gate_root_proc_mounts"
printf 'boot_id=%s\n' "$gate_boot_id_first"
printf 'cmdline=%s\n' "$(redacted_cmdline)"
printf 'possible=%s\n' "$(read_flat /sys/devices/system/cpu/possible)"
printf 'present=%s\n' "$(read_flat /sys/devices/system/cpu/present)"
printf 'online=%s\n' "$(read_flat /sys/devices/system/cpu/online)"
printf 'offline=%s\n' "$(read_flat /sys/devices/system/cpu/offline)"
printf 'uptime=%s\n' "$(read_flat /proc/uptime)"
printf 'power_ac=%s\n' "$(read_flat /sys/class/power_supply/ac/online)"
printf 'power_usb=%s\n' "$(read_flat /sys/class/power_supply/usb/online)"
printf 'battery_status=%s\n' "$(read_flat /sys/class/power_supply/battery/status)"
printf 'battery_present=%s\n' "$(read_flat /sys/class/power_supply/battery/present)"
printf 'battery_capacity=%s\n' "$(read_flat /sys/class/power_supply/battery/capacity)"
printf 'battery_health=%s\n' "$(read_flat /sys/class/power_supply/battery/health)"

section SAFE_CONTEXT
printf 'idvfs_debug_contract=driver-serialized-address-read;page-unobserved;selector-must-report-0xd9\n'
printf 'idvfs_debug_bus_semantics=i2c-register-address-phase-plus-read;no-register-value-write\n'
printf 'b_freq_contract=vendor-reported-cached-opp;not-raw-clock-state\n'
printf 'cci_freq_contract=vendor-derived-register-read;not-dvfsp-semaphore-protected\n'
printf 'cpufreq_volt_contract=metadata-only;content-excluded-because-online-b-path-may-call-smc-0x8200035f\n'
printf 'sample_contract=sequential-userspace-mask-bracket;never-atomic\n'
context_power_before=$(power_state)
require_stable_healthy_power safe-context-before "$context_power_before" "$gate_power_first"
dump_safe_path /sys/kernel/debug/cpuhvfs/dvfsp_reg
context_power_after=$(power_state)
require_stable_healthy_power safe-context-after "$context_power_after" "$gate_power_first"
printf 'safe_context_power_before=%s\n' "$context_power_before"
printf 'safe_context_power_after=%s\n' "$context_power_after"

section EXCLUDED_SURFACE_METADATA
printf 'notice=metadata-only;the following callbacks are deliberately not opened\n'
metadata_only "/proc/idvfs/dvt_test"
metadata_only "/sys/devices/platform/da9214-user/da9214_access"
metadata_only "/sys/bus/platform/devices/da9214-user/da9214_access"
metadata_only "/sys/kernel/debug/cpuhvfs/dbg_repo"
metadata_only "/sys/power/dcm_state"
metadata_only "/proc/clkmgr/armbpll_fsel"
metadata_only "/proc/clkmgr/armccipll_fsel"
metadata_only "/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_volt"

section NATURAL_SAMPLES
printf 'sample_count=%s\n' "$sample_count"
printf 'sample_interval_seconds=%s\n' "$sample_interval"
boot_id=$gate_boot_id_first
sample=1
while [ "$sample" -le "$sample_count" ]; do
	power_before=$(sample_power_state before)
	require_stable_healthy_power "sample-$sample-power-before" "$power_before" "$gate_power_first"
	uptime_before=$(read_flat /proc/uptime)
	require_sample_read uptime_before "$uptime_before"
	online_before=$(read_flat /sys/devices/system/cpu/online)
	require_sample_read online_before "$online_before"
	da9214_debug=$(read_flat /proc/idvfs/idvfs_debug)
	require_observable_read da9214_debug "$da9214_debug"
	case "$da9214_debug" in
	*"I2C_reg[0xd9]"*) da9214_selector=reported-0xd9 ;;
	*) da9214_selector=not-confirmed ;;
	esac
	b_freq=$(read_flat /proc/cpufreq/MT_CPU_DVFS_B/cpufreq_freq)
	require_observable_read b_freq "$b_freq"
	cci_freq=$(read_flat /proc/cpufreq/MT_CPU_DVFS_CCI/cpufreq_freq)
	require_observable_read cci_freq "$cci_freq"
	online_after=$(read_flat /sys/devices/system/cpu/online)
	require_sample_read online_after "$online_after"
	uptime_after=$(read_flat /proc/uptime)
	require_sample_read uptime_after "$uptime_after"
	power_after=$(sample_power_state after)
	require_stable_healthy_power "sample-$sample-power-after" "$power_after" "$power_before"
	[ "$power_after" = "$gate_power_first" ] ||
		fail_stop "sample-$sample-power-after-state-changed"
	if [ "$online_before" = "$online_after" ]; then
		mask_bracket=stable-nonatomic
	else
		mask_bracket=changed-torn
	fi

	printf 'sample_begin=%s\n' "$sample"
	printf 'boot_id=%s\n' "$boot_id"
	printf 'uptime_before=%s\n' "$uptime_before"
	printf 'online_before=%s\n' "$online_before"
	printf 'da9214_selector=%s\n' "$da9214_selector"
	printf 'da9214_debug=%s\n' "$da9214_debug"
	printf 'b_freq=%s\n' "$b_freq"
	printf 'cci_freq=%s\n' "$cci_freq"
	printf 'power_before=%s\n' "$power_before"
	printf 'power_after=%s\n' "$power_after"
	printf 'online_after=%s\n' "$online_after"
	printf 'uptime_after=%s\n' "$uptime_after"
	printf 'mask_bracket=%s\n' "$mask_bracket"
	printf 'sample_end=%s\n' "$sample"

	if [ "$sample" -lt "$sample_count" ] && [ "$sample_interval" -ne 0 ]; then
		sleep "$sample_interval"
	fi
	sample=$((sample + 1))
done

section SAMPLING_BOUNDARY
sampling_end_power=$(power_state)
require_stable_healthy_power sampling-end-power "$sampling_end_power" "$gate_power_first"
printf 'sampling_end_power=%s\n' "$sampling_end_power"
printf 'vendor_sampling_contract=ended-before-dmesg\n'

section DMESG_FILTERED
if [ -n "$observer_root" ]; then
	test_dmesg=$(resolve_path /test/dmesg)
	if [ -r "$test_dmesg" ]; then
		awk '{ print }' "$test_dmesg"
	else
		printf 'test-dmesg=absent\n'
	fi
else
	dmesg 2>&1 | grep -Ei \
		'(^|[^a-z])(cpu8|cpu9|psci|idvfs|bigi|da9214|buck|dcm|cci|hps)([^a-z]|$)' | \
		tail -n 1600 || true
fi

section COMPLETE
if [ -n "$observer_root" ] && [ -r "$(resolve_path /test/boot-id-final)" ]; then
	final_boot_id=$(read_flat /test/boot-id-final)
else
	final_boot_id=$(read_flat /proc/sys/kernel/random/boot_id)
fi
require_observable_read final_boot_id "$final_boot_id"
[ "$final_boot_id" = "$gate_boot_id_first" ] || fail_stop boot-id-changed-during-capture
printf 'boot_id_stable_through_capture=yes\n'
printf 'remote_files_created=none\n'
printf 'state_changing_writes=none\n'
printf 'policy_changes=none\n'
printf 'da9214_bus_operation=driver-serialized-register-address-read\n'
printf 'collector_smc_calls=none\n'
printf 'cpufreq_volt_content_read=no\n'
printf 'capture_scope=partial-existing-surfaces-only\n'
