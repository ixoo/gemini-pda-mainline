#!/usr/bin/env bash

# Pre-arm host USB/netcat observation for the one current-DT repair attempt.
# Raw captures stay below ignored artifacts/. Device probes are read-only.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly DEPLOYMENT_BOOT_ID=39c18b20-1b73-474a-835e-c99e1e6adc45
readonly WAIT_SECONDS=900
readonly LIVE_PROBE_SHA256=4dbb62376fd8b38b57287f411b9f82c596fb8462b229fb073a06f58e5598ffcb
readonly SERVICE_PROBE_SHA256=f363fc6fbea44d3e121e4ce632944cd425815909731c44a219d3d637ac7cb92d
readonly CANDIDATE_SHA256=fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --output artifacts/runtime-captures/current-dtb-usb-observation-attempt-1\n' "$0" >&2
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

for command in awk base64 basename chmod date dirname git grep ifconfig ioreg \
	mkdir mktemp nc rm route sha256sum sleep ssh tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
live_probe="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/remote-live-identity-probe.sh"
service_probe="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/remote-service-probe.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"

[[ -f "$live_probe" && ! -L "$live_probe" && -f "$service_probe" && ! -L "$service_probe" ]] ||
	die 'source probes are missing or unsafe'
[[ "$(sha256sum "$live_probe" | awk '{print $1}')" == "$LIVE_PROBE_SHA256" ]] ||
	die 'live probe identity changed'
[[ "$(sha256sum "$service_probe" | awk '{print $1}')" == "$SERVICE_PROBE_SHA256" ]] ||
	die 'service probe identity changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini SSH identity is missing or unsafe'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" &&
	"$(basename -- "$output")" == current-dtb-usb-observation-attempt-1 ]] ||
	die 'output must be the exact private attempt-1 child'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

mkdir -m 0700 "$output"
events="$output/observer-events.txt"
runtime="$output/runtime.txt"
service="$output/service.txt"
printf 'observer=armed\ncandidate_sha256=%s\n' "$CANDIDATE_SHA256" >"$events"
printf 'armed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
baseline_usb="$(ioreg -p IOUSB -l -w 0 |
	awk '/"idVendor"|"idProduct"|"USB Product Name"/' |
	sha256sum | awk '{print $1}')"
printf 'baseline_usb_topology_sha256=%s\n' "$baseline_usb" >>"$events"

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -i "$identity"
)

interface=
mac=
last_usb=$baseline_usb
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
	current_usb="$(ioreg -p IOUSB -l -w 0 |
		awk '/"idVendor"|"idProduct"|"USB Product Name"/' |
		sha256sum | awk '{print $1}')"
	if [[ "$current_usb" != "$last_usb" ]]; then
		printf 'usb_topology_change_utc=%s sha256=%s\n' \
			"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$current_usb" >>"$events"
		last_usb=$current_usb
	fi

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
			"${BASH_REMATCH[1]}" != "$DEPLOYMENT_BOOT_ID" ]]; then
			{
				printf 'changed_gemian_return_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
				printf 'returned_boot_id_sha256=%s\n' \
					"$(printf '%s' "${BASH_REMATCH[1]}" | sha256sum | awk '{print $1}')"
				printf 'classification=no-mainline-network-before-changed-Gemian-return\n'
			} >>"$events"
			(cd "$output" && sha256sum observer-events.txt >SHA256SUMS)
			printf 'runtime_classification=no-mainline-network-before-changed-Gemian-return\n'
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || {
	printf 'classification=no-exact-interface-before-timeout\n' >>"$events"
	(cd "$output" && sha256sum observer-events.txt >SHA256SUMS)
	die 'exact Gemini USB interface did not become ready before timeout'
}

printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"

command_file="$(mktemp "${TMPDIR:-/tmp}/.gemini-usb-observation.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT HUP INT TERM

run_probe() {
	local probe=$1 destination=$2 begin=$3 end=$4 payload status
	payload="$(base64 <"$probe" | tr -d '\n')"
	[[ "$payload" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'probe payload is malformed'
	printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
		"$payload" >"$command_file"
	chmod 0600 "$command_file"
	: >"$destination"
	chmod 0600 "$destination"
	for try in {1..6}; do
		printf 'netcat_try=%s destination=%s utc=%s\n' "$try" "$(basename -- "$destination")" \
			"$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
		set +e
		nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
			"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$destination" 2>&1
		status=$?
		set -e
		if grep -Fq "$begin" "$destination" && grep -Fq "$end" "$destination"; then
			printf 'netcat_complete=%s status=%s\n' "$(basename -- "$destination")" "$status" >>"$events"
			return 0
		fi
		sleep 5
	done
	return 1
}

run_probe "$live_probe" "$runtime" __GAEL_DTB_CONTROL_LIVE_BEGIN__ __GAEL_DTB_CONTROL_LIVE_END__ ||
	die 'exact interface appeared but live identity probe did not complete'
grep -Fxq 'kernel_release=7.1.3-gemini-entryled-a' "$runtime" || die 'kernel identity mismatch'
grep -Fxq 'architecture=aarch64' "$runtime" || die 'architecture mismatch'
grep -Fxq 'cpu_online=0-7' "$runtime" || die 'online CPU set changed'
grep -Fxq 'cpu_offline=8-9' "$runtime" || die 'offline CPU set changed'

run_probe "$service_probe" "$service" __GAEL_SERVICE_BEGIN__ __GAEL_SERVICE_END__ ||
	die 'identity passed but service probe did not complete'
printf 'classification=exact-current-kernel-serviceable-with-three-property-DT\n' >>"$events"
(
	cd "$output"
	sha256sum observer-events.txt runtime.txt service.txt >SHA256SUMS
)
chmod 0600 "$output/SHA256SUMS"
cleanup
trap - EXIT HUP INT TERM
printf 'runtime_classification=exact-current-kernel-serviceable-with-three-property-DT\n'
printf 'interface=%s\ncpu_online=0-7\ncpu_offline=8-9\n' "$interface"
printf 'capture=%s\n' "$output"
