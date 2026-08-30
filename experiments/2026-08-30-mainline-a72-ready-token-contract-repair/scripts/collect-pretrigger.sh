#!/usr/bin/env bash

# Capture one complete read-only READY frame with a bounded here-document
# transport. This helper never opens the trigger path.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly WAIT_SECONDS=300
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly CANDIDATE_SHA256=a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179
readonly WRAPPER_SHA256=bbb041f98bad1fa071a2aebf1c22ebaa462d5f3e45bb8472c59afd6fc1e7d83d
readonly PROBE_SHA256=ea8d422fca8cdfc8af5c5c3fc57f9d1988ccaaa700e1f4cceac0489f37053234
readonly VALIDATOR_SHA256=8feeb6e8c562278c0e76c284a757c8849dcc0d1e5eff705fee3434229c82eb52
readonly COMMAND_MARKER=__GEMINI_A72_READY_CONTRACT_PRETRIGGER_SCRIPT__

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
deployment_boot_id=
output=
while (($#)); do
	case "$1" in
	--deployment-boot-id)
		(($# >= 2)) || die '--deployment-boot-id requires UUID'
		deployment_boot_id=$2
		shift 2
		;;
	--output)
		(($# >= 2)) || die '--output requires DIR'
		output=$2
		shift 2
		;;
	*)
		die "usage: $0 --deployment-boot-id UUID --output artifacts/runtime-captures/a72-ready-token-contract-repair-pretrigger-attempt-1"
		;;
	esac
done
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || \
	die 'deployment boot ID is missing or malformed'
[[ -n "$output" ]] || die '--output is required'

for command in awk basename chmod date dirname git grep ifconfig mkdir mktemp \
	mv nc netstat python3 rm route sed sha256sum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
wrapper="$script_dir/remote-pretrigger.sh"
validator="$script_dir/validate-pretrigger.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly script_dir repo_root wrapper validator identity

require_sha256() {
	local path=$1 expected=$2 actual
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	actual=$(sha256sum "$path" | awk '{print $1}')
	[[ "$actual" == "$expected" ]] || die "source checksum mismatch: $path"
}
require_sha256 "$wrapper" "$WRAPPER_SHA256"
require_sha256 "$validator" "$VALIDATOR_SHA256"
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || \
	die 'private Gemini SSH key is absent or unsafe'

case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be one direct child of artifacts/runtime-captures/'
[[ "$(basename -- "$output")" == a72-ready-token-contract-repair-pretrigger-attempt-1 ]] || \
	die 'output directory identity changed'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
mkdir -m 0700 "$output"
output=$(cd -- "$output" && pwd -P)
readonly private_root output

events="$output/observer-events.txt"
frame="$output/pretrigger.txt"
classification="$output/classification.txt"
sums="$output/SHA256SUMS"
readonly events frame classification sums
probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ready-contract-probe.XXXXXXXX")
command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-ready-contract-command.XXXXXXXX")
cleanup() { rm -f -- "${probe:-}" "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM

"$wrapper" >"$probe"
[[ "$(sha256sum "$probe" | awk '{print $1}')" == "$PROBE_SHA256" ]] || \
	die 'materialized device probe changed'
grep -Fq "$COMMAND_MARKER" "$probe" && die 'command marker occurs in materialized probe'
{
	printf "/bin/busybox sh <<'%s'\n" "$COMMAND_MARKER"
	sed 's/\r$//' "$probe"
	printf '%s\nexit\n' "$COMMAND_MARKER"
} >"$command_file"
chmod 0600 "$command_file"
printf 'observer=armed\ncandidate_sha256=%s\narmed_utc=%s\n' \
	"$CANDIDATE_SHA256" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$events"

ssh_command=(ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes \
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity")
interface=
mac=
for ((attempt=0; attempt<WAIT_SECONDS; attempt++)); do
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		candidate_mac=$(ifconfig "$candidate" 2>/dev/null | \
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}') || true
		case "$candidate_mac" in
		"$HOST_MAC_82"|"$HOST_MAC_84") ;;
		*) continue ;;
		esac
		ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address {count++} END {exit count != 1}' || continue
		route_interface=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
			awk '$1 == "interface:" {print $2; count++} END {exit count != 1}') || true
		if [[ -z "$route_interface" ]]; then
			route_interface=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" \
				'$1 == "10.15.19/24" && $4 == interface {print $4; count++} END {exit count != 1}') || true
		fi
		[[ "$route_interface" == "$candidate" ]] || continue
		interface=$candidate
		mac=$candidate_mac
		break 2
	done
	if ((attempt % 5 == 0)); then
		# shellcheck disable=SC2016
		gemian=$("${ssh_command[@]}" gemini@"$GEMIAN_ADDRESS" \
			'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' \
			2>/dev/null || true)
		if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ && \
			"${BASH_REMATCH[1]}" != "$deployment_boot_id" ]]; then
			printf 'classification=no-mainline-usb-before-changed-Gemian-return\ngemian_boot_id=%s\n' \
				"${BASH_REMATCH[1]}" >>"$events"
			(cd "$output" && sha256sum observer-events.txt >SHA256SUMS)
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"
printf 'netcat_sessions=1 transport=bounded-heredoc access=read-only utc=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 45 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$frame" 2>&1
nc_rc=$?
set -e
chmod 0600 "$frame"
if ! grep -Fq __GEMINI_A72_LIVE_PRETRIGGER_BEGIN__ "$frame" || \
	! grep -Fq __GEMINI_A72_LIVE_PRETRIGGER_END__ "$frame"; then
	die "pre-trigger frame did not complete rc=$nc_rc"
fi
python3 "$validator" "$frame" >"$classification"
grep -Fqx 'pretrigger_classification=serviceable-armed-zero-execution' "$classification" || \
	die 'pre-trigger frame rejected'
printf 'netcat_complete=yes status=%s\ntrigger_session=none\n' "$nc_rc" >>"$events"
printf 'successful_mainline_left_running=yes\nnative_reboot_command_sent=no\n' >>"$events"
(cd "$output" && sha256sum classification.txt observer-events.txt pretrigger.txt >SHA256SUMS)
chmod 0600 "$output"/*
python3 - "$classification" "$events" "$frame" "$sums" "$output" <<'PY'
import os
import sys

for item in sys.argv[1:]:
    descriptor = os.open(item, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
cleanup
trap - EXIT HUP INT TERM
printf 'pretrigger_classification=serviceable-armed-zero-execution\n'
printf 'trigger_session=none\nsuccessful_mainline_left_running=yes\ncapture=%s\n' "$output"
