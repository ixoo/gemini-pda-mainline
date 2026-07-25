#!/usr/bin/env bash

# Bind Candidate AJ's existing fixed-MAC cycle watcher to the exact Gemian
# source target on which AJ was installed.  The source target must first be
# authenticated in its exact recovery state, then fail two consecutive SSH
# probes while the candidate MAC, address, and route remain absent.  Only then
# may the source-pinned collect-cycle.sh begin its own one-shot USB watch.
#
# This wrapper never reads a device partition, requests a reboot, or stores a
# plaintext USB/device serial.  Raw ioreg output is reduced in memory to the
# candidate's non-unit-unique marker state before the underlying watcher sees
# or persists it.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly RECOVERY_KERNEL=3.18.41+
readonly RECOVERY_ARCH=aarch64
readonly RECOVERY_ROOT=/dev/mmcblk0p29
readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly INSTALLED_FULL_SHA256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
readonly CYCLE_SHA256=20799b990dd225b1ca5400a555290b959e305fecfcda312335f673953945a6e0
readonly CANDIDATE_AJ_SHA256=77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1
readonly SANITIZER_SHA256=e7f7f2caeda6680fa104a62f7f3f2a65d9f489fc141ca09f80b7372c48362c27

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

usage() {
	cat <<'EOF'
usage: collect-unit-bound-cycle.sh --output DIR --installed-full-sha256 SHA256
       [--wait-seconds N] [--configure-address]

Start while the exact installed Gemini is reachable in Gemian. The wrapper
authenticates gemini@192.168.1.50 as exact Gemian 3.18.41+ on
/dev/mmcblk0p29, requires two consecutive SSH failures before Candidate AJ's
fixed-MAC endpoint appears, and only then invokes the pinned one-shot runtime
watcher. DIR must be a new direct child of artifacts/runtime-captures/.

The total N-second deadline includes the source-disconnect gate and the USB
appearance/runtime handoff. --configure-address retains the underlying
watcher's narrow passwordless-sudo behavior. No plaintext device serial is
printed or stored.
EOF
}

output=
installed_full_sha256=
wait_seconds=1200
configure_address=0
while (($#)); do
	case "$1" in
	--output|--installed-full-sha256|--wait-seconds)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--installed-full-sha256)
			[[ -z "$installed_full_sha256" ]] || die '--installed-full-sha256 duplicated'
			installed_full_sha256=$2
			;;
		--wait-seconds) wait_seconds=$2 ;;
		esac
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
	die '--installed-full-sha256 is not Candidate AJ'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
[[ "$output" != *$'\n'* ]] || die '--output must be a single-line path'

for command in awk bash basename chmod cp date dirname git grep ifconfig kill \
	ln mkdir mktemp mv python3 rm route shasum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
cycle="$script_dir/collect-cycle.sh"
candidate_identity="$script_dir/candidate_aj.py"
sanitizer="$script_dir/sanitize-unit-bound-ioreg.sh"
identity="$repo_root/$IDENTITY_RELATIVE"
readonly script_dir repo_root cycle candidate_identity sanitizer identity

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }

for pin in \
	"$cycle:$CYCLE_SHA256:Candidate AJ cycle watcher" \
	"$candidate_identity:$CANDIDATE_AJ_SHA256:Candidate AJ identity" \
	"$sanitizer:$SANITIZER_SHA256:ioreg sanitizer"; do
	path=${pin%%:*}
	remainder=${pin#*:}
	expected=${remainder%%:*}
	label=${remainder#*:}
	[[ -f "$path" && ! -L "$path" ]] || die "$label is absent or unsafe"
	[[ "$(file_sha256 "$path")" == "$expected" ]] || die "$label source identity changed"
done

pinned_full_sha256="$(python3 - "$candidate_identity" <<'PY'
import importlib.util
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_aj_unit_cycle_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AJ identity module")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AJ production artifact pins are unresolved or invalid'
[[ "$pinned_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die 'Candidate AJ padded identity changed'

[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || \
	die 'exact Gemini SSH identity is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == \
	"$identity" ]] || die 'exact Gemini SSH identity path contains an intermediate symlink'
git -C "$repo_root" check-ignore -q -- "$identity" || \
	die 'exact Gemini SSH identity is not private'
identity_start_sha256="$(file_sha256 "$identity")"
[[ "$identity_start_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'cannot identify exact Gemini SSH private key'
readonly identity_start_sha256

known_hosts_path="${HOME:?HOME is not set}/.ssh/known_hosts"
[[ "$known_hosts_path" == /* && "$known_hosts_path" != *$'\n'* ]] || \
	die 'SSH known-hosts path is unsafe'
[[ -f "$known_hosts_path" && ! -L "$known_hosts_path" ]] || \
	die 'SSH known-hosts database is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$known_hosts_path")" && pwd -P)/$(basename -- "$known_hosts_path")" == \
	"$known_hosts_path" ]] || die 'SSH known-hosts path contains an intermediate symlink'
known_hosts_sha256="$(file_sha256 "$known_hosts_path")"
[[ "$known_hosts_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'cannot identify SSH known-hosts database'
readonly known_hosts_path known_hosts_sha256

real_ioreg="$(command -v ioreg 2>/dev/null || true)"
[[ "$real_ioreg" == /* && "$real_ioreg" != *$'\n'* ]] || \
	die 'real ioreg command did not resolve to one absolute path'
[[ -f "$real_ioreg" && ! -L "$real_ioreg" && -x "$real_ioreg" ]] || \
	die 'real ioreg command is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$real_ioreg")" && pwd -P)/$(basename -- "$real_ioreg")" == \
	"$real_ioreg" ]] || die 'real ioreg command path contains an intermediate symlink'
readonly real_ioreg

private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || \
	die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
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
git -C "$repo_root" check-ignore -q -- "$output" || die '--output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime evidence'
readonly output output_name

assert_live_pins() {
	[[ -f "$cycle" && ! -L "$cycle" && "$(file_sha256 "$cycle")" == "$CYCLE_SHA256" ]] || \
		die 'Candidate AJ cycle watcher changed during the unit-bound gate'
	[[ -f "$candidate_identity" && ! -L "$candidate_identity" && \
		"$(file_sha256 "$candidate_identity")" == "$CANDIDATE_AJ_SHA256" ]] || \
		die 'Candidate AJ identity changed during the unit-bound gate'
	[[ -f "$sanitizer" && ! -L "$sanitizer" && \
		"$(file_sha256 "$sanitizer")" == "$SANITIZER_SHA256" ]] || \
		die 'ioreg sanitizer changed during the unit-bound gate'
	[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 && \
		"$(file_sha256 "$identity")" == "$identity_start_sha256" ]] || \
		die 'exact Gemini SSH private key changed during the unit-bound gate'
	[[ -f "$known_hosts_path" && ! -L "$known_hosts_path" && \
		"$(file_sha256 "$known_hosts_path")" == "$known_hosts_sha256" ]] || \
		die 'SSH known-hosts database changed during the unit-bound gate'
}

discover_exact_interfaces() {
	local candidate_interface candidate_mac interface_list
	interface_list="$(ifconfig -l)" || die 'host interface enumeration failed'
	for candidate_interface in $interface_list; do
		[[ "$candidate_interface" =~ ^[A-Za-z0-9]+$ ]] || \
			die 'host interface enumeration returned an unsafe name'
		candidate_mac="$(ifconfig "$candidate_interface" 2>/dev/null | \
			awk '/^[[:space:]]*ether / { print tolower($2); count++ } END { exit count > 1 }')" || \
			die "host interface $candidate_interface has ambiguous link identity"
		[[ "$candidate_mac" != "$HOST_MAC" ]] || printf '%s\n' "$candidate_interface"
	done
}

interfaces_with_host_address() {
	local candidate_interface interface_list
	interface_list="$(ifconfig -l)" || die 'host interface enumeration failed'
	for candidate_interface in $interface_list; do
		[[ "$candidate_interface" =~ ^[A-Za-z0-9]+$ ]] || \
			die 'host interface enumeration returned an unsafe name'
		if ifconfig "$candidate_interface" 2>/dev/null | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address { found++ } END { exit found != 1 }'; then
			printf '%s\n' "$candidate_interface"
		fi
	done
}

route_for_device() {
	local route_output
	if ! route_output="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null)"; then
		return 0
	fi
	printf '%s\n' "$route_output" | awk -v target="$DEVICE_ADDRESS" '
		$1 == "route" && $2 == "to:" { route_to = $3; route_to_count++ }
		$1 == "destination:" { destination = $2; destination_count++ }
		$1 == "interface:" { interface = $2; interface_count++ }
		$1 == "flags:" { flags = $0; flags_count++ }
		END {
			if (route_to_count != 1 || route_to != target ||
			    destination_count > 1 || interface_count != 1 || flags_count > 1) {
				print "__candidate_aj_unit_route_invalid__"
				exit
			}
			if (destination == "default" || flags ~ /(^|[<,])GATEWAY([,>]|$)/) exit
			if ((destination_count == 1 &&
			     destination !~ /^10[.]15[.]19[.][0-9]+(\/[0-9]+)?$/) ||
			    interface !~ /^[A-Za-z0-9]+$/) {
				print "__candidate_aj_unit_route_invalid__"
				exit
			}
			print interface
		}'
}

assert_candidate_absent() {
	local matches match_count address_interfaces route_interface
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	((match_count == 0)) || \
		die "Candidate AJ fixed MAC is present before the exact source disconnect: ${matches//$'\n'/,}"
	address_interfaces="$(interfaces_with_host_address)"
	[[ -z "$address_interfaces" ]] || \
		die "stale Candidate AJ host address exists before source disconnect: ${address_interfaces//$'\n'/,}"
	route_interface="$(route_for_device)"
	[[ "$route_interface" != __candidate_aj_unit_route_invalid__ ]] || \
		die 'Candidate AJ device route is malformed or ambiguous before source disconnect'
	[[ -z "$route_interface" ]] || \
		die "stale Candidate AJ device route exists before source disconnect: $route_interface"
}

ssh_options=(
	-F /dev/null -o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=5
	-o ServerAliveCountMax=3 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -o UserKnownHostsFile="$known_hosts_path"
	-o GlobalKnownHostsFile=/dev/null -i "$identity"
)
readonly ssh_options

# shellcheck disable=SC2016
remote_state_script='set -eu
test "$(id -u)" = 0
printf "kernel=%s\n" "$(uname -r)"
printf "architecture=%s\n" "$(uname -m)"
printf "root_source=%s\n" "$(findmnt -n -o SOURCE /)"
printf "boot_id=%s\n" "$(cat /proc/sys/kernel/random/boot_id)"'
readonly remote_state_script

remote_state() {
	printf '%s\n' "$remote_state_script" | \
		ssh "${ssh_options[@]}" "$TARGET" 'sudo -n -- /bin/sh -s'
}

state_value() {
	local key=$1 text=$2
	printf '%s\n' "$text" | awk -F= -v wanted="$key" \
		'$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }'
}

state_is_exact_source() {
	local text=$1 boot_id
	[[ "$(printf '%s\n' "$text" | awk 'END { print NR + 0 }')" == 4 ]] || return 1
	[[ "$(state_value kernel "$text" 2>/dev/null || true)" == "$RECOVERY_KERNEL" ]] || return 1
	[[ "$(state_value architecture "$text" 2>/dev/null || true)" == "$RECOVERY_ARCH" ]] || return 1
	[[ "$(state_value root_source "$text" 2>/dev/null || true)" == "$RECOVERY_ROOT" ]] || return 1
	boot_id="$(state_value boot_id "$text" 2>/dev/null || true)"
	[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
}

assert_live_pins
assert_candidate_absent
initial_state="$(remote_state)" || die 'exact installed Gemian target is not reachable at startup'
state_is_exact_source "$initial_state" || die 'reachable source target is not exact Gemian recovery'
initial_boot_id="$(state_value boot_id "$initial_state")"
assert_candidate_absent
confirmed_state="$(remote_state)" || die 'exact installed Gemian target failed confirmation'
[[ "$confirmed_state" == "$initial_state" ]] || die 'exact Gemian source state changed during confirmation'
assert_candidate_absent

source_verified_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
deadline_epoch=$(( $(date +%s) + wait_seconds ))
disconnect_failures=0
while (( $(date +%s) < deadline_epoch )); do
	assert_live_pins
	assert_candidate_absent
	set +e
	candidate_state="$(remote_state 2>/dev/null)"
	state_rc=$?
	set -e
	assert_live_pins
	assert_candidate_absent
	if ((state_rc == 0)); then
		state_is_exact_source "$candidate_state" || \
			die 'source target became reachable in a non-exact recovery state'
		[[ "$(state_value boot_id "$candidate_state")" == "$initial_boot_id" ]] || \
			die 'source target boot ID changed before the disconnect boundary'
		disconnect_failures=0
	else
		disconnect_failures=$((disconnect_failures + 1))
		if ((disconnect_failures >= 2)); then
			break
		fi
	fi
	sleep 1
done
((disconnect_failures >= 2)) || \
	die "exact installed Gemian target did not produce two SSH failures before ${wait_seconds}s deadline"
disconnect_confirmed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
disconnect_confirmed_epoch="$(date +%s)"
assert_live_pins
assert_candidate_absent

remaining_seconds=$((deadline_epoch - $(date +%s)))
((remaining_seconds >= 3)) || die 'too little cycle deadline remains after exact source disconnect'

binding_staging="$(mktemp "$private_root/.candidate-aj-unit-binding.XXXXXX")"
shim_dir="$(mktemp -d "$private_root/.candidate-aj-unit-ioreg.XXXXXX")"
child_pid=
binding_published=no
cleanup() {
	local code=$?
	set +e
	if [[ -n "${child_pid:-}" ]] && kill -0 "$child_pid" 2>/dev/null; then
		kill -TERM "$child_pid" 2>/dev/null
		wait "$child_pid" 2>/dev/null
	fi
	[[ ! -f "${binding_staging:-}" ]] || rm -f -- "$binding_staging"
	if [[ -n "${shim_dir:-}" && -d "$shim_dir" && ! -L "$shim_dir" && \
		"$(dirname -- "$shim_dir")" == "$private_root" && \
		"$(basename -- "$shim_dir")" == .candidate-aj-unit-ioreg.* ]]; then
		rm -f -- "$shim_dir/ioreg"
		rmdir -- "$shim_dir"
	fi
	exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

ln -s -- "$sanitizer" "$shim_dir/ioreg"
{
	printf 'format_version=1\nexperiment=2026-07-22-a72-reject-cpu8-request\n'
	printf 'candidate_label=AJ\nbinding=exact-gemian-source-disconnect-before-fixed-mac\n'
	printf 'source_target=%s\nsource_kernel=%s\nsource_architecture=%s\nsource_root=%s\n' \
		"$TARGET" "$RECOVERY_KERNEL" "$RECOVERY_ARCH" "$RECOVERY_ROOT"
	printf 'source_boot_id_recorded=no\nsource_boot_id_stable_through_disconnect=yes\n'
	printf 'source_state_confirmations=2\n'
	printf 'source_verified_utc=%s\ndisconnect_confirmed_utc=%s\n' \
		"$source_verified_utc" "$disconnect_confirmed_utc"
	printf 'disconnect_confirmed_epoch=%s\ndisconnect_probe_failures_required=2\n' \
		"$disconnect_confirmed_epoch"
	printf 'disconnect_probe_failures_observed=%s\nsource_disconnect_confirmed=yes\n' \
		"$disconnect_failures"
	printf 'fixed_mac_absent_through_source_disconnect=yes\n'
	printf 'host_address_absent_through_source_disconnect=yes\n'
	printf 'device_route_absent_through_source_disconnect=yes\n'
	printf 'candidate_fixed_mac=%s\ninstalled_full_sha256_input=%s\n' \
		"$HOST_MAC" "$installed_full_sha256"
	printf 'cycle_watcher_sha256=%s\ncandidate_identity_sha256=%s\n' \
		"$CYCLE_SHA256" "$CANDIDATE_AJ_SHA256"
	printf 'ioreg_sanitizer_sha256=%s\nssh_identity_content_recorded=no\n' \
		"$SANITIZER_SHA256"
	printf 'ssh_identity_stability_checked=yes\nknown_hosts_stability_checked=yes\n'
	printf 'known_hosts_content_recorded=no\nssh_config_file=/dev/null\n'
	printf 'ssh_batch_mode=yes\nssh_identities_only=yes\nssh_identity_agent=none\n'
	printf 'ssh_strict_host_key_checking=yes\nplaintext_device_serial_recorded=no\n'
	printf 'raw_ioreg_persisted=no\ndevice_partition_reads=none\ndevice_write_operations=none\n'
} >"$binding_staging"
chmod 0600 "$binding_staging"

publish_binding() {
	local partial destination
	[[ "$binding_published" == no ]] || return 0
	[[ -d "$output" && ! -L "$output" && "$(file_mode "$output")" == 700 ]] || return 1
	[[ "$(cd -- "$output" && pwd -P)" == "$output" ]] || die 'runtime evidence path changed identity'
	destination="$output/unit-binding.env"
	partial="$output/unit-binding.env.partial"
	[[ ! -e "$destination" && ! -L "$destination" && ! -e "$partial" && ! -L "$partial" ]] || \
		die 'unit-binding evidence destination appeared unexpectedly'
	cp -- "$binding_staging" "$partial"
	chmod 0600 "$partial"
	[[ "$(file_sha256 "$partial")" == "$(file_sha256 "$binding_staging")" ]] || \
		die 'unit-binding evidence changed during publication'
	mv -- "$partial" "$destination"
	binding_published=yes
}

write_final_binding() {
	local status_value=$1 child_code=$2 destination partial
	[[ -d "$output" && ! -L "$output" && "$(file_mode "$output")" == 700 ]] || return 0
	destination="$output/unit-binding-final.env"
	partial="$output/unit-binding-final.env.partial"
	[[ ! -e "$destination" && ! -L "$destination" && ! -e "$partial" && ! -L "$partial" ]] || \
		die 'final unit-binding evidence destination appeared unexpectedly'
	{
		printf 'format_version=1\nunit_binding_status=%s\n' "$status_value"
		printf 'source_unreachable_until_cycle_watcher_exit=%s\n' \
			"$([[ "$status_value" == valid ]] && printf yes || printf no)"
		printf 'underlying_cycle_exit_code=%s\ncompleted_utc=%s\n' \
			"$child_code" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
		printf 'plaintext_device_serial_recorded=no\nraw_ioreg_persisted=no\n'
	} >"$partial"
	chmod 0600 "$partial"
	mv -- "$partial" "$destination"
}

assert_live_pins
assert_candidate_absent
set +e
remote_state >/dev/null 2>&1
prelaunch_state_rc=$?
set -e
((prelaunch_state_rc != 0)) || die 'exact Gemian source returned before USB watcher launch'
assert_live_pins
assert_candidate_absent

cycle_args=(
	--output "$output"
	--installed-full-sha256 "$installed_full_sha256"
	--wait-seconds "$remaining_seconds"
)
((configure_address == 0)) || cycle_args+=(--configure-address)

AJ_UNIT_BOUND_REAL_IOREG="$real_ioreg" PATH="$shim_dir:$PATH" \
	bash "$cycle" "${cycle_args[@]}" &
child_pid=$!
source_returned=no
while kill -0 "$child_pid" 2>/dev/null; do
	if [[ "$binding_published" == no && -d "$output" ]]; then
		publish_binding || true
	fi
	assert_live_pins
	set +e
	remote_state >/dev/null 2>&1
	monitor_rc=$?
	set -e
	if ((monitor_rc == 0)); then
		source_returned=yes
		kill -TERM "$child_pid" 2>/dev/null || true
		break
	fi
	sleep 1
done

set +e
wait "$child_pid"
cycle_rc=$?
set -e
child_pid=
if [[ "$binding_published" == no && -d "$output" ]]; then
	publish_binding || die 'underlying watcher created unsafe runtime evidence'
fi

if [[ "$source_returned" == no ]]; then
	assert_live_pins
	set +e
	remote_state >/dev/null 2>&1
	monitor_rc=$?
	set -e
	((monitor_rc != 0)) || source_returned=yes
fi

if [[ "$source_returned" == yes ]]; then
	write_final_binding invalid-source-returned "$cycle_rc"
	die 'exact Gemian source returned before the unit-bound watcher completed'
fi

write_final_binding valid "$cycle_rc"
if ((cycle_rc == 0)); then
	printf 'unit_binding_status=valid\nsource_disconnect_confirmed=yes\n'
	printf 'source_unreachable_until_cycle_watcher_exit=yes\n'
	printf 'unit_binding=%s/unit-binding.env\n' "$output"
	printf 'unit_binding_final=%s/unit-binding-final.env\n' "$output"
fi
exit "$cycle_rc"
