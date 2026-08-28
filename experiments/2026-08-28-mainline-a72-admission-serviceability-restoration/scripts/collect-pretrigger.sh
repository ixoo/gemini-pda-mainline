#!/usr/bin/env bash

# Pre-arm one read-only serviceability/armed-state capture. Never trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1 DEVICE_ADDRESS=10.15.19.82 DEVICE_PORT=2323 GEMIAN_ADDRESS=192.168.1.50 WAIT_SECONDS=1800
readonly CANDIDATE_SHA256=f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02
readonly WRAPPER_SHA256=55361c7e8df662a1c124b2bd1fe9eef6e22aee85a442883ccc2004173bb21c1e
readonly PROBE_SHA256=bd0c14b6320713e1b73ef4ec3fee908c026babd35bbbe2131701e3aaf082cd90
readonly VALIDATOR_SHA256=5afa0f77e601f6407fc8a993ac0585148b8fc8567cb81947b576069f29b282e3
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
deployment_boot_id=''; output=''
while (($#)); do case "$1" in
	--deployment-boot-id) deployment_boot_id=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	*) die "usage: $0 --deployment-boot-id UUID --output artifacts/runtime-captures/a72-admission-serviceability-attempt-1" ;;
esac; done
[[ "$deployment_boot_id" =~ ^[0-9a-f-]{36}$ && -n "$output" ]] || die 'arguments missing or malformed'
for command in awk base64 basename chmod date dirname git grep ifconfig mkdir mktemp nc netstat python3 rm route sha256sum sleep ssh tr; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
wrapper="$script_dir/remote-pretrigger.sh"; validator="$script_dir/validate-pretrigger.py"; identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ "$(sha256sum "$wrapper" | awk '{print $1}')" == "$WRAPPER_SHA256" ]] || die 'probe wrapper changed'
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || die 'validator changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'identity is missing or unsafe'
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
private_root=$(cd -- "$repo_root/artifacts/runtime-captures" && pwd -P)
[[ "$(dirname -- "$output")" == "$private_root" && "$(basename -- "$output")" == a72-admission-serviceability-attempt-1 ]] || die 'output path changed'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'; git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored'
mkdir -m 0700 "$output"; events="$output/observer-events.txt"; frame="$output/pretrigger.txt"; classification="$output/classification.txt"
probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-serviceability-probe.XXXXXXXX"); command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-serviceability-command.XXXXXXXX")
cleanup() { rm -f -- "${probe:-}" "${command_file:-}"; }; trap cleanup EXIT HUP INT TERM
"$wrapper" >"$probe"; [[ "$(sha256sum "$probe" | awk '{print $1}')" == "$PROBE_SHA256" ]] || die 'materialized probe changed'
printf 'observer=armed\ncandidate_sha256=%s\narmed_utc=%s\n' "$CANDIDATE_SHA256" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$events"
ssh_command=(ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity")
interface=''; mac=''
for ((attempt=0; attempt<WAIT_SECONDS; attempt++)); do
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		candidate_mac=$(ifconfig "$candidate" 2>/dev/null | awk '/^[[:space:]]*ether / {print tolower($2); n++} END {exit n != 1}') || true
		case "$candidate_mac" in 42:00:15:19:82:00|42:00:15:19:84:00) ;; *) continue ;; esac
		ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {n++} END {exit n != 1}' || continue
		route_interface=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; n++} END {exit n != 1}') || true
		if [[ -z "$route_interface" ]]; then route_interface=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" '$1 == "10.15.19/24" && $4 == interface {print $4; n++} END {exit n != 1}') || true; fi
		[[ "$route_interface" == "$candidate" ]] || continue
		interface=$candidate; mac=$candidate_mac; break 2
	done
	if ((attempt % 5 == 0)); then
		# shellcheck disable=SC2016
		gemian=$("${ssh_command[@]}" gemini@"$GEMIAN_ADDRESS" 'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' 2>/dev/null || true)
		if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ && "${BASH_REMATCH[1]}" != "$deployment_boot_id" ]]; then printf 'classification=no-mainline-usb-before-changed-Gemian-return\ngemian_boot_id=%s\n' "${BASH_REMATCH[1]}" >>"$events"; (cd "$output" && sha256sum observer-events.txt >SHA256SUMS); exit 3; fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"
payload=$(base64 <"$probe" | tr -d '\n'); printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" "$payload" >"$command_file"; chmod 0600 "$command_file"; : >"$frame"; chmod 0600 "$frame"
complete=false
for try in {1..6}; do
	printf 'netcat_try=%s utc=%s\n' "$try" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
	set +e; nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 "$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$frame" 2>&1; nc_rc=$?; set -e
	if grep -Fq __GEMINI_A72_LIVE_PRETRIGGER_BEGIN__ "$frame" && grep -Fq __GEMINI_A72_LIVE_PRETRIGGER_END__ "$frame"; then printf 'netcat_complete=yes status=%s\n' "$nc_rc" >>"$events"; complete=true; break; fi
	sleep 5
done
[[ "$complete" == true ]] || die 'pre-trigger frame did not complete'
python3 "$validator" "$frame" >"$classification"
grep -Fqx 'pretrigger_classification=serviceable-armed-zero-execution' "$classification" || die 'pre-trigger frame rejected'
printf 'trigger_session=none\nsuccessful_mainline_left_running=yes\nnative_reboot_command_sent=no\n' >>"$events"
(cd "$output" && sha256sum classification.txt observer-events.txt pretrigger.txt >SHA256SUMS); chmod 0600 "$output"/*
cleanup; trap - EXIT HUP INT TERM
printf 'pretrigger_classification=serviceable-armed-zero-execution\ntrigger_session=none\nsuccessful_mainline_left_running=yes\ncapture=%s\n' "$output"
