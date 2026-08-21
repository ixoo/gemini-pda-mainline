#!/usr/bin/env bash

# Pre-arm one bounded USB/netcat observation of the exact serviceability
# control. Only after full classification passes, request one native reboot and
# confirm a changed-ID Gemian return.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly WAIT_SECONDS=900
readonly RETURN_SECONDS=600
readonly CANDIDATE_SHA256=7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3
readonly PROBE_SHA256=120bc5c9d0b0b6588260c311f092b654b5c501dad74c5495ab8ed78c1a189837
readonly VALIDATOR_SHA256=dda8ed943e27996f767f50899a5c5e56334d9f8d04ea8659563a8ac637631e7d

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/current-tree-service-control-attempt-1\n' "$0" >&2
}

deployment_boot_id=
output=
while (($#)); do
	case "$1" in
	--deployment-boot-id)
		(($# >= 2)) || die '--deployment-boot-id requires a value'
		[[ -z "$deployment_boot_id" ]] || die 'duplicate --deployment-boot-id'
		deployment_boot_id=$2
		shift 2
		;;
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
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
	die 'deployment boot ID is missing or malformed'
[[ -n "$output" ]] || { usage; exit 2; }

for command in awk base64 basename chmod date dirname git grep ifconfig ioreg mkdir \
	mktemp nc python3 rm route sha256sum sleep ssh tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
probe="$script_dir/remote-runtime-probe.sh"
validator="$script_dir/validate-runtime.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"
for input in "$probe" "$validator" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "input is missing or unsafe: $input"
done
[[ "$(sha256sum "$probe" | awk '{print $1}')" == "$PROBE_SHA256" ]] || die 'probe changed'
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] ||
	die 'validator changed'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" &&
	"$(basename -- "$output")" == current-tree-service-control-attempt-1 ]] ||
	die 'output must be the exact private attempt-1 child'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

mkdir -m 0700 "$output"
events="$output/observer-events.txt"
runtime="$output/runtime.txt"
classification="$output/classification.txt"
usb_topology="$output/usb-topology.txt"
printf 'observer=armed\ncandidate_sha256=%s\n' "$CANDIDATE_SHA256" >"$events"
printf 'armed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"

usb_snapshot() {
	ioreg -p IOUSB -l -w 0 | awk '/"idVendor"|"idProduct"|"USB Product Name"/'
}
baseline_snapshot="$(usb_snapshot)"
baseline_usb="$(printf '%s\n' "$baseline_snapshot" | sha256sum | awk '{print $1}')"
{
	printf 'snapshot=baseline utc=%s sha256=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$baseline_usb"
	printf '%s\n' "$baseline_snapshot"
} >"$usb_topology"
printf 'baseline_usb_topology_sha256=%s\n' "$baseline_usb" >>"$events"

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -i "$identity"
)
last_usb=$baseline_usb
record_usb_change() {
	local snapshot current change_utc
	snapshot="$(usb_snapshot)"
	current="$(printf '%s\n' "$snapshot" | sha256sum | awk '{print $1}')"
	if [[ "$current" != "$last_usb" ]]; then
		change_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
		printf 'usb_topology_change_utc=%s sha256=%s\n' "$change_utc" "$current" >>"$events"
		{
			printf 'snapshot=change utc=%s sha256=%s\n' "$change_utc" "$current"
			printf '%s\n' "$snapshot"
		} >>"$usb_topology"
		last_usb=$current
	fi
}

interface=
mac=
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
	record_usb_change
	# shellcheck disable=SC2046 # macOS ifconfig -l is space-separated.
	for candidate in $(ifconfig -l); do
		candidate_mac="$(ifconfig "$candidate" 2>/dev/null |
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		case "$candidate_mac" in
		42:00:15:19:82:00|42:00:15:19:84:00) ;;
		*) continue ;;
		esac
		if ! ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address {found++} END {exit found != 1}'; then
			continue
		fi
		route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null |
			awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')" || true
		[[ "$route_interface" == "$candidate" ]] || continue
		interface=$candidate
		mac=$candidate_mac
		break 2
	done
	if (( attempt % 5 == 0 )); then
		# shellcheck disable=SC2016 # Command substitutions are evaluated remotely.
		gemian="$("${ssh_command[@]}" gemini@"$GEMIAN_ADDRESS" \
			'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' \
			2>/dev/null || true)"
		if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ &&
			"${BASH_REMATCH[1]}" != "$deployment_boot_id" ]]; then
			printf 'classification=no-mainline-network-before-changed-Gemian-return\n' >>"$events"
			(cd "$output" && sha256sum observer-events.txt usb-topology.txt >SHA256SUMS)
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not become ready before timeout'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"

command_file="$(mktemp "${TMPDIR:-/tmp}/.gemini-current-service.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT HUP INT TERM
payload="$(base64 <"$probe" | tr -d '\n')"
[[ "$payload" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'probe payload is malformed'
printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
	"$payload" >"$command_file"
chmod 0600 "$command_file"
: >"$runtime"
chmod 0600 "$runtime"
probe_complete=false
for try in {1..6}; do
	printf 'netcat_try=%s utc=%s\n' "$try" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
	set +e
	nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$runtime" 2>&1
	status=$?
	set -e
	if grep -Fq __CURRENT_SERVICE_CONTROL_RUNTIME_BEGIN__ "$runtime" &&
		grep -Fq __CURRENT_SERVICE_CONTROL_RUNTIME_END__ "$runtime"; then
		printf 'netcat_complete=runtime.txt status=%s\n' "$status" >>"$events"
		probe_complete=true
		break
	fi
	sleep 5
done
[[ "$probe_complete" == true ]] || die 'exact interface appeared but runtime probe did not complete'
python3 "$validator" "$runtime" >"$classification"
grep -Fqx 'runtime_classification=serviceable-control-pass' "$classification" ||
	die 'runtime did not classify as the exact serviceability pass'

printf '/bin/reboot\n' >"$command_file"
printf 'native_reboot_command_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 10 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >/dev/null 2>&1
reboot_status=$?
set -e
printf 'native_reboot_netcat_status=%s\nnative_reboot_command_sent=yes\n' \
	"$reboot_status" >>"$events"
printf 'native_reboot_command_sent=yes\n' >>"$classification"

returned=false
for ((attempt = 0; attempt < RETURN_SECONDS; attempt++)); do
	record_usb_change
	if (( attempt % 3 == 0 )); then
		# shellcheck disable=SC2016 # Command substitutions are evaluated remotely.
		gemian="$("${ssh_command[@]}" gemini@"$GEMIAN_ADDRESS" \
			'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' \
			2>/dev/null || true)"
		if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ &&
			"${BASH_REMATCH[1]}" != "$deployment_boot_id" ]]; then
			printf 'changed_gemian_return_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
			printf 'returned_boot_id_sha256=%s\n' \
				"$(printf '%s' "${BASH_REMATCH[1]}" | sha256sum | awk '{print $1}')" >>"$events"
			printf 'native_reboot_to_changed_gemian=passed\n' >>"$classification"
			returned=true
			break
		fi
	fi
	sleep 1
done
[[ "$returned" == true ]] || die 'changed Gemian return was not observed after native reboot request'

(
	cd "$output"
	sha256sum classification.txt observer-events.txt runtime.txt usb-topology.txt >SHA256SUMS
)
chmod 0600 "$output"/*
cleanup
trap - EXIT HUP INT TERM
printf 'runtime_classification=serviceable-control-pass\n'
printf 'cpu_online=0-7\ncpu_offline=8-9\nDA921x_register_data_writes=0\n'
printf 'native_reboot_to_changed_gemian=passed\ncapture=%s\n' "$output"
