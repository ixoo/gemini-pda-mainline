#!/usr/bin/env bash

# Retain an exact pre-trigger capture before issuing one runtime token. The
# trigger is never retried; native reboot follows only a complete exact pass.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly WAIT_SECONDS=900
readonly RETURN_SECONDS=600
readonly CANDIDATE_SHA256=af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296
readonly PRETRIGGER_PROBE_SHA256=f8220774f4689f655bc2b5f8993ded11da04dd6c966d7b32da8a8bfe07b5825b
readonly TRIGGER_PROBE_SHA256=23ef1bb790e5ec301bc15cf7ddf7b23bc3953cd67266f2f988e5870edeabd08c
readonly CLASSIFIER_SHA256=865c911afbe755e9abb8bd4c7273ce7fda54972d88b64202375e9abafa00920b

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/mainline-da921x-runtime-preflight-attempt-1d\n' "$0" >&2
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

for command in awk base64 basename chmod date dirname find git grep ifconfig ioreg \
	mkdir mktemp mv nc python3 rm route sha256sum sleep sort ssh sync tr xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
pretrigger_probe="$script_dir/remote-pretrigger-probe.sh"
trigger_probe="$script_dir/remote-trigger-probe.sh"
classifier="$script_dir/classify-runtime.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"
for input in "$pretrigger_probe" "$trigger_probe" "$classifier" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "input is missing or unsafe: $input"
done
[[ "$(sha256sum "$pretrigger_probe" | awk '{print $1}')" == "$PRETRIGGER_PROBE_SHA256" ]] ||
	die 'pretrigger probe changed'
[[ "$(sha256sum "$trigger_probe" | awk '{print $1}')" == "$TRIGGER_PROBE_SHA256" ]] ||
	die 'trigger probe changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] ||
	die 'classifier changed'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" &&
	"$(basename -- "$output")" == mainline-da921x-runtime-preflight-attempt-1d ]] ||
	die 'output must be the exact private attempt-1d child'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

mkdir -m 0700 "$output"
events="$output/observer-events.txt"
usb_topology="$output/usb-topology.txt"
pretrigger="$output/pretrigger.txt"
pretrigger_classification="$output/pretrigger-classification.txt"
trigger_capture="$output/trigger.txt"
classification="$output/classification.txt"
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

finalize() {
	(
		cd "$output"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
	) >"$output/SHA256SUMS"
	chmod 0600 "$output"/*
	sync
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
			finalize
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not become ready before timeout'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"

command_file="$(mktemp "${TMPDIR:-/tmp}/.gemini-da921x-runtime-preflight.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT HUP INT TERM
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
	if grep -Fqx __DA921X_RUNTIME_PRETRIGGER_BEGIN__ "$attempt_capture" &&
		grep -Fqx __DA921X_RUNTIME_PRETRIGGER_END__ "$attempt_capture"; then
		mv "$attempt_capture" "$pretrigger"
		printf 'pretrigger_netcat_complete=pretrigger.txt status=%s\n' "$status" >>"$events"
		pretrigger_complete=true
		break
	fi
	sleep 5
done
[[ "$pretrigger_complete" == true ]] || die 'exact interface appeared but pretrigger probe did not complete'
python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification"
grep -Fqx 'runtime_classification=pretrigger-exact-20' "$pretrigger_classification" ||
	die 'pretrigger capture did not classify as exact 20'
{
	printf 'pretrigger_capture_sha256=%s\n' "$(sha256sum "$pretrigger" | awk '{print $1}')"
	printf 'pretrigger_classification_sha256=%s\n' \
		"$(sha256sum "$pretrigger_classification" | awk '{print $1}')"
	printf 'pretrigger_durable_before_trigger=yes\n'
} >>"$events"
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
if ! grep -Fqx __DA921X_RUNTIME_TRIGGER_BEGIN__ "$trigger_capture" ||
	! grep -Fqx __DA921X_RUNTIME_TRIGGER_END__ "$trigger_capture"; then
	{
		printf 'runtime_classification=transport-lost-during-trigger\n'
		printf 'pretrigger_classification=exact-20\n'
		printf 'trigger_command_started=%s\n' \
			"$(grep -Fqc 'trigger_command_started=yes' "$trigger_capture" || true)"
		printf 'trigger_retried=no\nnative_reboot_command_sent=no\n'
		printf 'Gate6_B3=blocking\nGate6_B4=blocking\nresult=stopped\n'
	} >"$classification"
	printf 'classification=transport-lost-during-trigger\n' >>"$events"
	finalize
	exit 4
fi
set +e
python3 "$classifier" --pretrigger "$pretrigger" --trigger "$trigger_capture" >"$classification" 2>&1
classifier_status=$?
set -e
if (( classifier_status != 0 )) ||
	! grep -Fqx 'runtime_classification=success-runtime-preflight-ledger' "$classification"; then
	printf 'classification=posttrigger-rejected status=%s\n' "$classifier_status" >>"$events"
	printf 'native_reboot_command_sent=no\n' >>"$classification"
	finalize
	exit 5
fi

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

finalize
cleanup
trap - EXIT HUP INT TERM
printf 'runtime_classification=success-runtime-preflight-ledger\n'
printf 'I2C6_pretrigger_sequence=exact-20-of-20\n'
printf 'I2C6_posttrigger_sequence=exact-30-of-30\n'
printf 'DA921x_register_data_writes=0\nCPU8_CPU9_admission=closed\n'
printf 'native_reboot_to_changed_gemian=passed\n'
printf 'capture=%s\n' "$output"
