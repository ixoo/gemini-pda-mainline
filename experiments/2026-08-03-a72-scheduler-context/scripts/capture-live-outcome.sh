#!/usr/bin/env bash

# Read-only best-effort capture of adjacent pair-v6 and pair-v7 terminals over
# the Gemini USB/netcat console. Changed-cycle pstore remains primary evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --output artifacts/runtime-captures/a72-scheduler-attempt-N/runtime.txt\n' "$0" >&2
}

output=
while (($#)); do
	case "$1" in
	--output) (($# >= 2)) || die '--output requires a value'; output=$2; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage; exit 2; }
for command in awk basename chmod dirname git grep ifconfig mkdir mktemp nc rm route sleep; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime-capture root is absent'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" &&
	"$(basename -- "$capture_dir")" == a72-scheduler-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new a72-scheduler-attempt-* private child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] || die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" || die 'capture directory is not ignored by Git'
mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"

command_file="$(mktemp "${TMPDIR:-/tmp}/.a72-scheduler-live.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
chmod 0600 "$command_file"
cat >"$command_file" <<'DEVICE'
printf '__A72_SCHEDULER_LIVE_BEGIN__\n'
printf 'kernel_release=%s\n' "$(/bin/busybox uname -r)"
printf 'kernel_version=%s\n' "$(/bin/busybox uname -v)"
printf 'cpu_online_initial=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
printf 'cpu_present=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/present)"
i=0
while [ "$i" -lt 30 ]; do
	pair7="$(/bin/busybox dmesg | /bin/busybox grep -E 'gemini-a72-pair-v7 result=(pass|fault)' | /bin/busybox tail -n 1)"
	if [ -n "$pair7" ]; then
		pair6="$(/bin/busybox dmesg | /bin/busybox grep -E 'gemini-a72-pair-v6 result=(pass|fault)' | /bin/busybox tail -n 1)"
		printf 'pair6_terminal_line=%s\n' "$pair6"
		printf 'pair7_terminal_line=%s\n' "$pair7"
		printf 'cpu_online_at_terminal=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
		printf 'pair_trace_begin\n'
		/bin/busybox dmesg | /bin/busybox grep -E 'gemini-a72-pair-v[67]'
		printf 'pair_trace_end\n'
		printf '__A72_SCHEDULER_LIVE_TERMINAL_CAPTURED__\n'
		while :; do /bin/busybox sleep 1; done
	fi
	i=$((i + 1))
	/bin/busybox sleep 1
done
printf 'pair7_terminal_marker=absent\n'
printf 'pair_trace_begin\n'
/bin/busybox dmesg | /bin/busybox grep -E 'gemini-a72-pair-v[67]'
printf 'pair_trace_end\n'
exit 93
DEVICE

interface=
for ((attempt = 0; attempt < 300; attempt++)); do
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		mac="$(ifconfig "$candidate" 2>/dev/null | awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		if [[ "$mac" == "$HOST_MAC" ]]; then interface=$candidate; break 2; fi
	done
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear within 300 seconds'
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {found++} END {exit found != 1}' ||
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini USB interface'

{
	printf '__A72_SCHEDULER_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$HOST_MAC" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' "$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface"
	printf 'device_storage_reads=none\ndevice_storage_writes=none\n'
	printf 'cpu_online_writes=none\nreboot_request=none\nruntime_stimulus=none\n'
	printf '__A72_SCHEDULER_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 "$DEVICE_ADDRESS" "$DEVICE_PORT" \
	<"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
grep -Eq 'pair6_terminal_line=.*gemini-a72-pair-v6 result=(pass|fault) ' "$output" ||
	die 'complete pair-v6 terminal was not captured'
grep -Eq 'pair7_terminal_line=.*gemini-a72-pair-v7 result=(pass|fault) parent_pass=[01] sc_reported=-?[0-9]+ sc_iterations=262144 sc_rescheds=64 sc_expected8=-?[0-9]+ sc_start8=-?[0-9]+ sc_end8=-?[0-9]+ sc_expected9=-?[0-9]+ sc_start9=-?[0-9]+ sc_end9=-?[0-9]+ sc_task8=-?[0-9]+ sc_task9=-?[0-9]+ sc_create8=-?[0-9]+ sc_create9=-?[0-9]+ sc_wake8=-?[0-9]+ sc_wake9=-?[0-9]+ sc_wait8=-?[0-9]+ sc_wait9=-?[0-9]+ sc_error8=-?[0-9]+ sc_error9=-?[0-9]+ sc_stop8=-?[0-9]+ sc_stop9=-?[0-9]+ sc_done8=[0-9]+ sc_done9=[0-9]+ sc_ready=[0-9]+ sc_finished=[0-9]+ sc_hash8=[0-9a-f]{16} sc_hash9=[0-9a-f]{16}$' "$output" ||
	die 'captured pair-v7 terminal is malformed'
grep -Fxq '__A72_SCHEDULER_LIVE_TERMINAL_CAPTURED__' "$output" ||
	die 'terminal capture terminator is absent'
printf 'validation=a72-scheduler-live-outcome-pass\ncapture=%s\n' "$output"
