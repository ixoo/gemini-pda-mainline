#!/usr/bin/env bash

# Bind one collection attempt to a real USB cycle. A reachable exact fixed-MAC
# Gemini link must disappear before reappearing; an initially absent link must
# remain cleanly absent across two observations before its first exact
# appearance. Only then is collect-runtime.sh invoked, exactly once. This
# watcher never reads a device partition and never retries a rejected capture.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly HOST_NETMASK=0xffffff00
readonly DEVICE_ADDRESS=10.15.19.82
readonly INSTALLED_FULL_SHA256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
readonly COLLECTOR_SHA256=5fe46ea345e8ec94ea2253c26e7f359f0ba46fd1e792598086c891806b3617bf

die() {
	last_detail=$*
	printf 'error: %s\n' "$*" >&2
	exit 2
}

usage() {
	cat <<'EOF'
usage: collect-cycle.sh --output DIR --installed-full-sha256 SHA256
       [--wait-seconds N] [--configure-address]

If the exact Gemini USB Ethernet interface is packet-ready at startup, confirm
that it disappears. If it is initially absent, confirm that absence twice.
Then validate its unique fixed MAC/address/route on appearance and invoke
Candidate AI's read-only runtime collector once.
DIR must be one new direct child of artifacts/runtime-captures/. If requested,
--configure-address may add only 10.15.19.1/24 to the exact-MAC interface via
passwordless sudo. The address remains until evidence recovery is complete.
SHA256 must come from the prior verified padded boot2 readback; this watcher
records that caller-supplied attestation and does not read a device partition.
EOF
}

output=
installed_full_sha256=
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
	--installed-full-sha256)
		(($# >= 2)) || die '--installed-full-sha256 requires SHA256'
		[[ -z "$installed_full_sha256" ]] || \
			die '--installed-full-sha256 was provided more than once'
		installed_full_sha256=$2
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

[[ -n "$output" ]] || { usage >&2; die '--output is required'; }
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die '--installed-full-sha256 must be one lowercase SHA-256 value'
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die '--installed-full-sha256 is not Candidate AI'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
[[ "$output" != *$'\n'* ]] || die '--output must be a single-line path'

for command in awk bash basename chmod date dirname git grep ifconfig ioreg mkdir \
	mv ping route shasum sleep stat sudo; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
readonly script_dir repo_root collector
[[ -f "$collector" && ! -L "$collector" ]] || die 'AI runtime collector is absent or unsafe'
collector_sha256="$(shasum -a 256 "$collector" | awk '{ print $1 }')"
[[ "$collector_sha256" == "$COLLECTOR_SHA256" ]] || \
	die 'AI runtime collector source identity changed'
readonly collector_sha256

private_root="$repo_root/artifacts/runtime-captures"
if [[ ! -e "$private_root" ]]; then
	mkdir -m 0700 "$private_root"
fi
[[ -d "$private_root" && ! -L "$private_root" ]] || \
	die 'private runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$(stat -f '%Lp' "$private_root" 2>/dev/null || stat -c '%a' "$private_root")" == 700 ]] || \
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
initial_interface=unavailable
mac=unavailable
route_interface=unavailable
address_added=no
usb_serial_marker=unavailable
collector_invocations=0
collector_rc=not-run
runtime_identity_capture=absent
runtime_subgate=not-run
native_reboot_subgate=not-run
console_subgate=not-observed
oracle=INCONCLUSIVE
preflight_path=unresolved
initial_link_verified=no
initial_absence_confirmed=no
disconnect_observed=no
reappearance_verified=no
finalized=0
started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
initial_ready_utc=unavailable
initial_absence_confirmed_utc=unavailable
disconnect_observed_utc=unavailable
ready_utc=unavailable
completed_utc=unavailable

file_size() {
	stat -f '%z' "$1" 2>/dev/null || stat -c '%s' "$1"
}

capture_sha256() {
	shasum -a 256 "$1" | awk '{ print $1 }'
}

log_event() {
	printf '%s phase=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$phase" "$*" \
		>>"$events"
}

write_status() {
	local operation_status=$1
	local code=$2
	local raw_bytes=absent
	local raw_sha256=absent
	local temporary="$status.partial"
	if [[ -f "$capture" && ! -L "$capture" ]]; then
		raw_bytes="$(file_size "$capture" 2>/dev/null || printf unavailable)"
		raw_sha256="$(capture_sha256 "$capture" 2>/dev/null || printf unavailable)"
	fi
	{
		printf 'experiment=2026-07-22-a72-reject-gate-kernel-split\n'
		printf 'candidate_label=AI\n'
		printf 'operation_status=%s\nexit_code=%s\nphase=%s\n' \
			"$operation_status" "$code" "$phase"
		printf 'oracle=%s\nruntime_subgate=%s\n' "$oracle" "$runtime_subgate"
		printf 'native_reboot_subgate=%s\nconsole_subgate=%s\n' \
			"$native_reboot_subgate" "$console_subgate"
		printf 'started_utc=%s\ninitial_ready_utc=%s\n' \
			"$started_utc" "$initial_ready_utc"
		printf 'initial_absence_confirmed_utc=%s\ndisconnect_observed_utc=%s\n' \
			"$initial_absence_confirmed_utc" "$disconnect_observed_utc"
		printf 'ready_utc=%s\ncompleted_utc=%s\n' "$ready_utc" "$completed_utc"
		printf 'preflight_path=%s\ninitial_link_verified=%s\n' \
			"$preflight_path" "$initial_link_verified"
		printf 'initial_absence_confirmed=%s\ndisconnect_observed=%s\n' \
			"$initial_absence_confirmed" "$disconnect_observed"
		printf 'reappearance_verified=%s\nruntime_identity_capture=%s\n' \
			"$reappearance_verified" "$runtime_identity_capture"
		printf 'wait_seconds=%s\ninitial_interface=%s\ninterface=%s\nmac=%s\n' \
			"$wait_seconds" "$initial_interface" "$interface" "$mac"
		printf 'host_address=%s/24\naddress_added=%s\n' "$HOST_ADDRESS" "$address_added"
		printf 'route_interface=%s\ndevice_endpoint=%s:2323\n' \
			"$route_interface" "$DEVICE_ADDRESS"
		printf 'usb_serial_marker=%s\ncollector_invocations=%s\ncollector_rc=%s\n' \
			"$usb_serial_marker" "$collector_invocations" "$collector_rc"
		printf 'collector_sha256=%s\n' "$collector_sha256"
		printf 'runtime_capture_bytes=%s\nruntime_capture_sha256=%s\n' \
			"$raw_bytes" "$raw_sha256"
		printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
		printf 'installed_full_hash_basis=caller-supplied-prior-full-partition-readback\n'
		printf 'installed_full_hash_reverified_during_collection=no\n'
		printf 'last_detail=%s\n' "$last_detail"
		printf 'device_explicit_write_operations=none\n'
		printf 'host_interface_address_retained=%s\n' "$address_added"
		printf 'visual_only_result=insufficient-for-pass\n'
		printf 'runtime_subgate_basis=exact-usb-runtime-at-45-plus-5-seconds\n'
		printf 'overall_pass_permitted=no\n'
	} >"$temporary"
	chmod 0600 "$temporary"
	mv "$temporary" "$status"
}

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

# shellcheck disable=SC2317
on_signal() {
	local name=$1
	local code=$2
	last_detail="received-signal-$name"
	exit "$code"
}
trap 'on_signal INT 130' INT
trap 'on_signal TERM 143' TERM

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
			awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address { found = 1 } END { exit !found }'; then
			printf '%s\n' "$candidate_interface"
		fi
	done
}

interface_has_exact_address() {
	ifconfig "$1" 2>/dev/null | awk -v address="$HOST_ADDRESS" -v mask="$HOST_NETMASK" \
		'$1 == "inet" && $2 == address && $3 == "netmask" && $4 == mask { found = 1 } END { exit !found }'
}

route_for_device() {
	local route_output
	if ! route_output="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null)"; then
		return 0
	fi
	printf '%s\n' "$route_output" | awk -v target="$DEVICE_ADDRESS" '
		$1 == "route" && $2 == "to:" {
			route_to = $3
			route_to_count++
		}
		$1 == "destination:" {
			destination = $2
			destination_count++
		}
		$1 == "interface:" {
			interface = $2
			interface_count++
		}
		$1 == "flags:" {
			flags = $0
			flags_count++
		}
		END {
			if (route_to_count != 1 || route_to != target ||
			    destination_count > 1 || interface_count != 1 ||
			    flags_count > 1) {
				print "__candidate_ai_route_invalid__"
				exit
			}
			if (destination == "default" ||
			    flags ~ /(^|[<,])GATEWAY([,>]|$)/) {
				exit
			}
			if ((destination_count == 1 &&
			     destination !~ /^10[.]15[.]19[.][0-9]+(\/[0-9]+)?$/) ||
			    interface !~ /^[A-Za-z0-9]+$/) {
				print "__candidate_ai_route_invalid__"
				exit
			}
			print interface
		}'
}

assert_route_parseable() {
	[[ "$1" != __candidate_ai_route_invalid__ ]] || \
		die 'Gemini device route output is malformed or ambiguous'
}

check_unique_host_address() {
	local expected_interface=$1
	local address_interfaces address_count
	address_interfaces="$(interfaces_with_host_address)"
	address_count="$(printf '%s\n' "$address_interfaces" | \
		awk 'NF { count++ } END { print count + 0 }')"
	if ((address_count > 1)) || \
		((address_count == 1)) && [[ "$address_interfaces" != "$expected_interface" ]]; then
		die "host USB address exists on an unexpected interface: ${address_interfaces:-none}"
	fi
	printf '%s\n' "$address_interfaces"
}

configure_exact_address() {
	local expected_interface=$1
	sudo -n ifconfig "$expected_interface" up || \
		die 'passwordless sudo cannot bring up the exact Gemini interface'
	sudo -n ifconfig "$expected_interface" alias "$HOST_ADDRESS" netmask 255.255.255.0 || \
		die 'passwordless sudo cannot add the exact Gemini host address'
	address_added=yes
	log_event "interface=$expected_interface address=$HOST_ADDRESS/24 added=yes"
}

assert_clean_initial_absence() {
	local address_interfaces absent_route
	address_interfaces="$(interfaces_with_host_address)"
	[[ -z "$address_interfaces" ]] || \
		die "exact host address is present without the exact Gemini MAC: $address_interfaces"
	absent_route="$(route_for_device)"
	assert_route_parseable "$absent_route"
	[[ -z "$absent_route" ]] || \
		die "Gemini device route is present without the exact Gemini MAC: $absent_route"
	if ioreg -p IOUSB -w0 -l | grep -qF GEMINI_OBSERVABILITY_20260717_L; then
		die 'exact Gemini USB serial is present without the exact Ethernet MAC'
	fi
}

# The watcher must observe a genuine departure boundary. This prevents an
# already-running candidate from being mistaken for a post-cycle appearance and
# consuming the sole collector invocation. Recovery may begin with no Gemini
# USB Ethernet interface, so two clean initial absences are an equivalent
# boundary.
phase=preflight-existing-link
matches="$(discover_exact_interfaces)"
match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
deadline_epoch=$(( $(date +%s) + wait_seconds ))
case "$match_count" in
0)
	preflight_path=initially-absent
	assert_clean_initial_absence
	log_event 'initial_exact_mac_interface=absent consecutive=1'
	phase=confirming-initial-absence
	sleep 1
	(( $(date +%s) < deadline_epoch )) || \
		die "second initial absence was not observed before the ${wait_seconds}s cycle deadline"
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	((match_count == 0)) || \
		die "exact Gemini interface appeared before two initial absence observations: count=$match_count"
	assert_clean_initial_absence
	initial_absence_confirmed=yes
	initial_absence_confirmed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	log_event 'initial_exact_mac_interface=absent consecutive=2 initial_absence=confirmed'
	;;
1)
	preflight_path=present-then-disconnected
	interface=$matches
	initial_interface=$interface
	[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || die 'resolved Gemini interface name is unsafe'
	mac="$(ifconfig "$interface" 2>/dev/null | \
		awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
	[[ "$mac" == "$HOST_MAC" ]] || die 'pre-cycle exact Gemini MAC changed'
	check_unique_host_address "$interface" >/dev/null
	if ! interface_has_exact_address "$interface"; then
		((configure_address == 1)) || die 'pre-cycle exact Gemini host address is absent'
		phase=configuring-host-address
		configure_exact_address "$interface"
	fi
	[[ "$(check_unique_host_address "$interface")" == "$interface" ]] || \
		die 'pre-cycle host address is not unique to the exact Gemini interface'
	route_interface="$(route_for_device)"
	assert_route_parseable "$route_interface"
	[[ "$route_interface" == "$interface" ]] || \
		die 'pre-cycle Gemini USB route is not the exact interface'
	phase=preflight-bounded-ping
	ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000 "$DEVICE_ADDRESS" \
		>/dev/null 2>&1 || die 'pre-cycle exact Gemini USB link is not packet-ready'
	initial_link_verified=yes
	initial_ready_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	log_event "initial_link=verified interface=$interface mac=$mac route_interface=$route_interface"

	phase=waiting-for-disconnect
	log_event "deadline_seconds=$wait_seconds expected_mac=$HOST_MAC cycle_disconnect=pending"
	absence_count=0
	while (( $(date +%s) < deadline_epoch )); do
		matches="$(discover_exact_interfaces)"
		match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
		if ((match_count > 1)); then
			die "more than one interface has the exact Gemini USB MAC: $matches"
		fi
		if ((match_count == 0)); then
			absence_count=$((absence_count + 1))
			log_event "exact_mac_interface=absent consecutive=$absence_count"
			if ((absence_count >= 2)); then
				disconnect_observed=yes
				disconnect_observed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
				log_event 'cycle_disconnect=confirmed'
				break
			fi
		else
			absence_count=0
		fi
		sleep 1
	done
	[[ "$disconnect_observed" == yes ]] || \
		die "exact Gemini USB link did not disappear before the ${wait_seconds}s cycle deadline"
	;;
*)
	die "pre-cycle exact Gemini USB interface count is $match_count, expected 0 or 1"
	;;
esac

phase=waiting-for-reappearance
last_wait_state=
reappearance_ready=0
while (( $(date +%s) < deadline_epoch )); do
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	if ((match_count > 1)); then
		die "more than one interface has the exact Gemini USB MAC after disconnect: $matches"
	fi
	if ((match_count == 0)); then
		if [[ "$last_wait_state" != mac-absent ]]; then
			last_wait_state='mac-absent'
			log_event 'post-cycle exact_mac_interface=absent'
		fi
		sleep 1
		continue
	fi

	interface=$matches
	[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || die 'reappeared Gemini interface name is unsafe'
	mac="$(ifconfig "$interface" 2>/dev/null | \
		awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
	[[ "$mac" == "$HOST_MAC" ]] || die 'reappeared Gemini MAC changed'
	check_unique_host_address "$interface" >/dev/null
	if ! interface_has_exact_address "$interface"; then
		if ((configure_address == 0)); then
			if [[ "$last_wait_state" != address-absent ]]; then
				last_wait_state=address-absent
				log_event "interface=$interface post_cycle_exact_address=absent"
			fi
			sleep 1
			continue
		fi
		phase=configuring-host-address
		configure_exact_address "$interface"
		phase=waiting-for-reappearance
	fi
	[[ "$(check_unique_host_address "$interface")" == "$interface" ]] || \
		die 'post-cycle host address is not unique to the exact Gemini interface'
	route_interface="$(route_for_device)"
	assert_route_parseable "$route_interface"
	if [[ "$route_interface" != "$interface" ]]; then
		if [[ "$last_wait_state" != "route-$route_interface" ]]; then
			last_wait_state="route-$route_interface"
			log_event "interface=$interface post_cycle_route_interface=${route_interface:-absent}"
		fi
		sleep 1
		continue
	fi
	if ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000 "$DEVICE_ADDRESS" \
		>/dev/null 2>&1; then
		reappearance_ready=1
		break
	fi
	if [[ "$last_wait_state" != ping-pending ]]; then
		last_wait_state=ping-pending
		log_event "interface=$interface post_cycle_ping=pending"
	fi
	sleep 1
done

((reappearance_ready == 1)) || \
	die "exact Gemini USB link did not reappear packet-ready before the ${wait_seconds}s cycle deadline"

phase=ready-after-cycle
reappearance_verified=yes
ready_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ifconfig "$interface" >"$output/ifconfig-ready.txt"
chmod 0600 "$output/ifconfig-ready.txt"
ioreg -p IOUSB -w0 -l >"$output/ioreg-ready.txt"
chmod 0600 "$output/ioreg-ready.txt"
if grep -qF GEMINI_OBSERVABILITY_20260717_L "$output/ioreg-ready.txt"; then
	usb_serial_marker=present
else
	usb_serial_marker=absent
fi
log_event "cycle_reappearance=verified interface=$interface mac=$mac route_interface=$route_interface ping=passed"

# Do not probe port 2323: the collector below must make the sole TCP session.
sleep 1
interface_has_exact_address "$interface" || die 'exact host address disappeared before collection'
[[ "$(discover_exact_interfaces)" == "$interface" ]] || \
	die 'exact Gemini interface identity changed before collection'
route_interface="$(route_for_device)"
assert_route_parseable "$route_interface"
[[ "$route_interface" == "$interface" ]] || \
	die 'Gemini USB route changed before collection'

phase=collecting-runtime
collector_invocations=1
runtime_subgate=in-progress
oracle=PENDING_RUNTIME_EVIDENCE_REVIEW
log_event 'collector_invocations=1 endpoint=10.15.19.82:2323'
set +e
bash "$collector" --interface "$interface" --output "$capture" \
	--installed-full-sha256 "$installed_full_sha256" \
	>"$collector_stdout" 2>"$collector_stderr"
collector_rc=$?
set -e
chmod 0600 "$collector_stdout" "$collector_stderr"
ifconfig -a >"$output/ifconfig-after.txt"
chmod 0600 "$output/ifconfig-after.txt"
completed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if ((collector_rc == 0)); then
	phase=runtime-validated
	runtime_identity_capture=complete
	runtime_subgate=passed
	oracle=PENDING_NATIVE_REBOOT_AND_CONSOLE
	last_detail=exact-ai-runtime-validator-passed
	log_event "collector_rc=0 capture_sha256=$(capture_sha256 "$capture")"
	write_status completed 0
	finalized=1
	trap - EXIT
	printf 'operation_status=completed\nruntime_subgate=passed\n'
	printf 'oracle=PENDING_NATIVE_REBOOT_AND_CONSOLE\n'
	printf 'output=%s\ninterface=%s\ncapture=%s\n' "$output" "$interface" "$capture"
	exit 0
fi

phase=runtime-rejected
runtime_subgate=rejected
if [[ -f "$capture" ]] && grep -aFq '__AI_IDENTITY_BEGIN__' "$capture" && \
	grep -aFq '__AI_IDENTITY_END__' "$capture"; then
	runtime_identity_capture=complete
	oracle=REQUIRES_RUNTIME_EVIDENCE_REVIEW
else
	runtime_identity_capture=absent-or-incomplete
	oracle=INCONCLUSIVE
fi
last_detail='collector-or-validator-failed'
log_event "collector_rc=$collector_rc raw_capture_present=$([[ -f "$capture" ]] && printf yes || printf no)"
write_status failed "$collector_rc"
finalized=1
trap - EXIT
printf 'error: Candidate AI runtime collection failed; evidence=%s\n' "$output" >&2
exit "$collector_rc"
