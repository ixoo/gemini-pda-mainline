#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly HOST_NETMASK=0xffffff00
readonly DEVICE_ADDRESS=10.15.19.82

die() {
	last_detail=$*
	printf 'error: %s\n' "$*" >&2
	exit 2
}

usage() {
	cat <<'EOF'
usage: collect-cycle.sh --output DIR [--wait-seconds N] [--configure-address]

Wait for the exact Gemini USB Ethernet interface, validate its unique fixed
MAC/address/route, and invoke Candidate AF's read-only runtime collector once.
DIR must be one new direct child of artifacts/runtime-captures/. If requested,
--configure-address may add only 10.15.19.1/24 to the exact-MAC interface via
passwordless sudo. The address is retained until evidence recovery is done.
EOF
}

output=
wait_seconds=600
configure_address=0
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires DIR'
		[[ -z "$output" ]] || die '--output was provided more than once'
		output=$2
		shift 2
		;;
	--wait-seconds)
		(($# >= 2)) || die '--wait-seconds requires N'
		wait_seconds=$2
		shift 2
		;;
	--configure-address)
		configure_address=1
		shift
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

[[ -n "$output" ]] || {
	usage >&2
	die '--output is required'
}
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
[[ "$output" != *$'\n'* ]] || die '--output must be a single-line path'

for command in awk basename chmod date dirname git grep ifconfig ioreg mkdir mv \
	ping route shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
readonly script_dir repo_root collector
[[ -x "$collector" && ! -L "$collector" ]] || die 'AF runtime collector is absent or unsafe'

private_root="$repo_root/artifacts/runtime-captures"
if [[ ! -e "$private_root" ]]; then
	mkdir -m 0700 "$private_root"
fi
[[ -d "$private_root" && ! -L "$private_root" ]] || \
	die 'private runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$(stat -f '%Lp' "$private_root")" == 700 ]] || \
	die 'private runtime-capture root mode is not 0700'
readonly private_root

case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be one direct child of artifacts/runtime-captures/'
output_name="$(basename -- "$output")"
[[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || \
	die '--output must have a simple directory name'
git -C "$repo_root" check-ignore -q -- "$output" || \
	die '--output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
mkdir -m 0700 "$output"
output="$(cd -- "$output" && pwd -P)"
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die 'canonical output escaped the private runtime-capture root'
readonly output

events="$output/events.txt"
status="$output/status.env"
capture="$output/runtime.txt"
collector_stdout="$output/collector.stdout"
collector_stderr="$output/collector.stderr"
readonly events status capture collector_stdout collector_stderr
: >"$events"
chmod 0600 "$events"

phase=initialized
last_detail=none
interface=unavailable
mac=unavailable
route_interface=unavailable
address_added=no
usb_marker=unavailable
collector_invocations=0
collector_rc=not-run
finalized=0
started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ready_utc=unavailable
completed_utc=unavailable

file_size() {
	stat -f '%z' "$1"
}

capture_sha256() {
	shasum -a 256 "$1" | awk '{ print $1 }'
}

log_event() {
	printf '%s phase=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$phase" "$*" \
		>>"$events"
}

write_status() {
	local result=$1
	local code=$2
	local raw_bytes=absent
	local raw_sha256=absent
	local temporary="$status.partial"
	if [[ -f "$capture" && ! -L "$capture" ]]; then
		raw_bytes="$(file_size "$capture" 2>/dev/null || printf unavailable)"
		raw_sha256="$(capture_sha256 "$capture" 2>/dev/null || printf unavailable)"
	fi
	{
		printf 'experiment=2026-07-22-cortex-a72-observer-initcall-diagnostic\n'
		printf 'candidate_label=AF\n'
		printf 'result=%s\nexit_code=%s\nphase=%s\n' "$result" "$code" "$phase"
		printf 'started_utc=%s\nready_utc=%s\ncompleted_utc=%s\n' \
			"$started_utc" "$ready_utc" "$completed_utc"
		printf 'wait_seconds=%s\ninterface=%s\nmac=%s\n' \
			"$wait_seconds" "$interface" "$mac"
		printf 'host_address=%s/24\naddress_added=%s\n' "$HOST_ADDRESS" "$address_added"
		printf 'route_interface=%s\ndevice_endpoint=%s:2323\n' \
			"$route_interface" "$DEVICE_ADDRESS"
		printf 'usb_serial_marker=%s\ncollector_invocations=%s\ncollector_rc=%s\n' \
			"$usb_marker" "$collector_invocations" "$collector_rc"
		printf 'runtime_capture_bytes=%s\nruntime_capture_sha256=%s\n' \
			"$raw_bytes" "$raw_sha256"
		printf 'last_detail=%s\n' "$last_detail"
		printf 'device_explicit_write_operations=none\n'
		printf 'host_interface_address_retained=%s\n' "$address_added"
	} >"$temporary"
	chmod 0600 "$temporary"
	mv "$temporary" "$status"
}

# ShellCheck does not follow EXIT-trap callbacks when proving reachability.
# shellcheck disable=SC2317
on_exit() {
	local code=$?
	if ((finalized == 0)); then
		set +e
		completed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
		write_status failed "$code"
	fi
}
trap on_exit EXIT

ifconfig -a >"$output/ifconfig-before.txt"
chmod 0600 "$output/ifconfig-before.txt"
ioreg -p IOUSB -w0 -l >"$output/ioreg-before.txt"
chmod 0600 "$output/ioreg-before.txt"

discover_exact_interfaces() {
	local candidate_interface candidate_mac
	for candidate_interface in $(ifconfig -l); do
		[[ "$candidate_interface" =~ ^[A-Za-z0-9]+$ ]] || continue
		candidate_mac="$(ifconfig "$candidate_interface" 2>/dev/null | \
			awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
		[[ "$candidate_mac" != "$HOST_MAC" ]] || printf '%s\n' "$candidate_interface"
	done
}

interfaces_with_host_address() {
	local candidate_interface
	for candidate_interface in $(ifconfig -l); do
		[[ "$candidate_interface" =~ ^[A-Za-z0-9]+$ ]] || continue
		if ifconfig "$candidate_interface" 2>/dev/null | \
			awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address { found = 1 } END { exit !found }'; then
			printf '%s\n' "$candidate_interface"
		fi
	done
}

interface_has_exact_address() {
	ifconfig "$1" 2>/dev/null | awk -v address="$HOST_ADDRESS" -v mask="$HOST_NETMASK" \
		'$1 == "inet" && $2 == address && $3 == "netmask" && $4 == mask { found = 1 } END { exit !found }'
}

route_for_device() {
	route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
		awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }'
}

deadline_epoch=$(( $(date +%s) + wait_seconds ))
last_wait_state=
phase=waiting-for-exact-mac
log_event "deadline_seconds=$wait_seconds expected_mac=$HOST_MAC"

while (( $(date +%s) < deadline_epoch )); do
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	if ((match_count > 1)); then
		die "more than one interface has the exact Gemini USB MAC: $matches"
	fi
	if ((match_count == 0)); then
		if [[ "$last_wait_state" != mac-absent ]]; then
			last_wait_state='mac-absent'
			log_event 'exact_mac_interface=absent'
		fi
		sleep 1
		continue
	fi

	interface=$matches
	[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || die 'resolved Gemini interface name is unsafe'
	mac="$(ifconfig "$interface" 2>/dev/null | \
		awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
	if [[ "$mac" != "$HOST_MAC" ]]; then
		last_wait_state='mac-flapped'
		log_event "exact_mac_interface_flapped interface=$interface"
		sleep 1
		continue
	fi

	address_interfaces="$(interfaces_with_host_address)"
	address_count="$(printf '%s\n' "$address_interfaces" | \
		awk 'NF { count++ } END { print count + 0 }')"
	if ((address_count > 1)) || \
		((address_count == 1)) && [[ "$address_interfaces" != "$interface" ]]; then
		die "host USB address exists on an unexpected interface: ${address_interfaces:-none}"
	fi

	if ! interface_has_exact_address "$interface"; then
		if ((configure_address == 0)); then
			if [[ "$last_wait_state" != address-absent ]]; then
				last_wait_state=address-absent
				log_event "interface=$interface exact_address=absent"
			fi
			sleep 1
			continue
		fi
		phase=configuring-host-address
		sudo -n ifconfig "$interface" up || \
			die 'passwordless sudo cannot bring up the exact Gemini interface'
		sudo -n ifconfig "$interface" alias "$HOST_ADDRESS" netmask 255.255.255.0 || \
			die 'passwordless sudo cannot add the exact Gemini host address'
		address_added=yes
		log_event "interface=$interface address=$HOST_ADDRESS/24 added=yes"
	fi

	interface_has_exact_address "$interface" || \
		die 'exact Gemini interface lacks 10.15.19.1/24 after configuration'
	address_interfaces="$(interfaces_with_host_address)"
	[[ "$address_interfaces" == "$interface" ]] || \
		die '10.15.19.1 is not unique to the exact Gemini interface'
	route_interface="$(route_for_device || true)"
	if [[ "$route_interface" != "$interface" ]]; then
		if [[ "$last_wait_state" != "route-$route_interface" ]]; then
			last_wait_state="route-$route_interface"
			phase=waiting-for-route
			log_event "interface=$interface route_interface=${route_interface:-absent}"
		fi
		sleep 1
		continue
	fi

	phase=waiting-for-bounded-ping
	if ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000 "$DEVICE_ADDRESS" \
		>/dev/null 2>&1; then
		break
	fi
	if [[ "$last_wait_state" != ping-pending ]]; then
		last_wait_state=ping-pending
		log_event "interface=$interface route_interface=$route_interface ping=pending"
	fi
	sleep 1
done

(( $(date +%s) < deadline_epoch )) || \
	die "exact Gemini USB link did not become packet-ready within ${wait_seconds}s"

phase=ready
ready_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ifconfig "$interface" >"$output/ifconfig-ready.txt"
chmod 0600 "$output/ifconfig-ready.txt"
ioreg -p IOUSB -w0 -l >"$output/ioreg-ready.txt"
chmod 0600 "$output/ioreg-ready.txt"
if grep -qF GEMINI_OBSERVABILITY_20260717_L "$output/ioreg-ready.txt"; then
	usb_marker=present
else
	usb_marker=absent
fi
log_event "interface=$interface mac=$mac route_interface=$route_interface ping=passed"

# Give the initramfs listener one bounded scheduling interval after the first
# successful ICMP response. Do not probe port 2323: the AF collector must make
# the sole TCP connection and validate its exact banner and runtime identity.
sleep 1
interface_has_exact_address "$interface" || die 'exact host address disappeared before collection'
[[ "$(discover_exact_interfaces)" == "$interface" ]] || \
	die 'exact Gemini interface identity changed before collection'
[[ "$(route_for_device || true)" == "$interface" ]] || \
	die 'Gemini USB route changed before collection'

phase=collecting-runtime
collector_invocations=1
log_event 'collector_invocations=1 endpoint=10.15.19.82:2323'
set +e
"$collector" --interface "$interface" --output "$capture" \
	>"$collector_stdout" 2>"$collector_stderr"
collector_rc=$?
set -e
chmod 0600 "$collector_stdout" "$collector_stderr"
ifconfig -a >"$output/ifconfig-after.txt"
chmod 0600 "$output/ifconfig-after.txt"
completed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if ((collector_rc == 0)); then
	phase=runtime-validated
	last_detail=exact-af-runtime-validator-passed
	log_event "collector_rc=0 capture_sha256=$(capture_sha256 "$capture")"
	write_status passed 0
	finalized=1
	trap - EXIT
	printf 'result=passed\noutput=%s\ninterface=%s\ncapture=%s\n' \
		"$output" "$interface" "$capture"
	exit 0
fi

phase=runtime-rejected
last_detail='collector-or-validator-failed'
log_event "collector_rc=$collector_rc raw_capture_present=$([[ -f "$capture" ]] && printf yes || printf no)"
write_status failed "$collector_rc"
finalized=1
trap - EXIT
printf 'error: Candidate AF runtime collection failed; evidence=%s\n' "$output" >&2
exit "$collector_rc"
