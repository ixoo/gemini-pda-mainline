#!/usr/bin/env bash

# Candidate AI's initramfs intentionally retains Candidate AC's inherited USB
# banner.  This collector therefore combines the caller-attested exact boot2
# readback with read-only live kernel/configuration/DT evidence.  It never
# reads a device partition and never requests a CPU state transition.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly INSTALLED_FULL_SHA256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
readonly VALIDATOR_SHA256=a1ca2a1a7a33eda0f9f52bbee8d964f3ed3004566183792f2eb4f446cffb1e38

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output NEW_FILE --installed-full-sha256 SHA256\n' "$0" >&2
}

interface=
output=
installed_full_sha256=
while (($#)); do
	case "$1" in
	--interface|--output|--installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) interface=$2 ;;
		--output) output=$2 ;;
		--installed-full-sha256) installed_full_sha256=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || { usage; exit 2; }
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'installed full-partition checksum must be one lowercase SHA-256 value'
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die 'installed full-partition checksum is not Candidate AI'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
for command in awk basename cat chmod dirname git grep ifconfig mktemp nc ping \
	python3 rm route shasum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
validator="$script_dir/validate-runtime.py"
[[ -f "$validator" && ! -L "$validator" ]] || die 'AI runtime validator is absent or unsafe'
[[ "$(shasum -a 256 "$validator" | awk '{ print $1 }')" == "$VALIDATOR_SHA256" ]] || \
	die 'AI runtime validator source identity changed'
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || \
	die 'private runtime-capture root is absent or unsafe; use collect-cycle.sh'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$(stat -f '%Lp' "$private_root" 2>/dev/null || stat -c '%a' "$private_root")" == 700 ]] || \
	die 'private runtime-capture root mode is not 0700'

case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || \
	die '--output must be inside one direct child of artifacts/runtime-captures/'
[[ "$(basename -- "$output")" == runtime.txt ]] || \
	die '--output filename must be runtime.txt'
[[ -d "$capture_dir" && ! -L "$capture_dir" ]] || die 'runtime-capture directory is unsafe'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || \
	die 'canonical runtime-capture directory escaped its private root'
[[ "$(stat -f '%Lp' "$capture_dir" 2>/dev/null || stat -c '%a' "$capture_dir")" == 700 ]] || \
	die 'runtime-capture directory mode is not 0700'
output="$capture_dir/runtime.txt"
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
git -C "$repo_root" check-ignore -q -- "$output" || \
	die 'runtime capture is not covered by repository ignore rules'

mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found = 1 } END { exit !found }' || \
	die 'host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-ai-runtime-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
uptime_seconds=$(/bin/busybox cut -d. -f1 /proc/uptime)
case "$uptime_seconds" in
''|*[!0-9]*) exit 91 ;;
esac
if [ "$uptime_seconds" -lt 45 ]; then
	/bin/busybox sleep $((45 - uptime_seconds))
fi

online_control_state() {
	if [ -e "/sys/devices/system/cpu/cpu$1/online" ]; then
		printf 'present'
	else
		printf 'absent'
	fi
}

printf '__AI_IDENTITY_BEGIN__\n'
printf 'cmdline='; /bin/busybox cat /proc/cmdline
printf 'possible='; /bin/busybox cat /sys/devices/system/cpu/possible
printf 'present='; /bin/busybox cat /sys/devices/system/cpu/present
printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
printf 'nproc='; /bin/busybox nproc
printf 'kernel='; /bin/busybox uname -r
printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_before='; /bin/busybox cut -d' ' -f1 /proc/uptime
printf 'config_sha256='; /bin/busybox zcat /proc/config.gz | /bin/busybox sha256sum | /bin/busybox awk '{ print $1 }'
printf 'cpu8_enable_method='; /bin/busybox tr -d '\000' </proc/device-tree/cpus/cpu@200/enable-method; printf '\n'
printf 'cpu9_enable_method='; /bin/busybox tr -d '\000' </proc/device-tree/cpus/cpu@201/enable-method; printf '\n'
printf 'boot_gate_symbol_count='; /bin/busybox grep -c ' mt6797_psci_cpu_boot$' /proc/kallsyms
printf 'disable_gate_symbol_count='; /bin/busybox grep -c ' mt6797_psci_cpu_can_disable$' /proc/kallsyms
printf 'ops_symbol_count='; /bin/busybox grep -c ' mt6797_psci_ops$' /proc/kallsyms
printf 'cpu8_online_control='; online_control_state 8; printf '\n'
printf 'cpu9_online_control='; online_control_state 9; printf '\n'
printf '__AI_IDENTITY_END__\n'
printf '__AI_STAT1_BEGIN__\n'; /bin/busybox grep '^cpu[0-9]' /proc/stat; printf '__AI_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AI_STAT2_BEGIN__\n'; /bin/busybox grep '^cpu[0-9]' /proc/stat; printf '__AI_STAT2_END__\n'
printf '__AI_STABILITY_BEGIN__\n'
printf 'boot_id_after='; /bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_after='; /bin/busybox cut -d' ' -f1 /proc/uptime
printf 'online_after='; /bin/busybox cat /sys/devices/system/cpu/online
printf 'offline_after='; /bin/busybox cat /sys/devices/system/cpu/offline
printf 'cpu8_online_control_after='; online_control_state 8; printf '\n'
printf 'cpu9_online_control_after='; online_control_state 9; printf '\n'
printf '__AI_STABILITY_END__\n'
printf '__AI_DMESG_BEGIN__\n'; /bin/busybox dmesg; printf '__AI_DMESG_END__\n'
exit
EOF

{
	printf '__AI_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'installed_full_hash_reverified_during_collection=no\n'
	printf 'device_partition_read_during_collection=no\n'
	printf 'interface=%s\n' "$interface"
	printf 'mac=%s\n' "$mac"
	printf 'host_address=%s/24\n' "$HOST_ADDRESS"
	printf 'route_interface=%s\n' "$route_interface"
	printf 'device_endpoint=%s:%s\n' "$DEVICE_ADDRESS" "$DEVICE_PORT"
	printf '__AI_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output"
python3 "$validator" --capture "$output" \
	--expected-installed-full-sha256 "$installed_full_sha256"
printf 'capture=%s\n' "$output"
