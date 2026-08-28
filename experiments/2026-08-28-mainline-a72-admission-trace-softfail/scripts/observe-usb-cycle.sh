#!/usr/bin/env bash

# Record sanitized USB-device and exact Gemini-network state transitions at a
# sub-second cadence. This observer never contacts or modifies the device.
set -euo pipefail
export LC_ALL=C
umask 077

readonly GEMINI_LOCATION_ID=17825792
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --output DIR [--duration-seconds N]\n' "$0"; }
for command in awk basename chmod date dirname git ifconfig ioreg mkdir mv \
	rm shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

output=
duration_seconds=300
while (($#)); do
	case "$1" in
	--output) output=${2:-}; shift 2 ;;
	--duration-seconds) duration_seconds=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage >&2; die '--output is required'; }
[[ "$duration_seconds" =~ ^[1-9][0-9]*$ ]] || die 'duration must be positive'

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
private_root="$repo_root/artifacts/runtime-captures"
if [[ ! -e "$private_root" ]]; then
	mkdir -m 0700 "$private_root"
fi
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private runtime root mode changed'
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" ]] ||
	die 'output must be one direct child of artifacts/runtime-captures'
[[ "$(basename -- "$output")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] ||
	die 'output name is unsafe'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -m 0700 "$output"
output=$(cd -- "$output" && pwd -P)

events="$output/events.txt"
status="$output/status.env"
snapshot="$output/.snapshot"
previous="$output/.previous"
: >"$events"
chmod 0600 "$events"
started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
deadline=$(( $(date +%s) + duration_seconds ))
polls=0
transitions=0
last_sha256=none
completed_utc=unavailable
finalized=0

write_status() {
	local result=$1 code=$2 temporary="$status.partial"
	{
		printf 'experiment=2026-08-28-mainline-a72-admission-trace-softfail\n'
		printf 'observer=sanitized-usb-and-exact-network-transitions\n'
		printf 'result=%s\nexit_code=%s\n' "$result" "$code"
		printf 'started_utc=%s\ncompleted_utc=%s\n' "$started_utc" "$completed_utc"
		printf 'duration_seconds=%s\npolls=%s\ntransitions=%s\n' \
			"$duration_seconds" "$polls" "$transitions"
		printf 'gemini_location_id=%s\nlast_snapshot_sha256=%s\n' \
			"$GEMINI_LOCATION_ID" "$last_sha256"
		printf 'device_contact=none\ndevice_storage_writes=none\nreboot_request=none\n'
	} >"$temporary"
	chmod 0600 "$temporary"
	mv "$temporary" "$status"
}

on_exit() {
	local code=$?
	if ((finalized == 0)); then
		set +e
		completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
		write_status interrupted "$code"
		rm -f -- "$snapshot" "$previous"
	fi
}
trap on_exit EXIT HUP INT TERM

capture_snapshot() {
	ioreg -p IOUSB -c IOUSBHostDevice -r -l -w0 2>/dev/null | awk \
		-v wanted="$GEMINI_LOCATION_ID" '
	function clean(value) {
		sub(/^.*= /, "", value)
		gsub(/^"|"$/, "", value)
		return value
	}
	function flush() {
		if (location == wanted) {
			printf "usb=present location_id=%s vendor_id=%s product_id=%s session_id=%s vendor=%s product=%s link_speed=%s\n", location, vendor_id, product_id, session_id, vendor, product, link_speed
			found = 1
		}
		node = location = vendor_id = product_id = session_id = vendor = product = link_speed = "unavailable"
	}
	BEGIN { node = location = vendor_id = product_id = session_id = vendor = product = link_speed = "unavailable" }
	/^[[:space:]]*\+-o / { if (seen) flush(); seen = 1; node = $0; next }
	/"locationID" = / { location = clean($0); next }
	/"idVendor" = / { vendor_id = clean($0); next }
	/"idProduct" = / { product_id = clean($0); next }
	/"sessionID" = / { session_id = clean($0); next }
	/"USB Vendor Name" = / { vendor = clean($0); next }
	/"USB Product Name" = / { product = clean($0); next }
	/"UsbLinkSpeed" = / { link_speed = clean($0); next }
	END { if (seen) flush(); if (!found) print "usb=absent" }
	' >"$snapshot"

	local interface mac exact_count=0
	for interface in $(ifconfig -l); do
		[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || continue
		mac=$(ifconfig "$interface" 2>/dev/null |
			awk '/^[[:space:]]*ether / { print tolower($2); exit }')
		if [[ "$mac" == "$HOST_MAC_82" || "$mac" == "$HOST_MAC_84" ]]; then
			printf 'net=present interface=%s mac=%s inet=%s\n' \
				"$interface" "$mac" \
				"$(ifconfig "$interface" 2>/dev/null | awk '$1 == "inet" { print $2; exit } END { if (!NR) print "unavailable" }')" \
				>>"$snapshot"
			exact_count=$((exact_count + 1))
		fi
	done
	((exact_count <= 1)) || die 'multiple exact Gemini network interfaces found'
	((exact_count == 1)) || printf 'net=absent\n' >>"$snapshot"
}

while (( $(date +%s) < deadline )); do
	polls=$((polls + 1))
	capture_snapshot
	current_sha256=$(shasum -a 256 "$snapshot" | awk '{print $1}')
	if [[ "$current_sha256" != "$last_sha256" ]]; then
		transitions=$((transitions + 1))
		printf 'utc=%s poll=%s transition=%s snapshot_sha256=%s\n' \
			"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$polls" "$transitions" \
			"$current_sha256" >>"$events"
		awk '{print "  " $0}' "$snapshot" >>"$events"
		last_sha256=$current_sha256
		mv "$snapshot" "$previous"
	else
		rm -f -- "$snapshot"
	fi
	sleep 0.25
done
completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
write_status passed 0
rm -f -- "$snapshot" "$previous"
finalized=1
trap - EXIT HUP INT TERM
printf 'result=passed\noutput=%s\npolls=%s\ntransitions=%s\n' \
	"$output" "$polls" "$transitions"
