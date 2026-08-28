#!/usr/bin/env bash

# Capture one exact serviceability frame, durably commit it, and only then
# send the one-shot CPU8 token. This helper never retries the trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly HOST_NETMASK=0xffffff00
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly INSTALLED_SHA256=4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef
readonly PRETRIGGER_SCRIPT_SHA256=008a8e33cd67654dc4d3632277b6d1600ef9b565ef7e5b763bb481c424229b60
readonly TRIGGER_SCRIPT_SHA256=93e6ee4b0dd84d6415a84a8bac400308b7fa7483aabab0b414b33016d1ae690b
readonly PRETRIGGER_VALIDATOR_SHA256=906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715
readonly ATTEMPT_CLASSIFIER_SHA256=274b950c8c0dbd2ca3eb6fa7933fe692251de70bf7aadf735bc98d5c12d2886e

die() {
	last_detail=$*
	printf 'error: %s\n' "$*" >&2
	exit 2
}

usage() {
	cat <<'EOF'
usage: collect-live-trigger.sh --output DIR --deployment-boot-id UUID
       [--wait-seconds N] [--recovery-seconds N] [--configure-address]
       [--gemian-target USER@HOST]

Wait for one exact Gemini USB interface, open one read-only netcat session,
validate and fsync the exact armed frame, then open one separate netcat session
that sends the CPU8 trigger exactly once. A completed terminal frame or a
post-commit transport loss is final; the trigger is never retried. The helper
never reads a device partition and never requests a reboot.

DIR must be one new direct child of artifacts/runtime-captures/. The caller's
deployment boot ID must be the known-good Gemian boot ID recorded during the
boot2 installation. --configure-address may add only 10.15.19.1/24 to the
exact known Gemini USB interface via passwordless sudo.
EOF
}

output=
deployment_boot_id=
wait_seconds=1800
recovery_seconds=300
configure_address=0
gemian_target=gemini@192.168.1.50
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires DIR'
		[[ -z "$output" ]] || die '--output was provided more than once'
		output=$2
		shift 2
		;;
	--deployment-boot-id)
		(($# >= 2)) || die '--deployment-boot-id requires UUID'
		[[ -z "$deployment_boot_id" ]] || die '--deployment-boot-id was provided more than once'
		deployment_boot_id=$2
		shift 2
		;;
	--wait-seconds)
		(($# >= 2)) || die '--wait-seconds requires N'
		wait_seconds=$2
		shift 2
		;;
	--recovery-seconds)
		(($# >= 2)) || die '--recovery-seconds requires N'
		recovery_seconds=$2
		shift 2
		;;
	--configure-address)
		configure_address=1
		shift
		;;
	--gemian-target)
		(($# >= 2)) || die '--gemian-target requires USER@HOST'
		gemian_target=$2
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage >&2
		die "unknown option: $1"
		;;
	esac
done

[[ -n "$output" ]] || { usage >&2; die '--output is required'; }
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || \
	die '--deployment-boot-id is malformed'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
[[ "$recovery_seconds" =~ ^[1-9][0-9]*$ ]] || die '--recovery-seconds must be positive'
[[ "$gemian_target" =~ ^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$ ]] || \
	die '--gemian-target is unsafe'

for command in awk basename chmod date dirname git grep ifconfig ioreg mkdir mv \
	nc ping python3 route sed shasum sleep ssh stat sudo sync; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
remote_pretrigger="$script_dir/remote-pretrigger.sh"
remote_trigger="$script_dir/remote-trigger.sh"
pretrigger_validator="$script_dir/validate-pretrigger.py"
attempt_classifier="$script_dir/classify-attempt.py"
readonly script_dir repo_root remote_pretrigger remote_trigger pretrigger_validator attempt_classifier

require_sha256() {
	local path=$1 expected=$2 actual
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	actual="$(shasum -a 256 "$path" | awk '{ print $1 }')"
	[[ "$actual" == "$expected" ]] || die "source checksum mismatch: $path"
}
require_sha256 "$remote_pretrigger" "$PRETRIGGER_SCRIPT_SHA256"
require_sha256 "$remote_trigger" "$TRIGGER_SCRIPT_SHA256"
require_sha256 "$pretrigger_validator" "$PRETRIGGER_VALIDATOR_SHA256"
require_sha256 "$attempt_classifier" "$ATTEMPT_CLASSIFIER_SHA256"

private_root="$repo_root/artifacts/runtime-captures"
if [[ ! -e "$private_root" ]]; then
	mkdir -m 0700 "$private_root"
fi
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
readonly private_root

case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be one direct child of artifacts/runtime-captures/'
output_name="$(basename -- "$output")"
[[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die '--output name is unsafe'
git -C "$repo_root" check-ignore -q -- "$output" || die '--output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
mkdir -m 0700 "$output"
output="$(cd -- "$output" && pwd -P)"
[[ "$(dirname -- "$output")" == "$private_root" ]] || die 'canonical output escaped private root'
readonly output

events="$output/events.txt"
status="$output/status.env"
pretrigger_capture="$output/pretrigger.txt"
pretrigger_classification="$output/pretrigger-classification.env"
trigger_intent="$output/trigger-intent.env"
trigger_capture="$output/trigger.txt"
attempt_classification="$output/attempt-classification.env"
readonly events status pretrigger_capture pretrigger_classification trigger_intent
readonly trigger_capture attempt_classification
: >"$events"
chmod 0600 "$events"

phase=initialized
last_detail=none
interface=unavailable
mac=unavailable
address_added=no
pretrigger_sessions=0
trigger_sessions=0
pretrigger_result=not-run
attempt_result=not-run
gemian_recovery=not-checked
gemian_recovery_boot_id=unavailable
finalized=0
started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
completed_utc=unavailable

file_sha256() {
	shasum -a 256 "$1" | awk '{ print $1 }'
}

log_event() {
	printf '%s phase=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$phase" "$*" >>"$events"
}

fsync_paths() {
	python3 - "$@" <<'PY'
import os
import sys

for item in sys.argv[1:]:
    descriptor = os.open(item, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
}

write_status() {
	local result=$1 code=$2 temporary="$status.partial"
	{
		printf 'experiment=2026-08-28-mainline-a72-admission-live-trigger\n'
		printf 'result=%s\nexit_code=%s\nphase=%s\n' "$result" "$code" "$phase"
		printf 'started_utc=%s\ncompleted_utc=%s\n' "$started_utc" "$completed_utc"
		printf 'installed_full_sha256=%s\n' "$INSTALLED_SHA256"
		printf 'deployment_boot_id=%s\n' "$deployment_boot_id"
		printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$mac" "$HOST_ADDRESS"
		printf 'address_added=%s\npretrigger_sessions=%s\ntrigger_sessions=%s\n' \
			"$address_added" "$pretrigger_sessions" "$trigger_sessions"
		printf 'pretrigger_result=%s\nattempt_result=%s\n' "$pretrigger_result" "$attempt_result"
		printf 'gemian_recovery=%s\ngemian_recovery_boot_id=%s\n' \
			"$gemian_recovery" "$gemian_recovery_boot_id"
		printf 'last_detail=%s\n' "$last_detail"
		printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
		printf 'trigger_maximum=1\ntrigger_retried=no\ncpu9_requests=0\n'
		printf 'cpu_off_requests=0\nretries=0\nreboot_requested=no\n'
	} >"$temporary"
	chmod 0600 "$temporary"
	mv "$temporary" "$status"
}

# shellcheck disable=SC2317
on_exit() {
	local code=$?
	if ((finalized == 0)); then
		set +e
		completed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
		write_status failed "$code"
		fsync_paths "$events" "$status" "$output"
	fi
}
trap on_exit EXIT

discover_exact_interfaces() {
	local candidate candidate_mac
	for candidate in $(ifconfig -l); do
		[[ "$candidate" =~ ^[A-Za-z0-9]+$ ]] || continue
		candidate_mac="$(ifconfig "$candidate" 2>/dev/null | \
			awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
		if [[ "$candidate_mac" == "$HOST_MAC_82" || "$candidate_mac" == "$HOST_MAC_84" ]]; then
			printf '%s\n' "$candidate"
		fi
	done
}

interface_has_address() {
	ifconfig "$1" 2>/dev/null | awk -v address="$HOST_ADDRESS" -v mask="$HOST_NETMASK" \
		'$1 == "inet" && $2 == address && $3 == "netmask" && $4 == mask { found = 1 } END { exit !found }'
}

addresses_elsewhere() {
	local candidate
	for candidate in $(ifconfig -l); do
		[[ "$candidate" =~ ^[A-Za-z0-9]+$ ]] || continue
		if ifconfig "$candidate" 2>/dev/null | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address { found = 1 } END { exit !found }'; then
			printf '%s\n' "$candidate"
		fi
	done
}

route_interface() {
	route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
		awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }'
}

phase=waiting-for-exact-usb
log_event "wait_seconds=$wait_seconds expected_macs=$HOST_MAC_82,$HOST_MAC_84"
deadline=$(( $(date +%s) + wait_seconds ))
while (( $(date +%s) < deadline )); do
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	((match_count <= 1)) || die "multiple exact Gemini interfaces found: $matches"
	if ((match_count == 0)); then
		sleep 1
		continue
	fi
	interface=$matches
	mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
	address_interfaces="$(addresses_elsewhere)"
	address_count="$(printf '%s\n' "$address_interfaces" | awk 'NF { count++ } END { print count + 0 }')"
	if ((address_count > 1)) || { ((address_count == 1)) && [[ "$address_interfaces" != "$interface" ]]; }; then
		die "10.15.19.1 exists on an unexpected interface: ${address_interfaces:-none}"
	fi
	if ! interface_has_address "$interface"; then
		if ((configure_address == 0)); then
			sleep 1
			continue
		fi
		sudo -n ifconfig "$interface" up || die 'cannot bring exact Gemini interface up'
		sudo -n ifconfig "$interface" alias "$HOST_ADDRESS" netmask 255.255.255.0 || \
			die 'cannot add exact Gemini host address'
		address_added=yes
	fi
	interface_has_address "$interface" || die 'exact interface address is absent after configuration'
	[[ "$(addresses_elsewhere)" == "$interface" ]] || die 'host address is not unique'
	[[ "$(route_interface || true)" == "$interface" ]] || { sleep 1; continue; }
	if ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000 "$DEVICE_ADDRESS" >/dev/null 2>&1; then
		break
	fi
	sleep 1
done
(( $(date +%s) < deadline )) || die "exact Gemini USB did not become packet-ready within ${wait_seconds}s"

phase=usb-packet-ready
ifconfig "$interface" >"$output/ifconfig-ready.txt"
ioreg -p IOUSB -w0 -l >"$output/ioreg-ready.txt"
chmod 0600 "$output/ifconfig-ready.txt" "$output/ioreg-ready.txt"
log_event "interface=$interface mac=$mac packet_ready=yes listener_settle_seconds=35"
# The pinned initramfs launches the netcat listener after a bounded 30-second worker delay.
sleep 35
[[ "$(discover_exact_interfaces)" == "$interface" ]] || die 'Gemini interface changed before pre-trigger capture'
interface_has_address "$interface" || die 'Gemini host address disappeared before pre-trigger capture'
[[ "$(route_interface || true)" == "$interface" ]] || die 'Gemini route changed before pre-trigger capture'

make_remote_command() {
	local source=$1 marker=$2 destination=$3
	{
		printf "/bin/busybox sh <<'%s'\n" "$marker"
		sed 's/\r$//' "$source"
		printf '%s\nexit\n' "$marker"
	} >"$destination"
	chmod 0600 "$destination"
}

pretrigger_command="$output/pretrigger-command.txt"
make_remote_command "$remote_pretrigger" __GEMINI_A72_PRETRIGGER_SCRIPT__ "$pretrigger_command"
phase=capturing-pretrigger
pretrigger_sessions=1
log_event 'pretrigger_nc_sessions=1 endpoint=10.15.19.82:2323 access=read-only'
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 45 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$pretrigger_command" >"$pretrigger_capture"
pretrigger_nc_rc=$?
set -e
chmod 0600 "$pretrigger_capture"
((pretrigger_nc_rc == 0)) || die "pre-trigger netcat failed rc=$pretrigger_nc_rc"
python3 "$pretrigger_validator" "$pretrigger_capture" >"$pretrigger_classification"
chmod 0600 "$pretrigger_classification"
pretrigger_result="$(awk -F= '$1 == "pretrigger_classification" { print $2 }' "$pretrigger_classification")"
[[ "$pretrigger_result" == serviceable-armed-zero-execution ]] || die 'pre-trigger validator rejected capture'

phase=committing-trigger-intent
{
	printf 'experiment=2026-08-28-mainline-a72-admission-live-trigger\n'
	printf 'installed_full_sha256=%s\n' "$INSTALLED_SHA256"
	printf 'pretrigger_capture_sha256=%s\n' "$(file_sha256 "$pretrigger_capture")"
	printf 'pretrigger_classification_sha256=%s\n' "$(file_sha256 "$pretrigger_classification")"
	printf 'pretrigger_result=%s\n' "$pretrigger_result"
	printf 'trigger_token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f\n'
	printf 'trigger_maximum=1\ntrigger_retry=forbidden\n'
	printf 'cpu9_requests=0\ncpu_off_requests=0\nretries=0\nreboot_requested=no\n'
	printf 'intent_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$trigger_intent"
chmod 0600 "$trigger_intent"
log_event 'pretrigger=accepted trigger_intent=written trigger_maximum=1'
fsync_paths "$pretrigger_capture" "$pretrigger_classification" "$trigger_intent" "$events" "$output"
sync
log_event 'pretrigger_and_intent_fsync=complete'
fsync_paths "$events" "$output"

trigger_command="$output/trigger-command.txt"
make_remote_command "$remote_trigger" __GEMINI_A72_TRIGGER_SCRIPT__ "$trigger_command"
fsync_paths "$trigger_command" "$output"
phase=executing-trigger-once
trigger_sessions=1
log_event 'trigger_nc_sessions=1 endpoint=10.15.19.82:2323 retries=0'
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$trigger_command" >"$trigger_capture"
trigger_nc_rc=$?
set -e
chmod 0600 "$trigger_capture"
fsync_paths "$trigger_capture" "$events" "$output"

set +e
python3 "$attempt_classifier" --pretrigger "$pretrigger_capture" --trigger "$trigger_capture" \
	>"$attempt_classification"
classification_rc=$?
set -e
chmod 0600 "$attempt_classification"
fsync_paths "$attempt_classification" "$output"
((classification_rc == 0)) || die "attempt classifier rejected transcript rc=$classification_rc nc_rc=$trigger_nc_rc"
attempt_result="$(awk -F= '$1 == "runtime_classification" { print $2 }' "$attempt_classification")"

if [[ "$attempt_result" == trigger-boundary-transport-loss ]]; then
	phase=monitoring-gemian-recovery
	key="$repo_root/artifacts/credentials/gemini_ed25519"
	[[ -f "$key" && ! -L "$key" && "$(stat -f '%Lp' "$key")" == 600 ]] || \
		die 'private Gemini SSH key is absent or unsafe'
	recovery_deadline=$(( $(date +%s) + recovery_seconds ))
	while (( $(date +%s) < recovery_deadline )); do
		set +e
		observed_boot_id="$(ssh -i "$key" -o IdentitiesOnly=yes -o IdentityAgent=none \
			-o BatchMode=yes -o ConnectTimeout=5 "$gemian_target" \
			'cat /proc/sys/kernel/random/boot_id' 2>/dev/null)"
		ssh_rc=$?
		set -e
		if ((ssh_rc == 0)) && [[ "$observed_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] && \
			[[ "$observed_boot_id" != "$deployment_boot_id" ]]; then
			gemian_recovery=changed-boot-id-observed
			gemian_recovery_boot_id=$observed_boot_id
			break
		fi
		sleep 5
	done
	if [[ "$gemian_recovery" != changed-boot-id-observed ]]; then
		gemian_recovery=no-changed-id-within-window
	fi
fi

phase=classified
last_detail="$attempt_result"
completed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
log_event "attempt_result=$attempt_result trigger_nc_rc=$trigger_nc_rc gemian_recovery=$gemian_recovery"
write_status passed 0
fsync_paths "$events" "$status" "$output"
finalized=1
trap - EXIT
printf 'result=passed\noutput=%s\npretrigger_result=%s\nattempt_result=%s\n' \
	"$output" "$pretrigger_result" "$attempt_result"
