#!/usr/bin/env bash

# Capture the exact read-only discriminator once over the established direct
# USB netcat shell. The device-side helper is staged only in initramfs /tmp.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly INSTALLED_FULL_SHA256=5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3
readonly RUNTIME_CHECK_SHA256=d4fae94c17bdcd901c6c269b778a1ccd6cbdde37ff646bc503fcf0bef3254bc9

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output NEW_RUNTIME_TXT\n' "$0" >&2
}

interface=
output=
while (($#)); do
	case "$1" in
	--interface|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) [[ -z "$interface" ]] || die '--interface duplicated'; interface=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] ||
	{ usage; exit 2; }
[[ "$output" != *$'\n'* ]] || die 'output path must be one line'
for command in awk base64 chmod dirname git grep ifconfig mkdir mktemp nc ping \
	rm route shasum stat tr; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
runtime_check="$script_dir/run-serviceability-check.sh"
[[ -f "$runtime_check" && ! -L "$runtime_check" ]] ||
	die 'runtime check is missing or unsafe'
[[ "$(shasum -a 256 "$runtime_check" | awk '{print $1}')" == \
	"$RUNTIME_CHECK_SHA256" ]] || die 'runtime check changed'

private_root="$repo_root/artifacts/runtime-captures"
file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
[[ -d "$private_root" && ! -L "$private_root" &&
	"$(file_mode "$private_root")" == 700 ]] ||
	die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" &&
	"$(basename -- "$capture_dir")" == da921x-dualstate-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new da921x-dualstate-attempt-* private child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] ||
	die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" ||
	die 'capture directory is not ignored by Git'
mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"

mac="$(ifconfig "$interface" |
	awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')"
[[ "$mac" == "$HOST_MAC" ]] ||
	die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address {found++} END {exit found != 1}' ||
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null |
	awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')"
[[ "$route_interface" == "$interface" ]] ||
	die 'device route is not the exact Gemini USB interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null ||
	die 'bounded exact-USB ping failed'

command_file="$(mktemp "${TMPDIR:-/tmp}/.dualstate-runtime.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
runtime_check_b64="$(base64 <"$runtime_check" | tr -d '\n')"
[[ "$runtime_check_b64" =~ ^[A-Za-z0-9+/]+=*$ ]] ||
	die 'runtime check base64 encoding is malformed'
{
	printf '%s\n' 'umask 077'
	printf '%s\n' 'check=/tmp/.gemini-dualstate-runtime-check'
	printf '%s\n' \
		"printf '%s' '$runtime_check_b64' | /bin/busybox base64 -d >\"\$check\" || exit 89"
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf '%s\n' '/bin/busybox chmod 0700 "$check" || exit 90'
	printf '%s\n' "printf '__DUALSTATE_IDENTITY_BEGIN__\\n'"
	printf '%s\n' "printf 'installed_full_sha256=%s\\n' '$INSTALLED_FULL_SHA256'"
	printf '%s\n' "printf 'runtime_check_sha256=%s\\n' '$RUNTIME_CHECK_SHA256'"
	printf '%s\n' "printf 'kernel_release=%s\\n' \"\$(/bin/busybox uname -r)\""
	printf '%s\n' "printf 'boot_id=%s\\n' \"\$(/bin/busybox cat /proc/sys/kernel/random/boot_id)\""
	printf '%s\n' "printf 'storage_access=none\\nreboot_request=none\\n'"
	printf '%s\n' "printf '__DUALSTATE_IDENTITY_END__\\n'"
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf '%s\n' '"$check"'
	printf '%s\n' 'check_status=$?'
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf '%s\n' '/bin/busybox rm -f -- "$check"'
	printf '%s\n' "printf 'runtime_check_exit=%s\\n' \"\$check_status\""
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf '%s\n' 'exit "$check_status"'
} >"$command_file"
chmod 0600 "$command_file"

{
	printf '__DUALSTATE_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' \
		"$interface" "$mac" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface"
	printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
	printf 'device_partition_reads=none\ndevice_write_operations=none\n'
	printf '__DUALSTATE_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 60 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
grep -Eq '^(GEMINI-AC-USB# )*dual_modalias_state_result=PASS\r?$' "$output" ||
	die 'read-only discriminator did not pass'
grep -Eq '^(GEMINI-AC-USB# )*runtime_check_exit=0\r?$' "$output" ||
	die 'runtime check did not exit successfully'
grep -Eq '^(GEMINI-AC-USB# )*storage_access=none\r?$' "$output" ||
	die 'device identity record is incomplete'
printf 'validation=da921x-dual-modalias-state-runtime\n'
printf 'capture=%s\ninstalled_full_sha256=%s\n' "$output" "$INSTALLED_FULL_SHA256"
printf 'storage_access=none\nreboot_request=none\n'
