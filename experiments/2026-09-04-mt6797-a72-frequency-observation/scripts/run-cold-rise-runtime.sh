#!/usr/bin/env bash

# SPDX-License-Identifier: MIT
# Execute the single cold-boot comparison transaction.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly BUILDER_SHA256=241854bde76396d2713a7cc5a75ea53f7e56fa1b143a3a2278c3b7f64fff52eb
readonly CLASSIFIER_SHA256=b186b6c1cf83d7757bbe401036d4660d950a25dd59e47aa71515dfb8b3c4f224
readonly COMMAND_MARKER=__GEMINI_A72_FREQUENCY_RUNTIME_SCRIPT__
readonly EXPECTED_CAPTURE=artifacts/runtime-captures/a72-frequency-thermal-cold-rise-1

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
capture=
while (($#)); do
	case "$1" in
	--capture)
		(($# >= 2)) || die '--capture requires DIR'
		capture=$2
		shift 2
		;;
	*) die "usage: $0 --capture $EXPECTED_CAPTURE" ;;
	esac
done
[[ "$capture" == "$EXPECTED_CAPTURE" ]] || die "capture must be $EXPECTED_CAPTURE"
for command in awk chmod date dirname grep ifconfig mktemp nc netstat python3 \
	rm route sed sha256sum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
builder=$script_dir/build-production-runtime.sh
classifier=$script_dir/classify-production-runtime.py
for specification in "$builder:$BUILDER_SHA256" "$classifier:$CLASSIFIER_SHA256"; do
	path=${specification%%:*}
	expected=${specification##*:}
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] ||
		die "source checksum mismatch: $path"
done
capture=$repo_root/${capture#./}
[[ -d "$capture" && ! -L "$capture" && "$(stat -f '%Lp' "$capture")" == 700 ]] ||
	die 'capture directory is absent or unsafe'
pretrigger=$capture/pretrigger-classification.txt
sums=$capture/SHA256SUMS
[[ -f "$pretrigger" && -f "$sums" && ! -L "$pretrigger" && ! -L "$sums" ]] ||
	die 'validated pre-trigger evidence is absent'
(cd "$capture" && sha256sum -c SHA256SUMS >/dev/null) || die 'pre-trigger evidence checksum failed'
grep -Fqx 'pretrigger_classification=serviceable-pristine-thermal-frequency-ready' "$pretrigger" ||
	die 'pre-trigger was not accepted'
boot_id=$(awk -F= '$1 == "boot_id" {print $2; count++} END {exit count != 1}' "$pretrigger") ||
	die 'pre-trigger boot ID is absent or duplicated'
for path in runtime.txt runtime-classification.txt runtime-events.txt; do
	[[ ! -e "$capture/$path" && ! -L "$capture/$path" ]] || die "refusing to overwrite $path"
done

python3 "$script_dir/compare-cold-rise.py" gate --capture "$capture"

remote=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-runtime.XXXXXXXX")
command_file=
cleanup() { rm -f -- "${remote:-}" "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-runtime-command.XXXXXXXX")
"$builder" --boot-id "$boot_id" >"$remote"
sh -n "$remote"
grep -Fq "$COMMAND_MARKER" "$remote" && die 'command marker occurs in runtime script'
{
	printf "/bin/busybox sh <<'%s'\n" "$COMMAND_MARKER"
	sed 's/\r$//' "$remote"
	printf '%s\nexit\n' "$COMMAND_MARKER"
} >"$command_file"
chmod 0600 "$command_file"

interface=
mac=
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
	break
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface is unavailable'
events=$capture/runtime-events.txt
transcript=$capture/runtime.txt
classification=$capture/runtime-classification.txt
printf 'runtime=armed\nboot_id=%s\narmed_utc=%s\ninterface=%s\nmac=%s\n' \
	"$boot_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$interface" "$mac" >"$events"
printf 'netcat_sessions=1\nretries=0\n' >>"$events"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 120 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$transcript" 2>&1
nc_rc=$?
set -e
chmod 0600 "$transcript"
printf 'netcat_complete=yes status=%s\n' "$nc_rc" >>"$events"
set +e
python3 "$classifier" "$transcript" --boot-id "$boot_id" >"$classification"
classifier_rc=$?
set -e
[[ -s "$classification" ]] || die "runtime classifier produced no result rc=$classifier_rc"
if ((classifier_rc == 0)); then
	grep -Fqx 'runtime_classification=stage18-thermal-frequency-bounded-load-pass' "$classification" ||
		die 'runtime classifier returned success without the pass classification'
	classification_result=pass
else
	classification_result=rejected
fi
printf 'classification=%s\nnative_reboot_command_sent=no\ndevice_left_running=yes\n' \
	"$classification_result" >>"$events"
(cd "$capture" && sha256sum deployment-summary.txt observer-events.txt \
	pretrigger-classification.txt pretrigger.txt runtime-classification.txt \
	runtime-events.txt runtime.txt >SHA256SUMS)
chmod 0600 "$capture"/*
cleanup
trap - EXIT HUP INT TERM
if ((classifier_rc != 0)); then
	cat "$classification"
	printf 'native_reboot_command_sent=no\ncapture=%s\n' "$capture"
	exit "$classifier_rc"
fi
set +e
python3 "$script_dir/compare-cold-rise.py" compare --capture "$capture" >"$capture/cold-rise-comparison.txt"
comparison_rc=$?
set -e
(cd "$capture" && sha256sum cold-rise-comparison.txt >>SHA256SUMS)
cat "$capture/cold-rise-comparison.txt"
((comparison_rc == 0)) || exit "$comparison_rc"
printf 'retries=0\nnative_reboot_command_sent=no\ncapture=%s\n' "$capture"
