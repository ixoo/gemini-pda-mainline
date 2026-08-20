#!/usr/bin/env bash

# Retain an exact pre-trigger capture, issue the one allowed token once, retain
# its terminal result, then request native reboot only after classification.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly WAIT_SECONDS=900
readonly RETURN_SECONDS=600
readonly CANDIDATE_SHA256=b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22
readonly PRETRIGGER_PROBE_SHA256=d28ae6cdf63ca0923f2101ad7252a9908824697280754a69d9e709b553172d54
readonly TRIGGER_PROBE_SHA256=088f6746d8435f43d721b5d666f2111117239aa83c151b2535cb8d488f600f8e
readonly CLASSIFIER_SHA256=9e29a770a0047d02d3a82dbce4c523f613b4232942642a3ab1f64a502e031c16

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/mainline-da921x-same-value-write-attempt-1\n' "$0" >&2
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

for command in awk base64 chmod date dirname find git grep ifconfig ioreg mkdir \
	mktemp mv nc python3 rm route sha256sum sleep sort ssh sync tr xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
output_parent="$(dirname -- "$output")"
mkdir -p -- "$output_parent"
output_parent="$(cd -- "$output_parent" && pwd -P)"
output="$output_parent/$(basename -- "$output")"
case "$output/" in
"$repo_root/artifacts/runtime-captures/"*) ;;
*) die 'output must be below artifacts/runtime-captures' ;;
esac
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite capture'

pretrigger_probe="$script_dir/remote-pretrigger-probe.sh"
trigger_probe="$script_dir/remote-trigger-probe.sh"
classifier="$script_dir/classify-runtime.py"
candidate="$repo_root/artifacts/da921x-same-value-write/candidate-mainline-da921x-same-value-write-b84f3ba8/boot2-padded.img"
key="$repo_root/artifacts/credentials/gemini_ed25519"
for input in "$pretrigger_probe" "$trigger_probe" "$classifier" "$candidate" "$key"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || die "input is unsafe: $input"
done
[[ "$(sha256sum "$pretrigger_probe" | awk '{print $1}')" == "$PRETRIGGER_PROBE_SHA256" ]] ||
	die 'pretrigger probe changed'
[[ "$(sha256sum "$trigger_probe" | awk '{print $1}')" == "$TRIGGER_PROBE_SHA256" ]] ||
	die 'trigger probe changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] ||
	die 'classifier changed'
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$CANDIDATE_SHA256" ]] ||
	die 'candidate changed'
[[ "$(git -C "$repo_root" remote get-url origin)" == \
	'https://github.com/ixoo/gemini-pda-mainline.git' ]] || die 'origin URL changed'

ssh_command=(ssh -i "$key" -o IdentitiesOnly=yes -o IdentityAgent=none
	-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new)
mkdir "$output"
events="$output/events.txt"
pretrigger="$output/pretrigger.txt"
pretrigger_classification="$output/pretrigger-classification.txt"
trigger_capture="$output/trigger.txt"
classification="$output/classification.txt"
usb_events="$output/usb-events.txt"
command_file=

finalize() {
	local status=$?
	if [[ -d "$output" ]]; then
		(
			cd "$output"
			find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
		) >"$output/SHA256SUMS"
		chmod 0600 "$output"/*
		sync
	fi
	[[ -z "${command_file:-}" || ! -e "$command_file" ]] || rm -f -- "$command_file"
	return "$status"
}
trap finalize EXIT
trap 'exit 130' HUP INT TERM

{
	printf 'experiment=2026-08-19-mainline-da921x-same-value-write-implementation\n'
	printf 'candidate_sha256=%s\n' "$CANDIDATE_SHA256"
	printf 'deployment_boot_id_sha256=%s\n' \
		"$(printf '%s' "$deployment_boot_id" | sha256sum | awk '{print $1}')"
	printf 'collector_started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	printf 'trigger_attempt_limit=1\ntrigger_retry_policy=none\n'
	printf 'second_write_policy=forbidden\n'
} >"$events"

last_usb=
record_usb_change() {
	local current
	current="$(ioreg -p IOUSB -l -w 0 2>/dev/null | grep -E 'Gemini|MediaTek|RNDIS|CDC' || true)"
	if [[ "$current" != "$last_usb" ]]; then
		printf 'usb_change_utc=%s\n%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$current" >>"$usb_events"
		last_usb=$current
	fi
}

interface=
mac=
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
	record_usb_change
	# shellcheck disable=SC2046 # macOS ifconfig -l is space-separated.
	for candidate_interface in $(ifconfig -l); do
		candidate_mac="$(ifconfig "$candidate_interface" 2>/dev/null |
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		case "$candidate_mac" in
		42:00:15:19:82:00|42:00:15:19:84:00) ;;
		*) continue ;;
		esac
		ifconfig "$candidate_interface" | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address {found++} END {exit found != 1}' || continue
		route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null |
			awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')" || true
		[[ "$route_interface" == "$candidate_interface" ]] || continue
		interface=$candidate_interface
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
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not become ready'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"

command_file="$(mktemp "${TMPDIR:-/tmp}/.gemini-da921x-same-value.XXXXXXXX")"
make_command() {
	local script=$1 payload
	payload="$(base64 <"$script" | tr -d '\n')"
	[[ "$payload" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'probe payload is malformed'
	printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
		"$payload" >"$command_file"
	chmod 0600 "$command_file"
}

make_command "$pretrigger_probe"
pretrigger_complete=false
for try in {1..6}; do
	attempt_capture="$output/pretrigger-try-${try}.txt"
	printf 'pretrigger_netcat_try=%s utc=%s\n' "$try" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
	set +e
	nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$attempt_capture" 2>&1
	status=$?
	set -e
	if grep -Fqx __DA921X_SAME_VALUE_PRETRIGGER_BEGIN__ "$attempt_capture" &&
		grep -Fqx __DA921X_SAME_VALUE_PRETRIGGER_END__ "$attempt_capture"; then
		mv "$attempt_capture" "$pretrigger"
		printf 'pretrigger_netcat_complete=pretrigger.txt status=%s\n' "$status" >>"$events"
		pretrigger_complete=true
		break
	fi
	sleep 5
done
[[ "$pretrigger_complete" == true ]] || die 'pretrigger probe did not complete'
python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification"
grep -Fqx 'runtime_classification=pretrigger-exact-20' "$pretrigger_classification" ||
	die 'pretrigger capture was rejected'
printf 'pretrigger_durable_before_trigger=yes\n' >>"$events"
sync

make_command "$trigger_probe"
printf 'trigger_token_attempt_utc=%s\ntrigger_retry_policy=none\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
sync
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 45 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$trigger_capture" 2>&1
trigger_status=$?
set -e
printf 'trigger_netcat_status=%s\ntrigger_netcat_attempts=1\n' "$trigger_status" >>"$events"
if ! grep -Fqx __DA921X_SAME_VALUE_TRIGGER_BEGIN__ "$trigger_capture" ||
	! grep -Fqx __DA921X_SAME_VALUE_TRIGGER_END__ "$trigger_capture"; then
	printf 'runtime_classification=transport-lost-during-trigger\ntrigger_retried=no\nnative_reboot_command_sent=no\nresult=stopped\n' >"$classification"
	exit 4
fi
python3 "$classifier" --pretrigger "$pretrigger" --trigger "$trigger_capture" >"$classification"
runtime_classification="$(awk -F= '$1 == "runtime_classification" {print $2; count++} END {exit count != 1}' "$classification")"
case "$runtime_classification" in
success-same-value-write|terminal-failed-no-write|terminal-faulted-no-further-i2c) ;;
*) die 'classifier did not produce a complete terminal result' ;;
esac
printf 'classification=%s\nclassification_durable_before_reboot=yes\n' \
	"$runtime_classification" >>"$events"
sync

printf '/bin/reboot\n' >"$command_file"
printf 'native_reboot_command_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 10 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >/dev/null 2>&1
reboot_status=$?
set -e
printf 'native_reboot_netcat_status=%s\nnative_reboot_command_sent=yes\n' \
	"$reboot_status" >>"$events"

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
			returned=true
			break
		fi
	fi
	sleep 1
done
[[ "$returned" == true ]] || die 'changed Gemian return was not observed'
printf 'native_reboot_to_changed_gemian=passed\nresult=pass\n' >>"$events"
printf 'runtime_classification=%s\n' "$runtime_classification"
printf 'trigger_attempts=1\ntrigger_retries=0\nsecond_writes=0\n'
printf 'native_reboot_to_changed_gemian=passed\ncapture=%s\n' "$output"
