#!/usr/bin/env bash

# Capture one read-only pristine frame over the direct Gemini USB link.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly WAIT_SECONDS=300
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly REMOTE_SHA256=71ea6e7c30c0874a002b05495071b3979d63e7a449b8557545ae553561b3d652
readonly VALIDATOR_SHA256=7f86575611c8fcaed0e0f7049f4d14019525d426980f860ece354dfeced49f2b
readonly COMMAND_MARKER=__GEMINI_A72_FREQUENCY_PRETRIGGER_SCRIPT__
readonly EXPECTED_OUTPUT=artifacts/runtime-captures/a72-frequency-thermal-successor-attempt-1

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
deployment_summary=
output=
while (($#)); do
	case "$1" in
	--deployment-summary)
		(($# >= 2)) || die '--deployment-summary requires FILE'
		deployment_summary=$2
		shift 2
		;;
	--output)
		(($# >= 2)) || die '--output requires DIR'
		output=$2
		shift 2
		;;
	*) die "usage: $0 --deployment-summary FILE --output $EXPECTED_OUTPUT" ;;
	esac
done
[[ -n "$deployment_summary" && -n "$output" ]] || die 'both arguments are required'
[[ "$output" == "$EXPECTED_OUTPUT" ]] || die "output must be $EXPECTED_OUTPUT"
for command in awk basename chmod cp date dirname git grep ifconfig mkdir \
	mktemp mv nc netstat python3 rm route sed sha256sum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
remote=$script_dir/remote-production-pretrigger.sh
validator=$script_dir/validate-production-pretrigger.py
for specification in "$remote:$REMOTE_SHA256" "$validator:$VALIDATOR_SHA256"; do
	path=${specification%%:*}
	expected=${specification##*:}
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] ||
		die "source checksum mismatch: $path"
done
[[ -f "$deployment_summary" && ! -L "$deployment_summary" ]] ||
	die 'deployment summary is absent or unsafe'

output=$repo_root/${output#./}
private_root=$repo_root/artifacts/runtime-captures
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode is not 0700'
[[ "$(dirname -- "$output")" == "$private_root" ]] || die 'output escaped private runtime root'
[[ "$(basename -- "$output")" == a72-frequency-thermal-successor-attempt-1 ]] || die 'output identity changed'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
mkdir -m 0700 "$output"
output=$(cd -- "$output" && pwd -P)

events=$output/observer-events.txt
frame=$output/pretrigger.txt
classification=$output/pretrigger-classification.txt
deployment_copy=$output/deployment-summary.txt
probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-pretrigger.XXXXXXXX")
command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-pretrigger-command.XXXXXXXX")
cleanup() { rm -f -- "${probe:-}" "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
cp "$deployment_summary" "$deployment_copy"
chmod 0600 "$deployment_copy"
sed 's/\r$//' "$remote" >"$probe"
chmod 0600 "$probe"
grep -Fq "$COMMAND_MARKER" "$probe" && die 'command marker occurs in remote probe'
{
	printf "/bin/busybox sh <<'%s'\n" "$COMMAND_MARKER"
	sed 's/\r$//' "$probe"
	printf '%s\nexit\n' "$COMMAND_MARKER"
} >"$command_file"
chmod 0600 "$command_file"
printf 'observer=armed\narmed_utc=%s\naccess=read-only\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$events"

interface=
mac=
for ((attempt=0; attempt<WAIT_SECONDS; attempt++)); do
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		candidate_mac=$(ifconfig "$candidate" 2>/dev/null | \
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}') || true
		case "$candidate_mac" in "$HOST_MAC_82"|"$HOST_MAC_84") ;; *) continue ;; esac
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
	sleep 1
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface did not appear'
printf 'exact_interface_utc=%s interface=%s mac=%s\n' \
	"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >>"$events"
printf 'netcat_sessions=1 transport=bounded-heredoc access=read-only\n' >>"$events"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 45 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$frame" 2>&1
nc_rc=$?
set -e
chmod 0600 "$frame"
if ! grep -Fq __A72_FREQUENCY_THERMAL_PRETRIGGER_BEGIN__ "$frame" ||
	! grep -Fq __A72_FREQUENCY_THERMAL_PRETRIGGER_END__ "$frame"; then
	die "pre-trigger frame did not complete rc=$nc_rc"
fi
set +e
python3 "$validator" "$frame" --deployment-summary "$deployment_copy" >"$classification"
validator_rc=$?
set -e
[[ -s "$classification" ]] || die "pre-trigger validator produced no classification rc=$validator_rc"
printf 'netcat_complete=yes status=%s\ntrigger_session=none\n' "$nc_rc" >>"$events"
printf 'successful_mainline_left_running=yes\nnative_reboot_command_sent=no\n' >>"$events"
(cd "$output" && sha256sum deployment-summary.txt observer-events.txt \
	pretrigger-classification.txt pretrigger.txt >SHA256SUMS)
chmod 0600 "$output"/*
cleanup
trap - EXIT HUP INT TERM
if ((validator_rc != 0)); then
	cat "$classification"
	printf 'trigger_session=none\nsuccessful_mainline_left_running=yes\ncapture=%s\n' "$output"
	exit "$validator_rc"
fi
grep -Fqx 'pretrigger_classification=serviceable-pristine-thermal-frequency-ready' "$classification" ||
	die 'pre-trigger validator returned success without the ready classification'
printf 'pretrigger_classification=serviceable-pristine-thermal-frequency-ready\n'
printf 'trigger_session=none\nsuccessful_mainline_left_running=yes\ncapture=%s\n' "$output"
