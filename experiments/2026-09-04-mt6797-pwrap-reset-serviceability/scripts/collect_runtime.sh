#!/usr/bin/env bash

# Capture one bounded, read-only PWRAP/MT6351/eMMC serviceability frame.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly INSTALLED_FULL_SHA256=5c7429b297c718f5af61367588975e292a8c239854ffd5ba527eb86da1e4a5a6
readonly REMOTE_SHA256=bfa7b11a355263f181285b12d99a07c1ca71ac6b8f13570730da7783937e9fe4
readonly CLASSIFIER_SHA256=5f781b183dba0f053e55acc28dbb0edb21e18c18735de101f599d486b8696455
readonly COMMAND_MARKER=__GEMINI_PWRAP_SERVICEABILITY_SCRIPT__

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
recovery_boot_id=
installed_full_sha256=
output=
while (($#)); do
	case "$1" in
	--recovery-boot-id|--installed-full-sha256|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--recovery-boot-id) recovery_boot_id=$2 ;;
		--installed-full-sha256) installed_full_sha256=$2 ;;
		--output) output=$2 ;;
		esac
		shift 2
		;;
	*) die "usage: $0 --recovery-boot-id UUID --installed-full-sha256 SHA256 --output artifacts/runtime-captures/pwrap-reset-serviceability-attempt-1" ;;
	esac
done
[[ "$recovery_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'recovery boot ID is missing or malformed'
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'installed checksum is not the exact candidate'
[[ -n "$output" ]] || die '--output is required'

for command in awk basename cat chmod date dirname git grep ifconfig mkdir mktemp \
	mv nc netstat python3 rm route sed sha256sum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
remote="$script_dir/remote_observe.sh"
classifier="$script_dir/classify_observation.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly script_dir repo_root remote classifier identity

require_sha256() {
	local path=$1 expected=$2 actual
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	actual=$(sha256sum "$path" | awk '{print $1}')
	[[ "$actual" == "$expected" ]] || die "source checksum mismatch: $path"
}
require_sha256 "$remote" "$REMOTE_SHA256"
require_sha256 "$classifier" "$CLASSIFIER_SHA256"
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'private Gemini SSH key is absent or unsafe'

case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
[[ "$(dirname -- "$output")" == "$private_root" ]] || die '--output must be one direct child of artifacts/runtime-captures/'
[[ "$(basename -- "$output")" == pwrap-reset-serviceability-attempt-1 ]] || die 'output directory identity changed'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
mkdir -m 0700 "$output"
output=$(cd -- "$output" && pwd -P)
readonly private_root output

events="$output/observer-events.txt"
frame="$output/observation.txt"
classification="$output/classification.txt"
readonly events frame classification
command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-pwrap-observer.XXXXXXXX")
cleanup() { rm -f -- "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
{
	printf "/bin/busybox sh <<'%s'\n" "$COMMAND_MARKER"
	sed 's/\r$//' "$remote"
	printf '%s\nexit\n' "$COMMAND_MARKER"
} >"$command_file"
chmod 0600 "$command_file"
printf 'observer=armed\nrecovery_boot_id=%s\ninstalled_full_sha256=%s\narmed_utc=%s\n' \
	"$recovery_boot_id" "$installed_full_sha256" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$events"

ssh_command=(ssh -o BatchMode=yes -o ConnectTimeout=2 -o IdentitiesOnly=yes \
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity")
interface=
mac=
for ((attempt=0; attempt<600; attempt++)); do
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		candidate_mac=$(ifconfig "$candidate" 2>/dev/null | awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}') || true
		case "$candidate_mac" in "$HOST_MAC_82"|"$HOST_MAC_84") ;; *) continue ;; esac
		ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {count++} END {exit count != 1}' || continue
		route_interface=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; count++} END {exit count != 1}') || true
		if [[ -z "$route_interface" ]]; then
			route_interface=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" '$1 == "10.15.19/24" && $4 == interface {print $4; count++} END {exit count != 1}') || true
		fi
		[[ "$route_interface" == "$candidate" ]] || continue
		interface=$candidate
		mac=$candidate_mac
		break 2
	done
	if ((attempt % 5 == 0)); then
		# shellcheck disable=SC2016
		gemian=$("${ssh_command[@]}" gemini@"$GEMIAN_ADDRESS" 'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' 2>/dev/null || true)
		if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ && "${BASH_REMATCH[1]}" != "$recovery_boot_id" ]]; then
			printf 'classification=no-mainline-usb-before-changed-Gemian-return\ngemian_boot_id=%s\n' "${BASH_REMATCH[1]}" >>"$events"
			(cd "$output" && sha256sum observer-events.txt >SHA256SUMS)
			exit 3
		fi
	fi
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"
printf 'netcat_sessions=1 transport=bounded-heredoc access=read-only utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$events"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 35 "$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$frame" 2>&1
nc_rc=$?
set -e
chmod 0600 "$frame"
grep -Fq __GEMINI_PWRAP_SERVICEABILITY_BEGIN__ "$frame" || die "observation frame did not begin rc=$nc_rc"
grep -Fq __GEMINI_PWRAP_SERVICEABILITY_END__ "$frame" || die "observation frame did not complete rc=$nc_rc"
python3 "$classifier" "$frame" --recovery-boot-id "$recovery_boot_id" >"$classification"
grep -Fqx 'classification=pwrap-reset-serviceability-pass' "$classification" || die 'observation frame rejected'
printf 'netcat_complete=yes status=%s\ntrigger_session=none\nload_session=none\n' "$nc_rc" >>"$events"
printf 'native_reboot_command_sent=no\nsuccessful_mainline_left_running=yes\n' >>"$events"
(cd "$output" && sha256sum classification.txt observer-events.txt observation.txt >SHA256SUMS)
chmod 0600 "$output"/*
printf 'result=pass\noutput=%s\n' "$output"
cat "$classification"
