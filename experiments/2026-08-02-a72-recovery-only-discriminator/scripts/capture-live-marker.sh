#!/usr/bin/env bash

# Capture the recovery-only marker from the exact direct USB/netcat shell.
# This is a read-only, one-session observation; all output remains ignored.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly MARKER='gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden'

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --output artifacts/runtime-captures/a72-recovery-live-attempt-N/runtime.txt\n' "$0" >&2; }

output=
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires a value'
		output=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage; exit 2; }
for command in awk basename cat chmod dirname git grep ifconfig mkdir mktemp nc rm route sleep; do
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
	"$(basename -- "$capture_dir")" == a72-recovery-live-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new a72-recovery-live-attempt-* private child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] || die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" || die 'capture directory is not ignored by Git'
mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"

command_file="$(mktemp "${TMPDIR:-/tmp}/.a72-recovery-live.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
chmod 0600 "$command_file"
cat >"$command_file" <<'DEVICE'
printf '__A72_RECOVERY_LIVE_BEGIN__\n'
printf 'kernel_release=%s\n' "$(/bin/busybox uname -r)"
printf 'cpu_online=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
printf 'cpu_present=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/present)"
i=0
while [ "$i" -lt 30 ]; do
	line="$(/bin/busybox dmesg | /bin/busybox grep -F 'gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden' | /bin/busybox tail -n 1)"
	if [ -n "$line" ]; then
		printf 'exact_armed_marker=present\n'
		printf 'armed_line=%s\n' "$line"
		printf 'cpu_online_after_arm=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online)"
		printf '__A72_RECOVERY_LIVE_MARKER_CAPTURED__\n'
		while :; do /bin/busybox sleep 1; done
	fi
	i=$((i + 1))
	/bin/busybox sleep 1
done
printf 'exact_armed_marker=absent\n'
exit 93
DEVICE

interface=
for ((attempt = 0; attempt < 300; attempt++)); do
	# ifconfig -l emits a space-separated interface-name inventory.
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		mac="$(ifconfig "$candidate" 2>/dev/null | awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		if [[ "$mac" == "$HOST_MAC" ]]; then
			interface=$candidate
			break 2
		fi
	done
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear within 300 seconds'
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {found++} END {exit found != 1}' ||
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini USB interface'

{
	printf '__A72_RECOVERY_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$HOST_MAC" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' "$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface"
	printf 'device_storage_reads=none\ndevice_storage_writes=none\nreboot_request=none\n'
	printf '__A72_RECOVERY_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 "$DEVICE_ADDRESS" "$DEVICE_PORT" \
	<"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
grep -Fxq 'exact_armed_marker=present' "$output" || die 'exact armed marker was not captured'
grep -Fq "$MARKER" "$output" || die 'captured marker text is not exact'
grep -Fxq '__A72_RECOVERY_LIVE_MARKER_CAPTURED__' "$output" || die 'marker capture terminator is absent'
printf 'validation=a72-recovery-live-marker-pass\ncapture=%s\n' "$output"
