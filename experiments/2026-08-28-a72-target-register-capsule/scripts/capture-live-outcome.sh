#!/usr/bin/env bash

# Read-only best-effort capture of target-register capsules, their exact
# scheduler parent, and adjacent pair-v6/pair-v7 terminals over USB/netcat.
# Changed-cycle pstore remains the primary evidence source.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --output artifacts/runtime-captures/a72-target-register-capsule-attempt-N/runtime.txt\n' "$0" >&2
}

output=
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires a value'
		[[ -z "$output" ]] || die 'duplicate --output'
		output=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage; exit 2; }
for command in awk basename cat chmod dirname git grep ifconfig mkdir mktemp \
	nc python3 rm route sleep; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
validator="$script_dir/validate_capture.py"
[[ -f "$validator" && ! -L "$validator" ]] ||
	die 'capsule-capture validator is absent or unsafe'
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] ||
	die 'private runtime-capture root is absent'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" &&
	"$(basename -- "$capture_dir")" == a72-target-register-capsule-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new exact private attempt child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] ||
	die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" ||
	die 'capture directory is not ignored by Git'
mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"

command_file="$(mktemp "${TMPDIR:-/tmp}/.a72-regcap-live.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
chmod 0600 "$command_file"
cat >"$command_file" <<'DEVICE'
printf '__A72_REGCAP_LIVE_BEGIN__\n'
printf 'kernel_release=%s\n' "$(/bin/busybox uname -r)"
printf 'kernel_version=%s\n' "$(/bin/busybox uname -v)"
printf 'cpu_online_initial=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
printf 'cpu_present=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/present)"
printf 'evidence_priority=changed-cycle-pstore-primary\n'
printf 'usb_capture_role=read-only-secondary\n'
i=0
phase_seen=0
snapshot_sequence=0
while [ "$i" -lt 30 ]; do
	if [ "$i" -eq 0 ]; then printf '\n'; fi
	trace="$(/bin/busybox dmesg | /bin/busybox grep -E 'gemini-a72-(pair-v[67] result=(pass|fault)|sc-phase|regcap-v1)' || true)"
	trace_lines="$(printf '%s\n' "$trace" | /bin/busybox awk 'NF { count++ } END { print count + 0 }')"
	snapshot_sequence=$((snapshot_sequence + 1))
	printf 'capsule_trace_snapshot_begin sequence=%s lines=%s\n' "$snapshot_sequence" "$trace_lines"
	if [ -n "$trace" ]; then printf '%s\n' "$trace"; fi
	printf 'capsule_trace_snapshot_end sequence=%s\n' "$snapshot_sequence"
	if printf '%s\n' "$trace" | /bin/busybox grep -q 'gemini-a72-sc-phase'; then
		phase_seen=1
	fi
	pair7="$(printf '%s\n' "$trace" | /bin/busybox grep -E 'gemini-a72-pair-v7 result=(pass|fault)' | /bin/busybox tail -n 1)"
	regcaps="$(printf '%s\n' "$trace" | /bin/busybox grep 'gemini-a72-regcap-v1' || true)"
	regcap_lines="$(printf '%s\n' "$regcaps" | /bin/busybox awk 'NF { count++ } END { print count + 0 }')"
	if [ -n "$pair7" ] && [ "$regcap_lines" -eq 8 ]; then
		pair6="$(printf '%s\n' "$trace" | /bin/busybox grep -E 'gemini-a72-pair-v6 result=(pass|fault)' | /bin/busybox tail -n 1)"
		printf 'pair6_terminal_line=%s\n' "$pair6"
		printf 'pair7_terminal_line=%s\n' "$pair7"
		printf '%s\n' "$regcaps" | /bin/busybox awk 'NF { print "regcap_terminal_line_" ++count "=" $0 }'
		printf 'cpu_online_at_terminal=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
		printf 'capsule_capture_class=terminal\n'
		printf '__A72_REGCAP_TERMINAL_CAPTURED__\n'
		while :; do /bin/busybox sleep 1; done
	fi
	i=$((i + 1))
	/bin/busybox sleep 1
done
if [ "$phase_seen" -eq 1 ]; then
	printf 'capsule_capture_class=phase-or-capsule-prefix\n'
else
	printf 'capsule_capture_class=no-phase\n'
fi
printf 'regcap_terminal_marker=absent\n'
exit 93
DEVICE

interface=
for ((attempt = 0; attempt < 300; attempt++)); do
	# shellcheck disable=SC2046
	for candidate_interface in $(ifconfig -l); do
		mac="$(ifconfig "$candidate_interface" 2>/dev/null |
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		if [[ "$mac" == "$HOST_MAC" ]]; then
			interface=$candidate_interface
			break 2
		fi
	done
	sleep 1
done
[[ -n "$interface" ]] ||
	die 'exact Gemini USB interface did not appear within 300 seconds'
ifconfig "$interface" |
	awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {found++} END {exit found != 1}' ||
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null |
	awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')"
[[ "$route_interface" == "$interface" ]] ||
	die 'device route is not the exact Gemini USB interface'

{
	printf '__A72_REGCAP_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' \
		"$interface" "$HOST_MAC" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface"
	printf 'evidence_priority=changed-cycle-pstore-primary\n'
	printf 'usb_capture_role=read-only-secondary\n'
	printf 'device_storage_reads=none\ndevice_storage_writes=none\n'
	printf 'cpu_online_writes=none\nreboot_request=none\nruntime_stimulus=none\n'
	printf '__A72_REGCAP_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
set +e
validation="$(python3 "$validator" --capture "$output" 2>&1)"
validation_status=$?
set -e
printf '%s\n' "$validation" >>"$output"
[[ "$validation_status" -eq 0 ]] ||
	die 'captured capsule trace failed structural validation'
if grep -Fxq '__A72_REGCAP_TERMINAL_CAPTURED__' "$output"; then
	grep -Fxq 'capture_class=terminal' <<<"$validation" ||
		die 'terminal marker lacks an exact terminal classification'
	printf 'validation=a72-target-register-capsule-terminal-capture-pass\n'
	printf 'capture=%s\n' "$output"
	exit 0
fi
grep -Eq '^capture_class=(valid-prefix|capsule-prefix|transport-truncated-valid-snapshot)$' \
	<<<"$validation" || die 'capsule validator returned an unknown capture class'
printf 'validation=a72-target-register-capsule-prefix-preserved\n'
printf 'capture=%s\n' "$output"
