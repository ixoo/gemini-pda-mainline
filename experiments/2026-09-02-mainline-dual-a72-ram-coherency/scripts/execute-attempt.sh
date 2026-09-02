#!/usr/bin/env bash

# Spend the proven CPU8/CPU9 admission trigger once, then make one bounded,
# boot-bound RAM-coherency observation in a second netcat session. Never retry.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly CANDIDATE_SHA256=370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e
readonly SOURCE_EXECUTOR_SHA256=4c472374115c49977c484e0b25be38d1c4e0b914c62da8cd196878cb617b2de7
readonly REMOTE_WRAPPER_SHA256=5cf2730d41d12f1b18860acdd3e85f7d58f565bc2c1fe28857d4e5a83810ba08
readonly CLASSIFIER_SHA256=a5892bfb0d72d176344c93f2ec389e35c5c5f8d7253ac40b61a11d645c39d888
readonly EXPECTED_CAPTURE=artifacts/runtime-captures/a72-dual-ram-coherency-attempt-1
readonly COMMAND_MARKER=__GEMINI_A72_RAM_COHERENCY_SCRIPT__

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
pretrigger_dir=
deployment_boot_id=
wait_seconds=300
recovery_seconds=300
while (($#)); do
	case "$1" in
	--pretrigger-dir)
		(($# >= 2)) || die '--pretrigger-dir requires DIR'
		pretrigger_dir=$2
		shift 2
		;;
	--deployment-boot-id)
		(($# >= 2)) || die '--deployment-boot-id requires UUID'
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
	*) die "unknown option: $1" ;;
	esac
done
[[ "$pretrigger_dir" == "$EXPECTED_CAPTURE" ]] || die "pre-trigger directory must be $EXPECTED_CAPTURE"
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'deployment boot ID is malformed'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die 'wait seconds must be positive'
[[ "$recovery_seconds" =~ ^[1-9][0-9]*$ ]] || die 'recovery seconds must be positive'

for command in awk base64 basename chmod date dirname git grep ifconfig mktemp \
	mv nc netstat python3 rm route sed sha256sum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/execute-completion-lock-repair-trigger.sh"
remote_wrapper="$script_dir/remote-bounded-ram-coherency.sh"
classifier="$script_dir/classify-attempt.py"
for item in "$source_executor" "$remote_wrapper" "$classifier"; do
	[[ -f "$item" && ! -L "$item" ]] || die "required tool is absent or unsafe: $item"
done
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_EXECUTOR_SHA256" ]] || die 'source executor changed'
[[ "$(sha256sum "$remote_wrapper" | awk '{print $1}')" == "$REMOTE_WRAPPER_SHA256" ]] || die 'remote wrapper changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] || die 'classifier changed'
source_dir=$(cd -- "$(dirname -- "$source_executor")" && pwd -P)

case "$pretrigger_dir" in
/*) ;;
*) pretrigger_dir="$repo_root/${pretrigger_dir#./}" ;;
esac
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
pretrigger_dir=$(cd -- "$pretrigger_dir" && pwd -P)
[[ "$(dirname -- "$pretrigger_dir")" == "$private_root" ]] || die 'capture is outside private runtime root'
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
git -C "$repo_root" check-ignore -q -- "$pretrigger_dir" || die 'capture is not ignored by Git'

classification="$pretrigger_dir/classification.txt"
[[ -f "$classification" && ! -L "$classification" ]] || die 'pre-trigger classification is absent or unsafe'
boot_id=$(awk -F= '$1 == "boot_id" { print $2; count++ } END { exit count != 1 }' "$classification") || die 'boot ID is absent or duplicated'

derived_executor=$(mktemp "$source_dir/.derived-execute-dual-a72-ram-parent.XXXXXXXX")
device_probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ram-probe.XXXXXXXX")
command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ram-command.XXXXXXXX")
cleanup() { rm -f -- "${derived_executor:-}" "${device_probe:-}" "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived_executor" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "a72-cpu9-completion-lock-pretrigger-attempt-1"
new = "a72-dual-ram-coherency-attempt-1"
if text.count(old) != 1:
    raise SystemExit("unsafe parent-executor derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived_executor"
/bin/bash "$derived_executor" \
	--pretrigger-dir "$EXPECTED_CAPTURE" \
	--deployment-boot-id "$deployment_boot_id" \
	--wait-seconds "$wait_seconds" \
	--recovery-seconds "$recovery_seconds"

parent_result="$pretrigger_dir/attempt-classification.env"
grep -Fqx 'runtime_classification=cpu8-cpu9-online-accounting-advanced' "$parent_result" || \
	die 'parent CPU8/CPU9 online/accounting gate did not pass'

coherency_intent="$pretrigger_dir/coherency-intent.env"
coherency_capture="$pretrigger_dir/coherency.txt"
coherency_classification="$pretrigger_dir/coherency-classification.env"
coherency_events="$pretrigger_dir/coherency-events.txt"
coherency_status="$pretrigger_dir/coherency-status.env"
coherency_sums="$pretrigger_dir/COHERENCY-SHA256SUMS"
for item in "$coherency_intent" "$coherency_capture" "$coherency_classification" \
	"$coherency_events" "$coherency_status" "$coherency_sums"; do
	[[ ! -e "$item" && ! -L "$item" ]] || die "refusing repeated coherency path: $item exists"
done

"$remote_wrapper" --boot-id "$boot_id" >"$device_probe"
grep -Fq __EXPECTED_BOOT_ID__ "$device_probe" && die 'device probe retained boot-ID marker'
grep -Fq "$COMMAND_MARKER" "$device_probe" && die 'command marker occurs in device probe'
probe_sha256=$(sha256sum "$device_probe" | awk '{print $1}')
{
	printf "/bin/busybox sh <<'%s'\n" "$COMMAND_MARKER"
	sed 's/\r$//' "$device_probe"
	printf '%s\nexit\n' "$COMMAND_MARKER"
} >"$command_file"
chmod 0600 "$command_file"

interface=
matches=0
# shellcheck disable=SC2046
for candidate in $(ifconfig -l); do
	candidate_mac=$(ifconfig "$candidate" 2>/dev/null | \
		awk '/^[[:space:]]*ether / { print tolower($2); count++ } END { exit count != 1 }') || true
	case "$candidate_mac" in
	"$HOST_MAC_82"|"$HOST_MAC_84") ;;
	*) continue ;;
	esac
	ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" \
		'$1 == "inet" && $2 == address { count++ } END { exit count != 1 }' || continue
	routed=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
		awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }') || true
	if [[ -z "$routed" ]]; then
		routed=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" \
			'$1 == "10.15.19/24" && $4 == interface { print $4; count++ } END { exit count != 1 }') || true
	fi
	[[ "$routed" == "$candidate" ]] || continue
	interface=$candidate
	mac=$candidate_mac
	((matches += 1))
done
((matches == 1)) || die "expected one exact Gemini interface, found $matches"

{
	printf 'experiment=2026-09-02-mainline-dual-a72-ram-coherency\n'
	printf 'candidate_full_sha256=%s\nboot_id=%s\n' "$CANDIDATE_SHA256" "$boot_id"
	printf 'parent_classification_sha256=%s\n' "$(sha256sum "$parent_result" | awk '{print $1}')"
	printf 'device_probe_sha256=%s\n' "$probe_sha256"
	printf 'probe_sessions=1\nprobe_retry=forbidden\n'
	printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
	printf 'cpu_off_requests=0\nretries=0\nreboot_requested=no\n'
} >"$coherency_intent"
printf '%s phase=probe-committed interface=%s mac=%s sessions=1 retries=0\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >"$coherency_events"
chmod 0600 "$coherency_intent" "$coherency_events"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$coherency_capture" 2>&1
nc_rc=$?
set -e
chmod 0600 "$coherency_capture"
set +e
python3 "$classifier" --capture "$coherency_capture" --boot-id "$boot_id" \
	>"$coherency_classification"
classification_rc=$?
set -e
chmod 0600 "$coherency_classification"
((classification_rc == 0)) || die "bounded coherency capture rejected rc=$classification_rc nc_rc=$nc_rc"
grep -Fqx 'runtime_classification=dual-a72-ram-integrity-pass' "$coherency_classification" || \
	die 'bounded coherency classification changed'
{
	printf 'result=passed\nboot_id=%s\n' "$boot_id"
	printf 'probe_sessions=1\nprobe_retried=no\n'
	printf 'netcat_status=%s\n' "$nc_rc"
	printf 'device_storage_writes=none\ncpu_off_requests=0\nretries=0\nreboot_requested=no\n'
} >"$coherency_status"
printf '%s phase=probe-classified result=pass nc_status=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$nc_rc" >>"$coherency_events"
chmod 0600 "$coherency_status"
(cd "$pretrigger_dir" && sha256sum coherency-classification.env coherency-events.txt \
	coherency-intent.env coherency-status.env coherency.txt >COHERENCY-SHA256SUMS)
chmod 0600 "$coherency_sums"
python3 - "$coherency_intent" "$coherency_capture" "$coherency_classification" \
	"$coherency_events" "$coherency_status" "$coherency_sums" "$pretrigger_dir" <<'PY'
import os
import sys

for path in sys.argv[1:]:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
cleanup
trap - EXIT HUP INT TERM
printf 'result=passed\nboot_id=%s\n' "$boot_id"
printf '%s\n' runtime_classification=dual-a72-ram-integrity-pass
printf '%s\n' probe_sessions=1 probe_retried=no
