#!/usr/bin/env bash

# Observe the one-way tail of an already-running Candidate AJ boot.  The exact
# AJ runtime transcript must already validate and the fixed-MAC USB link must
# be live when this process starts.  The collector never requests a reboot: it
# requires the old Gemian SSH endpoint to be unreachable, observes two exact
# USB-absence samples, then accepts only an exact Gemian return whose boot-ID
# digest differs from the pinned pre-cycle digest.  Pstore is read only.

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
readonly PRE_CYCLE_GEMIAN_BOOT_ID_SHA256=c831f4c5d5e28b4b6a8a6d0f22fb258ce2d8385bfb0d5d2c3918d7908ff2a79a
readonly CANDIDATE_AJ_SHA256=77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1
readonly RUNTIME_VALIDATOR_SHA256=e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089
readonly NATIVE_VALIDATOR_SHA256=c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd
readonly MAX_PSTORE_TAR_BYTES=4194304
readonly MAX_COMPANION_BYTES=2097152

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

usage() {
	cat <<'EOF'
usage: collect-one-way-recovery.sh --output DIR \
       --installed-full-sha256 SHA256 --runtime-capture RUNTIME \
       --native-reboot-capture NATIVE [--wait-seconds N]

Start only while exact Candidate AJ is live on its fixed-MAC USB link. RUNTIME
must already exist and pass the pinned AJ validator. NATIVE may already exist,
may be produced by a separate reboot request while this observer is running,
or may remain absent; a safe file is preserved and classified without being
allowed to destroy recovery evidence.

The observer issues no reboot, reads no device partition, writes nothing on
the device, and never removes pstore. DIR must be a new direct child of
artifacts/device-pstore/. The default deadline is 1200 seconds.
EOF
}

output=
installed_full_sha256=
runtime_capture=
native_reboot_capture=
wait_seconds=1200
while (($#)); do
	case "$1" in
	--output|--installed-full-sha256|--runtime-capture|--native-reboot-capture|--wait-seconds)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--installed-full-sha256) [[ -z "$installed_full_sha256" ]] || die '--installed-full-sha256 duplicated'; installed_full_sha256=$2 ;;
		--runtime-capture) [[ -z "$runtime_capture" ]] || die '--runtime-capture duplicated'; runtime_capture=$2 ;;
		--native-reboot-capture) [[ -z "$native_reboot_capture" ]] || die '--native-reboot-capture duplicated'; native_reboot_capture=$2 ;;
		--wait-seconds) wait_seconds=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown option: $1" ;;
	esac
done

[[ -n "$output" && -n "$runtime_capture" && -n "$native_reboot_capture" ]] || { usage >&2; exit 2; }
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ && "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die 'installed full-partition checksum is not exact Candidate AJ'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
((wait_seconds >= 1200 && wait_seconds <= 86400)) || \
	die '--wait-seconds must be between 1200 and 86400'
[[ "$output$runtime_capture$native_reboot_capture" != *$'\n'* ]] || \
	die 'paths must be single-line values'

for command in awk basename cat chmod cp date dirname find git grep ifconfig \
	mkdir mktemp mv python3 rm route shasum sleep sort ssh stat tar; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
candidate_identity="$script_dir/candidate_aj.py"
runtime_validator="$script_dir/validate-runtime.py"
native_validator="$script_dir/validate-native-reboot.py"
identity="$repo_root/$IDENTITY_RELATIVE"
readonly script_dir repo_root candidate_identity runtime_validator native_validator identity

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_size() { stat -f '%z' "$1" 2>/dev/null || stat -c '%s' "$1"; }
file_mtime() { stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
stream_sha256() { shasum -a 256 | awk '{ print $1 }'; }

for pin in \
	"$candidate_identity:$CANDIDATE_AJ_SHA256:Candidate AJ identity" \
	"$runtime_validator:$RUNTIME_VALIDATOR_SHA256:runtime validator" \
	"$native_validator:$NATIVE_VALIDATOR_SHA256:native reboot validator"; do
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
spec = importlib.util.spec_from_file_location("candidate_aj_one_way_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AJ identity module")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
if (
    module.RAW_SHA256 != "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
    or module.RAW_SIZE != "7380992"
    or module.ARTIFACT_MANIFEST_SHA256 != "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
    or module.PADDED_SHA256 != "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
    or module.AI_PADDED_SHA256 != "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
):
    raise RuntimeError("Candidate AJ/AI artifact identities changed")
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AJ production pins are unresolved or invalid'
[[ "$pinned_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die 'Candidate AJ padded identity changed'

[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || \
	die 'exact Gemini SSH identity is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == "$identity" ]] || \
	die 'exact Gemini SSH identity path contains an intermediate symlink'
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
[[ "$(cd -- "$(dirname -- "$known_hosts_path")" && pwd -P)/$(basename -- "$known_hosts_path")" == "$known_hosts_path" ]] || \
	die 'SSH known-hosts path contains an intermediate symlink'
known_hosts_start_sha256="$(file_sha256 "$known_hosts_path")"
[[ "$known_hosts_start_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'cannot identify SSH known-hosts database'
readonly known_hosts_path known_hosts_start_sha256

artifacts_root="$repo_root/artifacts"
private_root="$artifacts_root/device-pstore"
runtime_root="$artifacts_root/runtime-captures"
[[ -d "$artifacts_root" && ! -L "$artifacts_root" && "$(file_mode "$artifacts_root")" == 700 ]] || \
	die 'artifacts root is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || \
	die 'private pstore root is absent or unsafe'
[[ -d "$runtime_root" && ! -L "$runtime_root" && "$(file_mode "$runtime_root")" == 700 ]] || \
	die 'private runtime root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
runtime_root="$(cd -- "$runtime_root" && pwd -P)"
readonly artifacts_root private_root runtime_root

case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be one direct child of artifacts/device-pstore/'
[[ "$(basename -- "$output")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || \
	die '--output name is unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite recovery evidence'
git -C "$repo_root" check-ignore -q -- "$output" || die '--output is not ignored by Git'
readonly output

case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$native_reboot_capture" in /*) ;; *) native_reboot_capture="$repo_root/${native_reboot_capture#./}" ;; esac
runtime_parent="$(dirname -- "$runtime_capture")"
[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || \
	die 'runtime filename must be runtime.txt'
[[ "$(basename -- "$native_reboot_capture")" == native-reboot.txt ]] || \
	die 'native reboot filename must be native-reboot.txt'
[[ "$(dirname -- "$native_reboot_capture")" == "$runtime_parent" && \
	"$(dirname -- "$runtime_parent")" == "$runtime_root" ]] || \
	die 'companions must share one direct private runtime child'
[[ -d "$runtime_parent" && ! -L "$runtime_parent" && "$(file_mode "$runtime_parent")" == 700 ]] || \
	die 'companion directory is absent or unsafe'
runtime_parent="$(cd -- "$runtime_parent" && pwd -P)"
runtime_capture="$runtime_parent/runtime.txt"
native_reboot_capture="$runtime_parent/native-reboot.txt"
git -C "$repo_root" check-ignore -q -- "$runtime_capture" || die 'runtime companion is not private'
git -C "$repo_root" check-ignore -q -- "$native_reboot_capture" || die 'native reboot companion is not private'
[[ -f "$runtime_capture" && ! -L "$runtime_capture" && "$(file_mode "$runtime_capture")" == 600 ]] || \
	die 'exact runtime companion is absent or unsafe'
[[ "$(file_size "$runtime_capture")" -le "$MAX_COMPANION_BYTES" ]] || \
	die 'runtime companion exceeds size bound'
readonly runtime_parent runtime_capture native_reboot_capture

staging="$(mktemp -d "$private_root/.candidate-aj-one-way-recovery.XXXXXX")"
cleanup() {
	if [[ -n "${staging:-}" && -d "$staging" && ! -L "$staging" && \
		"$(dirname -- "$staging")" == "$private_root" && \
		"$(basename -- "$staging")" == .candidate-aj-one-way-recovery.* ]]; then
		rm -rf -- "$staging"
	fi
}
trap cleanup EXIT
chmod 0700 "$staging"

runtime_source_sha256="$(file_sha256 "$runtime_capture")"
runtime_source_mtime="$(file_mtime "$runtime_capture")"
cp -p -- "$runtime_capture" "$staging/candidate-aj-runtime.txt"
chmod 0600 "$staging/candidate-aj-runtime.txt"
[[ "$(file_sha256 "$runtime_capture")" == "$runtime_source_sha256" && \
	"$(file_sha256 "$staging/candidate-aj-runtime.txt")" == "$runtime_source_sha256" ]] || \
	die 'runtime companion changed during its pinned copy'
python3 "$runtime_validator" --capture "$staging/candidate-aj-runtime.txt" \
	--expected-installed-full-sha256 "$installed_full_sha256" \
	>"$staging/runtime-validation.txt" 2>&1 || die 'runtime companion is not exact validated Candidate AJ'
chmod 0600 "$staging/runtime-validation.txt"

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
printf "boot_id=%s\n" "$(cat /proc/sys/kernel/random/boot_id)"
if test -d /sys/fs/pstore; then printf "pstore_directory=present\n"; else printf "pstore_directory=absent\n"; fi'
readonly remote_state_script

remote_state() {
	printf '%s\n' "$remote_state_script" | \
		ssh "${ssh_options[@]}" "$TARGET" 'sudo -n -- /bin/sh -s'
}
ssh_up() { ssh -n "${ssh_options[@]}" "$TARGET" true >/dev/null 2>&1; }
state_value() {
	local key=$1 text=$2
	printf '%s\n' "$text" | awk -F= -v wanted="$key" \
		'$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }'
}
state_is_exact_recovery() {
	local text=$1 boot_id
	[[ "$(printf '%s\n' "$text" | awk 'END { print NR + 0 }')" == 5 ]] || return 1
	[[ "$(state_value kernel "$text" 2>/dev/null || true)" == "$RECOVERY_KERNEL" ]] || return 1
	[[ "$(state_value architecture "$text" 2>/dev/null || true)" == "$RECOVERY_ARCH" ]] || return 1
	[[ "$(state_value root_source "$text" 2>/dev/null || true)" == "$RECOVERY_ROOT" ]] || return 1
	[[ "$(state_value pstore_directory "$text" 2>/dev/null || true)" == present ]] || return 1
	boot_id="$(state_value boot_id "$text" 2>/dev/null || true)"
	[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
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
				print "__candidate_aj_one_way_route_invalid__"
				exit
			}
			if (destination == "default" || flags ~ /(^|[<,])GATEWAY([,>]|$)/) exit
			if ((destination_count == 1 &&
			     destination !~ /^10[.]15[.]19[.][0-9]+(\/[0-9]+)?$/) ||
			    interface !~ /^[A-Za-z0-9]+$/) {
				print "__candidate_aj_one_way_route_invalid__"
				exit
			}
			print interface
		}'
}

candidate_usb_state() {
	local matches match_count address_interfaces address_count route_interface interface
	matches="$(discover_exact_interfaces)"
	match_count="$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')"
	((match_count <= 1)) || die 'Candidate AJ fixed MAC is present on more than one interface'
	address_interfaces="$(interfaces_with_host_address)"
	address_count="$(printf '%s\n' "$address_interfaces" | awk 'NF { count++ } END { print count + 0 }')"
	route_interface="$(route_for_device)"
	[[ "$route_interface" != __candidate_aj_one_way_route_invalid__ ]] || \
		die 'Candidate AJ device route is malformed or ambiguous'
	if ((match_count == 1)); then
		interface=$matches
		if ((address_count == 1)) && [[ "$address_interfaces" == "$interface" && "$route_interface" == "$interface" ]]; then
			printf 'present:%s\n' "$interface"
		else
			printf 'transition\n'
		fi
	elif ((address_count == 0)) && [[ -z "$route_interface" ]]; then
		printf 'absent\n'
	else
		printf 'transition\n'
	fi
}

assert_live_pins() {
	[[ -f "$candidate_identity" && ! -L "$candidate_identity" && \
		"$(file_sha256 "$candidate_identity")" == "$CANDIDATE_AJ_SHA256" ]] || \
		die 'Candidate AJ identity changed during observation'
	[[ -f "$runtime_validator" && ! -L "$runtime_validator" && \
		"$(file_sha256 "$runtime_validator")" == "$RUNTIME_VALIDATOR_SHA256" ]] || \
		die 'runtime validator changed during observation'
	[[ -f "$native_validator" && ! -L "$native_validator" && \
		"$(file_sha256 "$native_validator")" == "$NATIVE_VALIDATOR_SHA256" ]] || \
		die 'native reboot validator changed during observation'
	[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 && \
		"$(file_sha256 "$identity")" == "$identity_start_sha256" ]] || \
		die 'exact Gemini SSH identity changed during observation'
	[[ -f "$known_hosts_path" && ! -L "$known_hosts_path" && \
		"$(file_sha256 "$known_hosts_path")" == "$known_hosts_start_sha256" ]] || \
		die 'SSH known-hosts database changed during observation'
	[[ -f "$runtime_capture" && ! -L "$runtime_capture" && \
		"$(file_sha256 "$runtime_capture")" == "$runtime_source_sha256" ]] || \
		die 'exact Candidate AJ runtime companion changed during observation'
}

snapshot_recovery() {
	local expected_boot_id=$1 expected_state=$2 directory="$staging/recovery"
	local before after member member_name member_type member_path boot_hash
	mkdir -m 0700 "$directory" "$directory/pstore"
	before="$(remote_state)" || die 'recovery state capture failed'
	state_is_exact_recovery "$before" || die 'returned target is not exact Gemian recovery'
	[[ "$before" == "$expected_state" && "$(state_value boot_id "$before")" == "$expected_boot_id" ]] || \
		die 'recovery state changed before pstore capture'
	ssh -n "${ssh_options[@]}" "$TARGET" \
		'sudo -n -- tar -C /sys/fs/pstore -cf - .' >"$directory/pstore.tar" || \
		die 'recovery pstore archive failed'
	[[ "$(file_size "$directory/pstore.tar")" -le "$MAX_PSTORE_TAR_BYTES" ]] || \
		die 'recovery pstore archive exceeds bound'
	tar -tf "$directory/pstore.tar" >"$directory/pstore-members.txt" || \
		die 'recovery pstore member listing failed'
	member_count=0
	while IFS= read -r member || [[ -n "$member" ]]; do
		[[ "$member" == . || "$member" == ./ ]] && continue
		[[ "$member" == ./* ]] || die 'recovery pstore archive member is unsafe'
		member_name=${member#./}
		[[ "$member_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || \
			die 'recovery pstore member name is unsafe'
		member_count=$((member_count + 1))
		((member_count <= 64)) || die 'recovery pstore archive has too many members'
	done <"$directory/pstore-members.txt"
	tar -tvf "$directory/pstore.tar" >"$directory/pstore-members.verbose" || \
		die 'recovery pstore verbose member listing failed'
	while IFS= read -r verbose || [[ -n "$verbose" ]]; do
		member_type=${verbose:0:1}
		case "$member_type" in
		-) ;;
		d) [[ "$verbose" == *' ./' || "$verbose" == *' .' ]] || \
			die 'recovery archive directory is unsafe' ;;
		*) die 'recovery archive has a non-regular entry' ;;
		esac
	done <"$directory/pstore-members.verbose"
	rm -- "$directory/pstore-members.verbose"
	tar -C "$directory/pstore" -xf "$directory/pstore.tar"
	[[ -z "$(find "$directory/pstore" -mindepth 1 ! -type f -print -quit)" ]] || \
		die 'recovery pstore extraction is unsafe'
	: >"$directory/pstore-inventory.tsv"
	while IFS= read -r member_path || [[ -n "$member_path" ]]; do
		[[ -n "$member_path" ]] || continue
		member_name="$(basename -- "$member_path")"
		chmod 0600 "$member_path"
		printf '%s\t%s\t%s\n' "$(file_sha256 "$member_path")" \
			"$(file_size "$member_path")" "$member_name" >>"$directory/pstore-inventory.tsv"
	done < <(find "$directory/pstore" -mindepth 1 -maxdepth 1 -type f -print | sort)
	after="$(remote_state)" || die 'recovery state changed during pstore capture'
	[[ "$after" == "$before" ]] || die 'recovery state changed during pstore capture'
	boot_hash="$(printf '%s\n' "$expected_boot_id" | stream_sha256)"
	[[ "$boot_hash" != "$PRE_CYCLE_GEMIAN_BOOT_ID_SHA256" ]] || \
		die 'returned Gemian boot ID did not change from the known pre-cycle boot'
	{
		printf 'capture_phase=recovery\n'
		printf 'kernel=%s\narchitecture=%s\nroot_source=%s\n' \
			"$RECOVERY_KERNEL" "$RECOVERY_ARCH" "$RECOVERY_ROOT"
		printf 'boot_id_sha256=%s\npstore_directory=present\n' "$boot_hash"
	} >"$directory/state.env"
	find "$directory" -maxdepth 1 -type f -exec chmod 0600 {} +
	chmod 0700 "$directory/pstore"
}

observer_started_epoch="$(date +%s)"
observer_started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
((runtime_source_mtime <= observer_started_epoch)) || die 'runtime companion has a future mtime'
assert_live_pins
initial_usb_state="$(candidate_usb_state)"
[[ "$initial_usb_state" == present:* ]] || die 'exact Candidate AJ fixed-MAC USB endpoint is not live at startup'
source_interface=${initial_usb_state#present:}
assert_live_pins
ssh_up && die 'Gemian SSH endpoint is reachable while Candidate AJ is claimed live'
assert_live_pins
sleep 2
[[ "$(candidate_usb_state)" == "present:$source_interface" ]] || \
	die 'exact Candidate AJ fixed-MAC USB endpoint was not stable at startup'
assert_live_pins
ssh_up && die 'Gemian SSH endpoint did not remain unreachable at startup'
assert_live_pins
source_gate_epoch="$(date +%s)"
source_gate_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
deadline_epoch=$((observer_started_epoch + wait_seconds))

absence_count=0
first_usb_absence_epoch=0
while (( $(date +%s) < deadline_epoch )); do
	usb_state="$(candidate_usb_state)"
	case "$usb_state" in
	absent)
		if ((absence_count == 0)); then first_usb_absence_epoch="$(date +%s)"; fi
		absence_count=$((absence_count + 1))
		((absence_count >= 2)) && break
		;;
	present:*|transition) absence_count=0 ;;
	*) die 'internal Candidate AJ USB state is malformed' ;;
	esac
	now="$(date +%s)"
	remaining=$((deadline_epoch - now))
	((remaining > 0)) || break
	((remaining > 2)) && remaining=2
	sleep "$remaining"
done
((absence_count >= 2)) || die "exact Candidate AJ USB disappearance was not stable before ${wait_seconds}s deadline"
usb_disconnect_epoch="$(date +%s)"
usb_disconnect_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

returned_state=
while (( $(date +%s) < deadline_epoch )); do
	usb_state="$(candidate_usb_state)"
	[[ "$usb_state" != present:* ]] || die 'Candidate AJ fixed-MAC USB endpoint reappeared after confirmed disappearance'
	candidate_state="$(remote_state 2>/dev/null || true)"
	if state_is_exact_recovery "$candidate_state"; then
		candidate_boot_id="$(state_value boot_id "$candidate_state")"
		candidate_boot_hash="$(printf '%s\n' "$candidate_boot_id" | stream_sha256)"
		if [[ "$candidate_boot_hash" != "$PRE_CYCLE_GEMIAN_BOOT_ID_SHA256" ]]; then
			sleep 2
			confirmed_state="$(remote_state 2>/dev/null || true)"
			if [[ "$confirmed_state" == "$candidate_state" && "$(candidate_usb_state)" == absent ]]; then
				returned_state=$candidate_state
				returned_boot_id=$candidate_boot_id
				returned_boot_id_sha256=$candidate_boot_hash
				break
			fi
		fi
	fi
	now="$(date +%s)"
	remaining=$((deadline_epoch - now))
	((remaining > 0)) || break
	((remaining > 3)) && remaining=3
	sleep "$remaining"
done
[[ -n "$returned_state" ]] || \
	die "changed exact Gemian recovery did not return before ${wait_seconds}s deadline"
recovery_return_epoch="$(date +%s)"
recovery_return_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
snapshot_recovery "$returned_boot_id" "$returned_state"
recovery_snapshot_epoch="$(date +%s)"
recovery_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[[ "$(candidate_usb_state)" == absent ]] || \
	die 'Candidate AJ fixed-MAC USB endpoint returned during recovery capture'

native_status=absent
native_preserved=no
native_source_sha256=unavailable
native_source_mtime=unavailable
native_transition_binding=absent
if [[ ! -e "$native_reboot_capture" && ! -L "$native_reboot_capture" ]]; then
	printf 'status=absent\nreason=native-reboot-capture-not-produced\n' >"$staging/native-reboot-validation.txt"
elif [[ -f "$native_reboot_capture" && ! -L "$native_reboot_capture" && \
	"$(file_mode "$native_reboot_capture")" == 600 && \
	"$(file_size "$native_reboot_capture")" -le "$MAX_COMPANION_BYTES" ]]; then
	native_preserved=yes
	native_source_sha256="$(file_sha256 "$native_reboot_capture")"
	native_source_mtime="$(file_mtime "$native_reboot_capture")"
	cp -p -- "$native_reboot_capture" "$staging/candidate-aj-native-reboot.txt"
	chmod 0600 "$staging/candidate-aj-native-reboot.txt"
	if [[ "$(file_sha256 "$native_reboot_capture")" != "$native_source_sha256" || \
		"$(file_sha256 "$staging/candidate-aj-native-reboot.txt")" != "$native_source_sha256" ]]; then
		native_status=invalid
		printf 'status=invalid\nreason=native-reboot-changed-during-copy\n' >"$staging/native-reboot-validation.txt"
	else
		set +e
		python3 "$native_validator" --capture "$staging/candidate-aj-native-reboot.txt" \
			--runtime-capture "$staging/candidate-aj-runtime.txt" \
			--expected-installed-full-sha256 "$installed_full_sha256" \
			>/dev/null 2>&1
		native_rc=$?
		set -e
		if ((native_rc == 0)); then
			native_status=valid
			if ((native_source_mtime >= observer_started_epoch && native_source_mtime <= recovery_return_epoch)); then
				native_transition_binding=exact-observer-window
			else
				native_transition_binding=valid-but-outside-observer-window
			fi
			printf 'status=valid\ntransition_binding=%s\n' "$native_transition_binding" >"$staging/native-reboot-validation.txt"
		else
			native_status=invalid
			native_transition_binding=invalid
			printf 'status=invalid\nreason=native-reboot-validator-rejected\n' >"$staging/native-reboot-validation.txt"
		fi
	fi
else
	native_status=invalid
	native_transition_binding=invalid
	printf 'status=invalid\nreason=native-reboot-source-unsafe-or-oversize\n' >"$staging/native-reboot-validation.txt"
fi
chmod 0600 "$staging/native-reboot-validation.txt"

case "$native_status:$native_transition_binding" in
valid:exact-observer-window) external_reboot_evidence_status=exact-validated-companion ;;
valid:*) external_reboot_evidence_status=valid-outside-observer-window ;;
invalid:*) external_reboot_evidence_status=invalid-companion ;;
absent:*) external_reboot_evidence_status=absent ;;
*) die 'internal native reboot companion classification is malformed' ;;
esac

assert_live_pins
[[ "$(candidate_usb_state)" == absent ]] || \
	die 'Candidate AJ fixed-MAC USB endpoint changed before evidence publication'
final_state="$(remote_state)" || die 'exact Gemian recovery disappeared before evidence publication'
[[ "$final_state" == "$returned_state" ]] || \
	die 'exact Gemian recovery state changed before evidence publication'

{
	printf 'format_version=1\nobserver=candidate-aj-one-way-recovery\n'
	printf 'candidate=AJ\ninstalled_full_sha256=%s\n' "$installed_full_sha256"
	printf 'known_pre_cycle_boot_id_sha256=%s\n' "$PRE_CYCLE_GEMIAN_BOOT_ID_SHA256"
	printf 'returned_boot_id_sha256=%s\n' "$returned_boot_id_sha256"
	printf 'returned_boot_id_differs_from_known_pre_cycle=yes\n'
	printf 'source_usb_interface=%s\nsource_usb_gate=two-stable-exact-present-observations\n' "$source_interface"
	printf 'source_gemian_ssh_gate=two-consecutive-unreachable-observations\n'
	printf 'usb_disconnect_gate=two-consecutive-exact-absence-observations\n'
	printf 'recovery_gate=two-stable-exact-gemian-observations-plus-stable-snapshot\n'
	printf 'runtime_companion_status=valid\nruntime_source_sha256=%s\nruntime_source_mtime_epoch=%s\n' \
		"$runtime_source_sha256" "$runtime_source_mtime"
	printf 'native_reboot_companion_status=%s\nnative_reboot_companion_preserved=%s\n' \
		"$native_status" "$native_preserved"
	printf 'native_reboot_source_sha256=%s\nnative_reboot_source_mtime_epoch=%s\n' \
		"$native_source_sha256" "$native_source_mtime"
	printf 'native_reboot_transition_binding=%s\nexternal_reboot_evidence_status=%s\n' \
		"$native_transition_binding" "$external_reboot_evidence_status"
	printf 'observer_started_epoch=%s\nobserver_started_utc=%s\n' "$observer_started_epoch" "$observer_started_utc"
	printf 'source_gate_epoch=%s\nsource_gate_utc=%s\n' "$source_gate_epoch" "$source_gate_utc"
	printf 'first_usb_absence_epoch=%s\nusb_disconnect_epoch=%s\nusb_disconnect_utc=%s\n' \
		"$first_usb_absence_epoch" "$usb_disconnect_epoch" "$usb_disconnect_utc"
	printf 'recovery_return_epoch=%s\nrecovery_return_utc=%s\n' "$recovery_return_epoch" "$recovery_return_utc"
	printf 'recovery_snapshot_epoch=%s\nrecovery_snapshot_utc=%s\n' \
		"$recovery_snapshot_epoch" "$recovery_snapshot_utc"
	printf 'collector_reboot_command_issued=no\n'
	printf 'device_partition_reads=none\ndevice_write_operations=none\n'
	printf 'pstore_access=read-only\npstore_records_removed=no\n'
	printf 'plaintext_boot_ids_published=no\nplaintext_device_serials_published=no\n'
} >"$staging/cycle.env"
chmod 0600 "$staging/cycle.env"

(
	cd -- "$staging"
	find . -type f ! -name SHA256SUMS -print | sort | while IFS= read -r path; do
		shasum -a 256 -- "${path#./}"
	done
) >"$staging/SHA256SUMS"
chmod 0600 "$staging/SHA256SUMS"
find "$staging" -type f -exec chmod 0600 {} +
find "$staging" -type d -exec chmod 0700 {} +
mv -- "$staging" "$output"
staging=
trap - EXIT

printf 'validation=candidate-aj-one-way-recovery-observer\n'
printf 'runtime_companion_status=valid\n'
printf 'native_reboot_companion_status=%s\n' "$native_status"
printf 'external_reboot_evidence_status=%s\n' "$external_reboot_evidence_status"
printf 'changed_exact_gemian_return=yes\n'
printf 'pstore_access=read-only\ncollector_reboot_command_issued=no\n'
printf 'device_partition_reads=none\ndevice_write_operations=none\n'
