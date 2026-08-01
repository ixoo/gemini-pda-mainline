#!/usr/bin/env bash

# Capture the exact single-multicast discriminator once over the established
# direct USB netcat shell. All helpers are staged only in initramfs /run.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly INSTALLED_FULL_SHA256=b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274
readonly RUNTIME_CHECK_SHA256=e3ca6cc1e7d3de31afe7f15e0bd95b97e37a5eabc8e0df916721851b72ca8373
readonly PREDECESSOR_LISTENER_SHA256=056618b3a508fa49e1d171e1667dbd6db22466fc408e6effb0f90fa099c84a21
readonly LISTENER_SHA256=08f0afeb04b43c049418df420e6a136a14aea1d9ee9026b8ffaffdde6a56502f

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --predecessor-listener FILE --listener FILE --output NEW_RUNTIME_TXT\n' \
		"$0" >&2
}

interface=
predecessor_listener=
listener=
output=
while (($#)); do
	case "$1" in
	--interface|--predecessor-listener|--listener|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) [[ -z "$interface" ]] || die '--interface duplicated'; interface=$2 ;;
		--predecessor-listener) [[ -z "$predecessor_listener" ]] || die '--predecessor-listener duplicated'; predecessor_listener=$2 ;;
		--listener) [[ -z "$listener" ]] || die '--listener duplicated'; listener=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$predecessor_listener" && -n "$listener" && -n "$output" ]] ||
	{ usage; exit 2; }
[[ "$predecessor_listener" != *$'\n'* && "$listener" != *$'\n'* && "$output" != *$'\n'* ]] ||
	die 'file paths must be one line'
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
[[ -f "$listener" && ! -L "$listener" ]] || die 'listener is missing or unsafe'
[[ "$(shasum -a 256 "$listener" | awk '{print $1}')" == \
	"$LISTENER_SHA256" ]] || die 'listener changed'
[[ -f "$predecessor_listener" && ! -L "$predecessor_listener" ]] ||
	die 'predecessor listener is missing or unsafe'
[[ "$(shasum -a 256 "$predecessor_listener" | awk '{print $1}')" == \
	"$PREDECESSOR_LISTENER_SHA256" ]] || die 'predecessor listener changed'

private_root="$repo_root/artifacts/runtime-captures"
file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
[[ -d "$private_root" && ! -L "$private_root" &&
	"$(file_mode "$private_root")" == 700 ]] ||
	die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" &&
	"$(basename -- "$capture_dir")" == da921x-mcast1-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new da921x-mcast1-attempt-* private child'
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

command_file="$(mktemp "${TMPDIR:-/tmp}/.mcast1-runtime.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
chmod 0600 "$command_file"
printf '%s\n' 'umask 077' >"$command_file"

emit_file()
{
	local source_file=$1
	local device_file=$2
	local encoded_file=${device_file}.b64
	local encoded
	local chunk

	encoded="$(base64 <"$source_file" | tr -d '\n')"
	[[ "$encoded" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'base64 encoding is malformed'
	printf '%s\n' ": >'$encoded_file' || exit 87" >>"$command_file"
	while [[ -n "$encoded" ]]; do
		chunk=${encoded:0:1024}
		encoded=${encoded:1024}
		printf "printf '%%s' '%s' >>'%s' || exit 88\n" \
			"$chunk" "$encoded_file" >>"$command_file"
	done
	printf '%s\n' "/bin/busybox base64 -d <'$encoded_file' >'$device_file' || exit 89" \
		>>"$command_file"
	printf '%s\n' "/bin/busybox rm -f -- '$encoded_file'" >>"$command_file"
}

device_check=/run/.gemini-mcast1-runtime-check
device_predecessor_listener=/run/.gemini-bounded-listener
device_listener=/run/.gemini-single-multicast-listener
emit_file "$runtime_check" "$device_check"
emit_file "$predecessor_listener" "$device_predecessor_listener"
emit_file "$listener" "$device_listener"
{
	printf '%s\n' "/bin/busybox chmod 0700 '$device_check' '$device_predecessor_listener' '$device_listener' || exit 90"
	printf '%s\n' "printf '__MCAST1_IDENTITY_BEGIN__\\n'"
	printf '%s\n' "printf 'installed_full_sha256=%s\\n' '$INSTALLED_FULL_SHA256'"
	printf '%s\n' "printf 'runtime_check_sha256=%s\\n' '$RUNTIME_CHECK_SHA256'"
	printf '%s\n' "printf 'predecessor_listener_sha256=%s\\n' '$PREDECESSOR_LISTENER_SHA256'"
	printf '%s\n' "printf 'listener_sha256=%s\\n' '$LISTENER_SHA256'"
	printf '%s\n' "printf 'kernel_release=%s\\n' \"\$(/bin/busybox uname -r)\""
	printf '%s\n' "printf 'boot_id=%s\\n' \"\$(/bin/busybox cat /proc/sys/kernel/random/boot_id)\""
	printf '%s\n' "printf 'storage_access=none\\nreboot_request=none\\n'"
	printf '%s\n' "printf '__MCAST1_IDENTITY_END__\\n'"
	printf '%s\n' "'$device_check'"
	printf '%s\n' 'check_status=$?'
	printf '%s\n' "/bin/busybox rm -f -- '$device_check' '$device_predecessor_listener' '$device_listener'"
	printf '%s\n' "printf 'runtime_check_exit=%s\\n' \"\$check_status\""
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf '%s\n' 'exit "$check_status"'
} >>"$command_file"

{
	printf '__MCAST1_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' \
		"$interface" "$mac" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface"
	printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
	printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
	printf 'initramfs_run_write=runtime-check-and-two-listeners-only-removed-after-execution\n'
	printf 'virtual_sysfs_mount=temporary-rw-restored-ro\n'
	printf '__MCAST1_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 180 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
grep -Eq '^(GEMINI-AC-USB# )*uevent_single_multicast_result=PASS\r?$' "$output" ||
	die 'single-multicast discriminator did not pass'
grep -Eq '^(GEMINI-AC-USB# )*runtime_check_exit=0\r?$' "$output" ||
	die 'runtime check did not exit successfully'
grep -Eq '^(GEMINI-AC-USB# )*storage_access=none\r?$' "$output" ||
	die 'device identity record is incomplete'
printf 'validation=da921x-uevent-single-multicast-runtime\n'
printf 'capture=%s\ninstalled_full_sha256=%s\n' "$output" "$INSTALLED_FULL_SHA256"
printf 'predecessor_listener_sha256=%s\nlistener_sha256=%s\n' \
	"$PREDECESSOR_LISTENER_SHA256" "$LISTENER_SHA256"
printf 'storage_access=none\nreboot_request=none\n'
