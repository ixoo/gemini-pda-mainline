#!/usr/bin/env bash

# Validate a durable pre-trigger capture, commit one exact trigger intent, and
# open exactly one boot-bound CPU8 trigger session. This helper never retries.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly CANDIDATE_SHA256=a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179
readonly TRIGGER_WRAPPER_SHA256=620c6273e59286f65e67084bb071ae60cd53b27e9634188492cc47611d6f37d2
readonly CLASSIFIER_SHA256=3d5bfa25d84239232d765b4fba000ffa89246bf20ed636bca19e3afe92d1f9dd
readonly VALIDATOR_SHA256=8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52
readonly TOKEN_SHA256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f

die() {
	last_detail=$*
	printf 'error: %s\n' "$*" >&2
	exit 2
}

usage() {
	cat <<'EOF'
usage: execute-trigger.sh --pretrigger-dir DIR --deployment-boot-id UUID
                          [--wait-seconds N] [--recovery-seconds N]

DIR must be the completed, ignored private capture directory created by this
experiment's collect-pretrigger.sh. The helper revalidates and fsyncs that
baseline, then sends the CPU8 token in exactly one netcat session bound to the
same boot ID. It never retries, requests CPU9, requests CPU_OFF, or reboots.
EOF
}

pretrigger_dir=
deployment_boot_id=
wait_seconds=300
recovery_seconds=300
while (($#)); do
	case "$1" in
	--pretrigger-dir)
		(($# >= 2)) || die '--pretrigger-dir requires DIR'
		[[ -z "$pretrigger_dir" ]] || die '--pretrigger-dir was provided more than once'
		pretrigger_dir=$2
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

[[ -n "$pretrigger_dir" ]] || { usage >&2; die '--pretrigger-dir is required'; }
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || \
	die '--deployment-boot-id is malformed'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
[[ "$recovery_seconds" =~ ^[1-9][0-9]*$ ]] || die '--recovery-seconds must be positive'

for command in awk base64 basename cat chmod date dirname git grep ifconfig mkdir \
	mktemp mv nc netstat ping python3 rm route sed sha256sum sleep ssh stat sync tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
trigger_wrapper="$script_dir/remote-trigger.sh"
classifier="$script_dir/classify-attempt.py"
validator="$script_dir/validate-pretrigger.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly script_dir repo_root trigger_wrapper classifier validator identity

require_sha256() {
	local path=$1 expected=$2 actual
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	actual=$(sha256sum "$path" | awk '{print $1}')
	[[ "$actual" == "$expected" ]] || die "source checksum mismatch: $path"
}
require_sha256 "$trigger_wrapper" "$TRIGGER_WRAPPER_SHA256"
require_sha256 "$classifier" "$CLASSIFIER_SHA256"
require_sha256 "$validator" "$VALIDATOR_SHA256"

private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
case "$pretrigger_dir" in
/*) ;;
*) pretrigger_dir="$repo_root/${pretrigger_dir#./}" ;;
esac
[[ -d "$pretrigger_dir" && ! -L "$pretrigger_dir" ]] || die 'pre-trigger directory is absent or unsafe'
pretrigger_dir=$(cd -- "$pretrigger_dir" && pwd -P)
[[ "$(dirname -- "$pretrigger_dir")" == "$private_root" ]] || \
	die '--pretrigger-dir must be one direct child of artifacts/runtime-captures/'
[[ "$(basename -- "$pretrigger_dir")" == a72-ready-token-contract-repair-pretrigger-attempt-1 ]] || \
	die 'pre-trigger directory identity changed'
git -C "$repo_root" check-ignore -q -- "$pretrigger_dir" || die 'pre-trigger directory is not ignored'
readonly private_root pretrigger_dir

pretrigger="$pretrigger_dir/pretrigger.txt"
pretrigger_classification="$pretrigger_dir/classification.txt"
pretrigger_sums="$pretrigger_dir/SHA256SUMS"
observer_events="$pretrigger_dir/observer-events.txt"
for file in "$pretrigger" "$pretrigger_classification" "$pretrigger_sums" "$observer_events"; do
	[[ -f "$file" && ! -L "$file" ]] || die "completed pre-trigger evidence is absent or unsafe: $file"
done
(cd "$pretrigger_dir" && sha256sum -c SHA256SUMS >/dev/null) || die 'pre-trigger evidence checksum failed'

validated=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ready-contract-validation.XXXXXXXX")
derived_trigger=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ready-contract-trigger.XXXXXXXX")
trigger_command=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ready-contract-command.XXXXXXXX")
cleanup() {
	rm -f -- "${validated:-}" "${derived_trigger:-}" "${trigger_command:-}"
}
trap cleanup EXIT HUP INT TERM
python3 "$validator" "$pretrigger" >"$validated"
grep -Fqx 'pretrigger_classification=serviceable-armed-zero-execution' "$validated" || \
	die 'pre-trigger frame failed current validation'
boot_id=$(awk -F= '$1 == "boot_id" {print $2; count++} END {exit count != 1}' "$validated") || \
	die 'pre-trigger boot ID is absent or duplicated'
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || \
	die 'pre-trigger boot ID is malformed'
grep -Fqx "boot_id=$boot_id" "$pretrigger_classification" || \
	die 'durable and current pre-trigger classifications disagree on boot ID'
"$trigger_wrapper" --boot-id "$boot_id" >"$derived_trigger"
chmod 0700 "$derived_trigger"

trigger_intent="$pretrigger_dir/trigger-intent.env"
trigger_capture="$pretrigger_dir/trigger.txt"
attempt_classification="$pretrigger_dir/attempt-classification.env"
trigger_events="$pretrigger_dir/trigger-events.txt"
trigger_status="$pretrigger_dir/trigger-status.env"
for file in "$trigger_intent" "$trigger_capture" "$attempt_classification" \
	"$trigger_events" "$trigger_status"; do
	[[ ! -e "$file" && ! -L "$file" ]] || die "refusing a repeated trigger path: $file already exists"
done
readonly pretrigger pretrigger_classification pretrigger_sums observer_events
readonly trigger_intent trigger_capture attempt_classification trigger_events trigger_status

phase=initialized
last_detail=none
interface=unavailable
mac=unavailable
trigger_sessions=0
attempt_result=not-run
gemian_recovery=not-checked
gemian_recovery_boot_id=unavailable
started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
completed_utc=unavailable
finalized=0

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
	local result=$1 code=$2 temporary="$trigger_status.partial"
	{
		printf 'experiment=2026-08-30-mainline-a72-ready-token-contract-repair\n'
		printf 'result=%s\nexit_code=%s\nphase=%s\n' "$result" "$code" "$phase"
		printf 'started_utc=%s\ncompleted_utc=%s\n' "$started_utc" "$completed_utc"
		printf 'installed_full_sha256=%s\nboot_id=%s\ndeployment_boot_id=%s\n' \
			"$CANDIDATE_SHA256" "$boot_id" "$deployment_boot_id"
		printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$mac" "$HOST_ADDRESS"
		printf 'trigger_sessions=%s\nattempt_result=%s\n' "$trigger_sessions" "$attempt_result"
		printf 'gemian_recovery=%s\ngemian_recovery_boot_id=%s\n' \
			"$gemian_recovery" "$gemian_recovery_boot_id"
		printf 'last_detail=%s\n' "$last_detail"
		printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
		printf 'trigger_maximum=1\ntrigger_retried=no\ncpu9_requests=0\n'
		printf 'cpu_off_requests=0\nretries=0\nreboot_requested=no\n'
	} >"$temporary"
	chmod 0600 "$temporary"
	mv "$temporary" "$trigger_status"
}

# shellcheck disable=SC2317
on_exit() {
	local code=$?
	cleanup
	if ((finalized == 0)); then
		set +e
		completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
		write_status failed "$code"
		fsync_paths "$trigger_status" "$pretrigger_dir"
	fi
}
trap on_exit EXIT
trap 'exit 130' HUP INT TERM

discover_exact_interfaces() {
	local candidate candidate_mac
	for candidate in $(ifconfig -l); do
		[[ "$candidate" =~ ^[A-Za-z0-9]+$ ]] || continue
		candidate_mac=$(ifconfig "$candidate" 2>/dev/null | \
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}') || true
		if [[ "$candidate_mac" == "$HOST_MAC_82" || "$candidate_mac" == "$HOST_MAC_84" ]]; then
			printf '%s\n' "$candidate"
		fi
	done
}

interface_has_address() {
	ifconfig "$1" 2>/dev/null | awk -v address="$HOST_ADDRESS" \
		'$1 == "inet" && $2 == address {count++} END {exit count != 1}'
}

route_interface() {
	local candidate=$1 routed
	routed=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
		awk '$1 == "interface:" {print $2; count++} END {exit count != 1}') || true
	if [[ -z "$routed" ]]; then
		routed=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" \
			'$1 == "10.15.19/24" && $4 == interface {print $4; count++} END {exit count != 1}') || true
	fi
	printf '%s\n' "$routed"
}

phase=waiting-for-exact-usb
deadline=$(( $(date +%s) + wait_seconds ))
while (( $(date +%s) < deadline )); do
	matches=$(discover_exact_interfaces)
	match_count=$(printf '%s\n' "$matches" | awk 'NF {count++} END {print count + 0}')
	((match_count <= 1)) || die "multiple exact Gemini interfaces found: $matches"
	if ((match_count == 1)); then
		interface=$matches
		mac=$(ifconfig "$interface" | awk '/^[[:space:]]*ether / {print tolower($2); exit}')
		if interface_has_address "$interface" && [[ "$(route_interface "$interface")" == "$interface" ]] && \
			ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000 "$DEVICE_ADDRESS" >/dev/null 2>&1; then
			break
		fi
	fi
	sleep 1
done
(( $(date +%s) < deadline )) || die 'exact boot2 USB path did not become packet-ready'

phase=committing-trigger-intent
{
	printf 'experiment=2026-08-30-mainline-a72-ready-token-contract-repair\n'
	printf 'installed_full_sha256=%s\nboot_id=%s\n' "$CANDIDATE_SHA256" "$boot_id"
	printf 'pretrigger_sha256=%s\n' "$(sha256sum "$pretrigger" | awk '{print $1}')"
	printf 'pretrigger_classification_sha256=%s\n' \
		"$(sha256sum "$pretrigger_classification" | awk '{print $1}')"
	printf 'derived_trigger_sha256=%s\ntrigger_token_sha256=%s\n' \
		"$(sha256sum "$derived_trigger" | awk '{print $1}')" "$TOKEN_SHA256"
	printf 'trigger_maximum=1\ntrigger_retry=forbidden\n'
	printf 'cpu9_requests=0\ncpu_off_requests=0\nretries=0\nreboot_requested=no\n'
	printf 'intent_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$trigger_intent"
printf '%s phase=%s interface=%s mac=%s pretrigger=accepted trigger_maximum=1\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$phase" "$interface" "$mac" >"$trigger_events"
chmod 0600 "$trigger_intent" "$trigger_events"
fsync_paths "$pretrigger" "$pretrigger_classification" "$trigger_intent" \
	"$trigger_events" "$pretrigger_dir"
sync

payload=$(base64 <"$derived_trigger" | tr -d '\n')
printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" "$payload" >"$trigger_command"
chmod 0600 "$trigger_command"
fsync_paths "$trigger_command"

phase=executing-trigger-once
trigger_sessions=1
printf '%s phase=%s trigger_nc_sessions=1 endpoint=%s:%s retries=0\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$phase" "$DEVICE_ADDRESS" "$DEVICE_PORT" >>"$trigger_events"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$trigger_command" >"$trigger_capture"
trigger_nc_rc=$?
set -e
chmod 0600 "$trigger_capture"
fsync_paths "$trigger_capture" "$trigger_events" "$pretrigger_dir"

set +e
python3 "$classifier" --pretrigger "$pretrigger" --trigger "$trigger_capture" \
	>"$attempt_classification"
classification_rc=$?
set -e
chmod 0600 "$attempt_classification"
fsync_paths "$attempt_classification" "$pretrigger_dir"
((classification_rc == 0)) || die "attempt transcript rejected rc=$classification_rc nc_rc=$trigger_nc_rc"
attempt_result=$(awk -F= '$1 == "runtime_classification" {print $2; count++} END {exit count != 1}' \
	"$attempt_classification") || die 'attempt classification is absent or duplicated'

if [[ "$attempt_result" == trigger-boundary-transport-loss ]]; then
	phase=monitoring-gemian-recovery
	[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || \
		die 'private Gemini SSH key is absent or unsafe'
	recovery_deadline=$(( $(date +%s) + recovery_seconds ))
	while (( $(date +%s) < recovery_deadline )); do
		set +e
		observed_boot_id=$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o IdentitiesOnly=yes \
			-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
			-i "$identity" gemini@"$GEMIAN_ADDRESS" 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null)
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
last_detail=$attempt_result
completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s phase=%s attempt_result=%s trigger_nc_rc=%s gemian_recovery=%s\n' \
	"$completed_utc" "$phase" "$attempt_result" "$trigger_nc_rc" "$gemian_recovery" >>"$trigger_events"
write_status passed 0
(cd "$pretrigger_dir" && sha256sum attempt-classification.env classification.txt \
	observer-events.txt pretrigger.txt trigger-events.txt trigger-intent.env trigger-status.env \
	trigger.txt >TRIGGER-SHA256SUMS)
chmod 0600 "$pretrigger_dir"/*
fsync_paths "$trigger_events" "$trigger_status" "$pretrigger_dir/TRIGGER-SHA256SUMS" "$pretrigger_dir"
finalized=1
cleanup
trap - EXIT HUP INT TERM
printf 'result=passed\nboot_id=%s\nattempt_result=%s\ntrigger_sessions=1\ntrigger_retried=no\n' \
	"$boot_id" "$attempt_result"
