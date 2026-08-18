#!/usr/bin/env bash

# Reclassify immutable attempt-1e evidence, confirm the surviving live state,
# then request the already-planned native return to Gemian. No trigger is sent.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly WAIT_SECONDS=60
readonly RETURN_SECONDS=600
readonly CANDIDATE_SHA256=af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296
readonly SOURCE_MANIFEST_SHA256=e55c548836444b115ecf8bfc39462c3212c8b5fc38a74f7635b6aa25099add5a
readonly RUNTIME_CLASSIFIER_SHA256=6b592f12fd9b75ecbf06705723ca82fe5e0e43024896be16412dfeef7f16075e
readonly CONFIRM_PROBE_SHA256=5dfa1517af1db67bd5aa8965f66d83861487fc7ee0d3b733f0303d0bf94e8f3e
readonly FINALIZATION_CLASSIFIER_SHA256=3ed6af26940ec41ab36c0429244ff4bd6cae63e73f5c63b3c96e2a377e6ac12c

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/mainline-da921x-runtime-preflight-attempt-1e-finalize\n' "$0" >&2
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

for command in awk base64 basename chmod date dirname find git grep ifconfig \
	mkdir mktemp nc python3 rm route sha256sum sleep sort ssh sync tr xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
runtime_classifier="$script_dir/classify-runtime.py"
confirm_probe="$script_dir/remote-posttrigger-confirm.sh"
finalization_classifier="$script_dir/classify-finalization.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"
source="$private_root/mainline-da921x-runtime-preflight-attempt-1e"
for input in "$runtime_classifier" "$confirm_probe" "$finalization_classifier" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "input is missing or unsafe: $input"
done
[[ "$(sha256sum "$runtime_classifier" | awk '{print $1}')" == "$RUNTIME_CLASSIFIER_SHA256" ]] ||
	die 'runtime classifier changed'
[[ "$(sha256sum "$confirm_probe" | awk '{print $1}')" == "$CONFIRM_PROBE_SHA256" ]] ||
	die 'confirmation probe changed'
[[ "$(sha256sum "$finalization_classifier" | awk '{print $1}')" == \
	"$FINALIZATION_CLASSIFIER_SHA256" ]] || die 'finalization classifier changed'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ -d "$source" && ! -L "$source" && -f "$source/SHA256SUMS" ]] ||
	die 'immutable attempt-1e capture is missing or unsafe'
[[ "$(sha256sum "$source/SHA256SUMS" | awk '{print $1}')" == "$SOURCE_MANIFEST_SHA256" ]] ||
	die 'attempt-1e manifest identity changed'
(cd "$source" && sha256sum -c SHA256SUMS >/dev/null) || die 'attempt-1e capture verification failed'

git -C "$repo_root" diff --quiet || die 'worktree is not clean'
git -C "$repo_root" diff --cached --quiet || die 'index is not clean'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == \
	"$(git -C "$repo_root" rev-parse refs/remotes/origin/main)" ]] ||
	die 'HEAD is not the published origin/main'

case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" &&
	"$(basename -- "$output")" == mainline-da921x-runtime-preflight-attempt-1e-finalize ]] ||
	die 'output must be the exact private attempt-1e-finalize child'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

mkdir -m 0700 "$output"
events="$output/finalization-events.txt"
retained="$output/retained-classification.txt"
confirm="$output/posttrigger-confirm.txt"
classification="$output/finalization-classification.txt"
{
	printf 'finalizer=armed\narmed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	printf 'candidate_sha256=%s\nsource_manifest_sha256=%s\n' \
		"$CANDIDATE_SHA256" "$SOURCE_MANIFEST_SHA256"
	printf 'repository_commit=%s\n' "$(git -C "$repo_root" rev-parse HEAD)"
} >"$events"

python3 "$runtime_classifier" --pretrigger "$source/pretrigger.txt" \
	--trigger "$source/trigger.txt" >"$retained"
grep -Fqx 'runtime_classification=success-runtime-preflight-ledger' "$retained" ||
	die 'retained attempt-1e capture did not classify as success'
grep -Fqx 'result=pass' "$retained" || die 'retained attempt-1e pass marker absent'
printf 'retained_classification_sha256=%s\n' \
	"$(sha256sum "$retained" | awk '{print $1}')" >>"$events"
sync

interface=
mac=
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
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
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface is not ready'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"

command_file="$(mktemp "${TMPDIR:-/tmp}/.gemini-da921x-finalize.XXXXXXXX")"
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT HUP INT TERM
payload="$(base64 <"$confirm_probe" | tr -d '\n')"
[[ "$payload" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'confirmation payload is malformed'
printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
	"$payload" >"$command_file"
chmod 0600 "$command_file"

confirm_complete=false
for try in {1..3}; do
	attempt_capture="$output/posttrigger-confirm-try-${try}.txt"
	printf 'confirm_netcat_try=%s utc=%s\n' "$try" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"
	set +e
	nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
		"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$attempt_capture" 2>&1
	status=$?
	set -e
	if grep -Fqx __DA921X_RUNTIME_POSTTRIGGER_CONFIRM_BEGIN__ "$attempt_capture" &&
		grep -Fqx __DA921X_RUNTIME_POSTTRIGGER_CONFIRM_END__ "$attempt_capture"; then
		mv "$attempt_capture" "$confirm"
		printf 'confirm_netcat_complete=posttrigger-confirm.txt status=%s\n' "$status" >>"$events"
		confirm_complete=true
		break
	fi
	sleep 2
done
[[ "$confirm_complete" == true ]] || die 'post-trigger live confirmation did not complete'

python3 "$finalization_classifier" \
	--runtime-classifier "$runtime_classifier" \
	--trigger "$source/trigger.txt" \
	--retained-classification "$retained" \
	--confirm "$confirm" >"$classification"
grep -Fqx 'finalization_classification=posttrigger-live-confirmed' "$classification" ||
	die 'post-trigger live state did not classify'
grep -Fqx 'native_reboot_permitted=once' "$classification" ||
	die 'native reboot permission absent'
grep -Fqx 'result=pass' "$classification" || die 'finalization pass marker absent'
{
	printf 'posttrigger_confirm_sha256=%s\n' "$(sha256sum "$confirm" | awk '{print $1}')"
	printf 'finalization_classification_sha256=%s\n' \
		"$(sha256sum "$classification" | awk '{print $1}')"
	printf 'second_trigger_requests=0\nnative_reboot_gate=passed\n'
} >>"$events"
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

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -i "$identity"
)
returned=false
for ((attempt = 0; attempt < RETURN_SECONDS; attempt++)); do
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

(
	cd "$output"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$output/SHA256SUMS"
chmod 0600 "$output"/*
sync
cleanup
trap - EXIT HUP INT TERM
printf 'finalization_classification=posttrigger-live-confirmed\n'
printf 'retained_runtime_classification=success-runtime-preflight-ledger\n'
printf 'second_trigger_requests=0\n'
printf 'native_reboot_to_changed_gemian=passed\n'
printf 'capture=%s\n' "$output"
