#!/usr/bin/env bash

# Reconstruct stage 22 and capture stage 23 once over the exact USB netcat
# shell. All executable helpers live only in initramfs /run and are removed.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:84:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly INSTALLED_FULL_SHA256=0c31f1c73bcd7f61d6b10010e17bd4de3bcc05ab6239130cab5d7fa2d26e139d
readonly PREDECESSOR_SOURCE_SHA256=e3ca6cc1e7d3de31afe7f15e0bd95b97e37a5eabc8e0df916721851b72ca8373
readonly PREDECESSOR_CHECK_SHA256=49fbce4a6745575e2eec6e1ddbb58c040ed6320988722e08ac5f555a8156805c
readonly RUNTIME_CHECK_SHA256=d2319f6cdd1288015e4886546746e77055ca6152811da73e68f4c3498bff3e23
readonly BOUNDED_LISTENER_SHA256=056618b3a508fa49e1d171e1667dbd6db22466fc408e6effb0f90fa099c84a21
readonly SINGLE_LISTENER_SHA256=08f0afeb04b43c049418df420e6a136a14aea1d9ee9026b8ffaffdde6a56502f
readonly LISTENER_SHA256=6ca94f0197026b43ba651cc15f2b2b6eb9cc5c328781cd0fb68e04669fb292e2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --bounded-listener FILE --single-listener FILE --listener FILE --output NEW_RUNTIME_TXT\n' "$0" >&2
}

interface=
bounded_listener=
single_listener=
listener=
output=
while (($#)); do
	case "$1" in
	--interface|--bounded-listener|--single-listener|--listener|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) interface=$2 ;;
		--bounded-listener) bounded_listener=$2 ;;
		--single-listener) single_listener=$2 ;;
		--listener) listener=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$bounded_listener" && -n "$single_listener" && -n "$listener" && -n "$output" ]] || { usage; exit 2; }
for command in awk base64 chmod dirname git grep ifconfig mkdir mktemp nc perl ping rm route shasum stat tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
predecessor_source="$repo_root/experiments/2026-08-01-da921x-uevent-single-multicast/scripts/run-serviceability-check.sh"
runtime_check="$script_dir/run-serviceability-check.sh"
[[ "$(shasum -a 256 "$predecessor_source" | awk '{print $1}')" == "$PREDECESSOR_SOURCE_SHA256" ]] || die 'predecessor checker changed'
[[ "$(shasum -a 256 "$runtime_check" | awk '{print $1}')" == "$RUNTIME_CHECK_SHA256" ]] || die 'runtime checker changed'
for specification in "$BOUNDED_LISTENER_SHA256:$bounded_listener" "$SINGLE_LISTENER_SHA256:$single_listener" "$LISTENER_SHA256:$listener"; do
	expected=${specification%%:*}; file=${specification#*:}
	[[ -f "$file" && ! -L "$file" && "$(shasum -a 256 "$file" | awk '{print $1}')" == "$expected" ]] || die "helper changed: $file"
done

private_root="$repo_root/artifacts/runtime-captures"
file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" && "$(basename -- "$capture_dir")" == da921x-untag-attempt-* && "$(basename -- "$output")" == runtime.txt ]] || die 'output must be runtime.txt in one new da921x-untag-attempt-* private child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] || die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" || die 'capture directory is not ignored by Git'
mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"

mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {found++} END {exit found != 1}' || die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini USB interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || die 'bounded exact-USB ping failed'

predecessor_check="$(mktemp "${TMPDIR:-/tmp}/.untag-predecessor.XXXXXXXX")"
command_file="$(mktemp "${TMPDIR:-/tmp}/.untag-runtime.XXXXXXXX")"
cleanup() { rm -f -- "${predecessor_check:-}" "${command_file:-}"; }
trap cleanup EXIT
perl -pe 's/7\.1\.3-gemini-da921x-mcast1/7.1.3-gemini-da921x-untag/g' "$predecessor_source" >"$predecessor_check"
[[ "$(shasum -a 256 "$predecessor_check" | awk '{print $1}')" == "$PREDECESSOR_CHECK_SHA256" ]] || die 'derived predecessor checker identity mismatch'
chmod 0600 "$predecessor_check" "$command_file"
printf '%s\n' 'umask 077' >"$command_file"

emit_file()
{
	local source_file=$1 device_file=$2 encoded chunk
	encoded="$(base64 <"$source_file" | tr -d '\n')"
	[[ "$encoded" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'base64 encoding malformed'
	printf ": >'%s.b64' || exit 87\n" "$device_file" >>"$command_file"
	while [[ -n "$encoded" ]]; do
		chunk=${encoded:0:1024}; encoded=${encoded:1024}
		printf "printf '%%s' '%s' >>'%s.b64' || exit 88\n" "$chunk" "$device_file" >>"$command_file"
	done
	printf "/bin/busybox base64 -d <'%s.b64' >'%s' || exit 89\n/bin/busybox rm -f -- '%s.b64'\n" "$device_file" "$device_file" "$device_file" >>"$command_file"
}

device_predecessor=/run/.gemini-untag-predecessor-check
device_check=/run/.gemini-untag-runtime-check
device_bounded=/run/.gemini-bounded-listener
device_single=/run/.gemini-single-multicast-listener
device_listener=/run/.gemini-untagged-dispatch-listener
emit_file "$predecessor_check" "$device_predecessor"
emit_file "$runtime_check" "$device_check"
emit_file "$bounded_listener" "$device_bounded"
emit_file "$single_listener" "$device_single"
emit_file "$listener" "$device_listener"
{
	printf "/bin/busybox chmod 0700 '%s' '%s' '%s' '%s' '%s' || exit 90\n" "$device_predecessor" "$device_check" "$device_bounded" "$device_single" "$device_listener"
	printf "printf '__UNTAG_IDENTITY_BEGIN__\\n'\n"
	printf "printf 'installed_full_sha256=%%s\\n' '%s'\n" "$INSTALLED_FULL_SHA256"
	printf "printf 'predecessor_check_sha256=%%s\\n' '%s'\n" "$PREDECESSOR_CHECK_SHA256"
	printf "printf 'runtime_check_sha256=%%s\\n' '%s'\n" "$RUNTIME_CHECK_SHA256"
	printf "printf 'listener_sha256=%%s\\n' '%s'\n" "$LISTENER_SHA256"
	printf "printf 'kernel_release=%%s\\n' \"\$(/bin/busybox uname -r)\"\n"
	printf "printf 'boot_id=%%s\\n' \"\$(/bin/busybox cat /proc/sys/kernel/random/boot_id)\"\n"
	printf "printf 'storage_access=none\\nreboot_request=none\\n__UNTAG_IDENTITY_END__\\n'\n"
	printf "'%s'\npredecessor_status=\$?\n" "$device_predecessor"
	printf "[ \"\$predecessor_status\" -eq 0 ] && '%s'\ncheck_status=\$?\n" "$device_check"
	printf "/bin/busybox rm -f -- '%s' '%s' '%s' '%s' '%s'\n" "$device_predecessor" "$device_check" "$device_bounded" "$device_single" "$device_listener"
	printf "printf 'predecessor_check_exit=%%s\\nruntime_check_exit=%%s\\n' \"\$predecessor_status\" \"\$check_status\"\n"
	# shellcheck disable=SC2016 # Emit deferred device-side expansion literally.
	printf 'exit "$check_status"\n'
} >>"$command_file"

{
	printf '__UNTAG_HOST_BEGIN__\ninterface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$mac" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\ninstalled_full_sha256=%s\n' "$DEVICE_ADDRESS" "$DEVICE_PORT" "$route_interface" "$INSTALLED_FULL_SHA256"
	printf 'device_partition_reads=none\ndevice_storage_writes=none\ninitramfs_run_write=five-helpers-only-removed-after-execution\nvirtual_sysfs_mount=temporary-rw-restored-ro\n__UNTAG_HOST_END__\n'
} >"$output"
chmod 0600 "$output"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 240 "$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"
grep -Eq '^(GEMINI-AC-USB# )*uevent_single_multicast_result=PASS\r?$' "$output" || die 'stage-22 predecessor did not pass'
grep -Eq '^(GEMINI-AC-USB# )*uevent_untagged_dispatch_result=PASS\r?$' "$output" || die 'stage-23 discriminator did not pass'
grep -Eq '^(GEMINI-AC-USB# )*runtime_check_exit=0\r?$' "$output" || die 'runtime check did not exit successfully'
printf 'validation=da921x-uevent-untagged-dispatch-runtime\ncapture=%s\ninstalled_full_sha256=%s\nlistener_sha256=%s\nstorage_access=none\nreboot_request=none\n' "$output" "$INSTALLED_FULL_SHA256" "$LISTENER_SHA256"
