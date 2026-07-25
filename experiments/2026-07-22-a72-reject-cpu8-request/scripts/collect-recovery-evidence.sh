#!/usr/bin/env bash

# Observe one exact Gemian -> unavailable -> changed-Gemian cycle. This
# collector never requests the transition; separately produced AJ runtime and
# native-reboot transcripts are optional evidence inputs whose failure is
# preserved and classified rather than allowed to destroy the recovery record.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly RECOVERY_KERNEL=3.18.41+
readonly RECOVERY_ARCH=aarch64
readonly RECOVERY_ROOT=/dev/mmcblk0p29
readonly INSTALLED_FULL_SHA256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
readonly CANDIDATE_AJ_SHA256=77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1
readonly RUNTIME_VALIDATOR_SHA256=e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089
readonly NATIVE_VALIDATOR_SHA256=c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd
readonly RECOVERY_VALIDATOR_SHA256=a42df5750fad1773efaa9d9c4ccf7a9170d600dbfcf8ebb7d2850c222fd0379e
readonly MAX_PSTORE_TAR_BYTES=4194304
readonly MAX_COMPANION_BYTES=2097152

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	cat <<'EOF'
usage: collect-recovery-evidence.sh --output DIR \
       --installed-full-sha256 SHA256 --runtime-capture PLANNED_RUNTIME \
       --native-reboot-capture PLANNED_NATIVE [--wait-seconds N]

Both planned companion files must be absent at startup and reside in the same
private runtime-capture directory. Missing, unsafe, stale, or invalid files are
recorded without discarding the read-only recovery snapshots. This collector
does not reboot, read a device partition, write the device, or delete pstore.
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
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ && "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'installed full-partition checksum is not exact Candidate AJ'
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || die '--wait-seconds must be positive'
((wait_seconds >= 1200 && wait_seconds <= 86400)) || die '--wait-seconds must be between 1200 and 86400'
[[ "$output$runtime_capture$native_reboot_capture" != *$'\n'* ]] || die 'paths must be single-line values'
for command in awk basename cat chmod cp date dirname find git mkdir mktemp mv \
	python3 rm shasum sleep sort ssh stat tar xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
candidate_identity="$script_dir/candidate_aj.py"
runtime_validator="$script_dir/validate-runtime.py"
native_validator="$script_dir/validate-native-reboot.py"
recovery_validator="$script_dir/validate-recovery-evidence.py"
identity="$repo_root/$IDENTITY_RELATIVE"
readonly script_dir repo_root candidate_identity runtime_validator native_validator recovery_validator identity

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_size() { stat -f '%z' "$1" 2>/dev/null || stat -c '%s' "$1"; }
file_mtime() { stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
stream_sha256() { shasum -a 256 | awk '{ print $1 }'; }

# Pin every interpreter bottom-up before inspecting planned evidence or probing a target.
for pin in \
	"$candidate_identity:$CANDIDATE_AJ_SHA256:Candidate AJ identity" \
	"$runtime_validator:$RUNTIME_VALIDATOR_SHA256:runtime validator" \
	"$native_validator:$NATIVE_VALIDATOR_SHA256:native reboot validator" \
	"$recovery_validator:$RECOVERY_VALIDATOR_SHA256:recovery validator"; do
	path=${pin%%:*}; remainder=${pin#*:}; expected=${remainder%%:*}; label=${remainder#*:}
	[[ -f "$path" && ! -L "$path" ]] || die "$label is absent or unsafe"
	[[ "$(file_sha256 "$path")" == "$expected" ]] || die "$label source identity changed"
done
pinned_full_sha256="$(python3 - "$candidate_identity" <<'PY'
import importlib.util
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("aj_recovery_collector_pins", path)
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
[[ "$pinned_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'Candidate AJ padded identity changed'

[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || die 'exact Gemini SSH identity is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == "$identity" ]] || die 'exact Gemini SSH identity path contains a symlink'
git -C "$repo_root" check-ignore -q -- "$identity" || die 'exact Gemini SSH identity is not private'

artifacts_root="$repo_root/artifacts"
private_root="$artifacts_root/device-pstore"
runtime_root="$artifacts_root/runtime-captures"
[[ -d "$artifacts_root" && ! -L "$artifacts_root" && "$(file_mode "$artifacts_root")" == 700 ]] || die 'artifacts root is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || die 'private pstore root is absent or unsafe'
[[ -d "$runtime_root" && ! -L "$runtime_root" && "$(file_mode "$runtime_root")" == 700 ]] || die 'private runtime root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
runtime_root="$(cd -- "$runtime_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || die '--output must be one direct child of artifacts/device-pstore'
[[ "$(basename -- "$output")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die '--output name is unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite recovery evidence'
git -C "$repo_root" check-ignore -q -- "$output" || die '--output is not ignored by Git'

case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$native_reboot_capture" in /*) ;; *) native_reboot_capture="$repo_root/${native_reboot_capture#./}" ;; esac
runtime_parent="$(dirname -- "$runtime_capture")"
[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || die 'planned runtime filename must be runtime.txt'
[[ "$(basename -- "$native_reboot_capture")" == native-reboot.txt ]] || die 'planned native reboot filename must be native-reboot.txt'
[[ "$(dirname -- "$native_reboot_capture")" == "$runtime_parent" && "$(dirname -- "$runtime_parent")" == "$runtime_root" ]] || die 'planned companions must share one direct private runtime child'
[[ -d "$runtime_parent" && ! -L "$runtime_parent" && "$(file_mode "$runtime_parent")" == 700 ]] || die 'planned companion directory is absent or unsafe'
runtime_parent="$(cd -- "$runtime_parent" && pwd -P)"
runtime_capture="$runtime_parent/runtime.txt"
native_reboot_capture="$runtime_parent/native-reboot.txt"
git -C "$repo_root" check-ignore -q -- "$runtime_capture" || die 'planned runtime companion is not private'
git -C "$repo_root" check-ignore -q -- "$native_reboot_capture" || die 'planned native reboot companion is not private'
[[ ! -e "$runtime_capture" && ! -L "$runtime_capture" && ! -e "$native_reboot_capture" && ! -L "$native_reboot_capture" ]] || die 'planned companions must both be absent at startup'

staging="$(mktemp -d "$private_root/.candidate-aj-recovery.XXXXXX")"
cleanup() {
	if [[ -n "${staging:-}" && -d "$staging" && ! -L "$staging" && "$(dirname -- "$staging")" == "$private_root" && "$(basename -- "$staging")" == .candidate-aj-recovery.* ]]; then
		rm -rf -- "$staging"
	fi
}
trap cleanup EXIT
chmod 0700 "$staging"

ssh_options=(
	-o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=5
	-o ServerAliveCountMax=3 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
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

remote_state() { printf '%s\n' "$remote_state_script" | ssh "${ssh_options[@]}" "$TARGET" 'sudo -n -- /bin/sh -s'; }
ssh_up() { ssh -n "${ssh_options[@]}" "$TARGET" true >/dev/null 2>&1; }
state_value() {
	local key=$1 text=$2
	printf '%s\n' "$text" | awk -F= -v wanted="$key" '$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }'
}
state_is_expected() {
	local text=$1 boot_id
	[[ "$(printf '%s\n' "$text" | awk 'END { print NR + 0 }')" == 5 ]] || return 1
	[[ "$(state_value kernel "$text" 2>/dev/null || true)" == "$RECOVERY_KERNEL" ]] || return 1
	[[ "$(state_value architecture "$text" 2>/dev/null || true)" == "$RECOVERY_ARCH" ]] || return 1
	[[ "$(state_value root_source "$text" 2>/dev/null || true)" == "$RECOVERY_ROOT" ]] || return 1
	[[ "$(state_value pstore_directory "$text" 2>/dev/null || true)" == present ]] || return 1
	boot_id="$(state_value boot_id "$text" 2>/dev/null || true)"
	[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
}

snapshot() {
	local phase=$1 expected_boot_id=${2:-}
	local directory="$staging/$phase"
	local before after boot_id boot_sha member member_name member_type member_path
	mkdir -m 0700 "$directory" "$directory/pstore"
	before="$(remote_state)" || die "$phase recovery state capture failed"
	state_is_expected "$before" || die "$phase recovery state is not exact Gemian"
	boot_id="$(state_value boot_id "$before")"
	[[ -z "$expected_boot_id" || "$boot_id" == "$expected_boot_id" ]] || die "$phase snapshot boot ID changed"
	ssh -n "${ssh_options[@]}" "$TARGET" 'sudo -n -- tar -C /sys/fs/pstore -cf - .' >"$directory/pstore.tar" || die "$phase pstore archive failed"
	[[ "$(file_size "$directory/pstore.tar")" -le "$MAX_PSTORE_TAR_BYTES" ]] || die "$phase pstore archive exceeds bound"
	tar -tf "$directory/pstore.tar" >"$directory/pstore-members.txt" || die "$phase pstore member listing failed"
	member_count=0
	while IFS= read -r member || [[ -n "$member" ]]; do
		[[ "$member" == . || "$member" == ./ ]] && continue
		[[ "$member" == ./* ]] || die "$phase pstore archive member is unsafe"
		member_name=${member#./}
		[[ "$member_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || die "$phase pstore member name is unsafe"
		member_count=$((member_count + 1)); ((member_count <= 64)) || die "$phase pstore archive has too many members"
	done <"$directory/pstore-members.txt"
	tar -tvf "$directory/pstore.tar" >"$directory/pstore-members.verbose"
	while IFS= read -r verbose || [[ -n "$verbose" ]]; do
		member_type=${verbose:0:1}
		case "$member_type" in -) ;; d) [[ "$verbose" == *' ./' || "$verbose" == *' .' ]] || die "$phase archive directory is unsafe" ;; *) die "$phase archive has a non-regular entry" ;; esac
	done <"$directory/pstore-members.verbose"
	rm -- "$directory/pstore-members.verbose"
	tar -C "$directory/pstore" -xf "$directory/pstore.tar"
	[[ -z "$(find "$directory/pstore" -mindepth 1 ! -type f -print -quit)" ]] || die "$phase pstore extraction is unsafe"
	: >"$directory/pstore-inventory.tsv"
	while IFS= read -r -d '' member_path; do
		member_name="$(basename -- "$member_path")"
		chmod 0600 "$member_path"
		printf '%s\t%s\t%s\n' "$(file_sha256 "$member_path")" "$(file_size "$member_path")" "$member_name" >>"$directory/pstore-inventory.tsv"
	done < <(find "$directory/pstore" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z)
	after="$(remote_state)" || die "$phase recovery state changed during capture"
	[[ "$after" == "$before" ]] || die "$phase recovery state changed during capture"
	boot_sha="$(printf '%s\n' "$boot_id" | stream_sha256)"
	{
		printf 'capture_phase=%s\nkernel=%s\narchitecture=%s\nroot_source=%s\n' "$phase" "$RECOVERY_KERNEL" "$RECOVERY_ARCH" "$RECOVERY_ROOT"
		printf 'boot_id_sha256=%s\npstore_directory=present\n' "$boot_sha"
	} >"$directory/state.env"
	chmod 0600 "$directory"/* 2>/dev/null || true
	chmod 0700 "$directory/pstore"
	printf '%s\n' "$boot_id"
}

cycle_started_epoch="$(date +%s)"; cycle_started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
initial_boot_id="$(snapshot pre)"
pre_snapshot_epoch="$(date +%s)"; pre_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
deadline_epoch=$((pre_snapshot_epoch + wait_seconds))
disconnect_failures=0
while (( $(date +%s) < deadline_epoch )); do
	if ssh_up; then disconnect_failures=0; else disconnect_failures=$((disconnect_failures + 1)); ((disconnect_failures >= 2)) && break; fi
	now="$(date +%s)"; remaining=$((deadline_epoch - now)); ((remaining > 0)) || break; ((remaining > 3)) && remaining=3; sleep "$remaining"
done
((disconnect_failures >= 2)) || die "target did not remain disconnected before ${wait_seconds}s deadline"
disconnect_observed_epoch="$(date +%s)"; disconnect_observed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

final_state=
while (( $(date +%s) < deadline_epoch )); do
	candidate_state="$(remote_state 2>/dev/null || true)"
	if state_is_expected "$candidate_state"; then
		candidate_recovery_boot_id="$(state_value boot_id "$candidate_state")"
		if [[ "$candidate_recovery_boot_id" != "$initial_boot_id" ]]; then final_state=$candidate_state; break; fi
	fi
	now="$(date +%s)"; remaining=$((deadline_epoch - now)); ((remaining > 0)) || break; ((remaining > 3)) && remaining=3; sleep "$remaining"
done
[[ -n "$final_state" ]] || die "changed exact recovery boot did not return before ${wait_seconds}s deadline"
final_boot_id="$(state_value boot_id "$final_state")"
reconnect_observed_epoch="$(date +%s)"; reconnect_observed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
post_boot_id="$(snapshot post "$final_boot_id")"
[[ "$post_boot_id" == "$final_boot_id" ]] || die 'post snapshot boot ID changed'
post_snapshot_epoch="$(date +%s)"; post_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

runtime_status=absent; runtime_preserved=no; runtime_mtime=unavailable
if [[ ! -e "$runtime_capture" && ! -L "$runtime_capture" ]]; then
	printf 'status=absent\nreason=planned-runtime-not-produced\n' >"$staging/runtime-validation.txt"
elif [[ -f "$runtime_capture" && ! -L "$runtime_capture" && "$(file_size "$runtime_capture")" -le "$MAX_COMPANION_BYTES" ]]; then
	runtime_preserved=yes; runtime_mtime="$(file_mtime "$runtime_capture")"; source_sha="$(file_sha256 "$runtime_capture")"
	cp -p -- "$runtime_capture" "$staging/candidate-aj-runtime.txt"; chmod 0600 "$staging/candidate-aj-runtime.txt"
	if [[ "$(file_sha256 "$runtime_capture")" != "$source_sha" || "$(file_sha256 "$staging/candidate-aj-runtime.txt")" != "$source_sha" ]]; then
		runtime_status=invalid; printf 'status=invalid\nreason=runtime-changed-during-copy\n' >"$staging/runtime-validation.txt"
	elif ((runtime_mtime < disconnect_observed_epoch || runtime_mtime > reconnect_observed_epoch)); then
		runtime_status=invalid; printf 'status=invalid\nreason=runtime-mtime-outside-disconnect-reconnect\n' >"$staging/runtime-validation.txt"
	else
		set +e
		python3 "$runtime_validator" --capture "$staging/candidate-aj-runtime.txt" --expected-installed-full-sha256 "$installed_full_sha256" >"$staging/runtime-validator-output.tmp" 2>&1
		runtime_rc=$?
		set -e
		if ((runtime_rc == 0)); then runtime_status=valid; printf 'status=valid\n' >"$staging/runtime-validation.txt"; else runtime_status=invalid; printf 'status=invalid\nreason=runtime-validator-rejected\n' >"$staging/runtime-validation.txt"; fi
		cat "$staging/runtime-validator-output.tmp" >>"$staging/runtime-validation.txt"; rm -- "$staging/runtime-validator-output.tmp"
	fi
else
	runtime_status=invalid; printf 'status=invalid\nreason=runtime-source-unsafe-or-oversize\n' >"$staging/runtime-validation.txt"
fi

native_status=absent; native_preserved=no; native_mtime=unavailable
if [[ ! -e "$native_reboot_capture" && ! -L "$native_reboot_capture" ]]; then
	printf 'status=absent\nreason=planned-native-reboot-not-produced\n' >"$staging/native-reboot-validation.txt"
elif [[ -f "$native_reboot_capture" && ! -L "$native_reboot_capture" && "$(file_size "$native_reboot_capture")" -le "$MAX_COMPANION_BYTES" ]]; then
	native_preserved=yes; native_mtime="$(file_mtime "$native_reboot_capture")"; source_sha="$(file_sha256 "$native_reboot_capture")"
	cp -p -- "$native_reboot_capture" "$staging/candidate-aj-native-reboot.txt"; chmod 0600 "$staging/candidate-aj-native-reboot.txt"
	if [[ "$(file_sha256 "$native_reboot_capture")" != "$source_sha" || "$(file_sha256 "$staging/candidate-aj-native-reboot.txt")" != "$source_sha" ]]; then
		native_status=invalid; printf 'status=invalid\nreason=native-reboot-changed-during-copy\n' >"$staging/native-reboot-validation.txt"
	elif [[ "$runtime_status" != valid ]]; then
		native_status=invalid; printf 'status=invalid\nreason=native-reboot-lacks-valid-runtime\n' >"$staging/native-reboot-validation.txt"
	elif ((native_mtime < runtime_mtime || native_mtime > reconnect_observed_epoch)); then
		native_status=invalid; printf 'status=invalid\nreason=native-reboot-mtime-outside-runtime-reconnect\n' >"$staging/native-reboot-validation.txt"
	else
		set +e
		python3 "$native_validator" --capture "$staging/candidate-aj-native-reboot.txt" --runtime-capture "$staging/candidate-aj-runtime.txt" --expected-installed-full-sha256 "$installed_full_sha256" >"$staging/native-validator-output.tmp" 2>&1
		native_rc=$?
		set -e
		if ((native_rc == 0)); then native_status=valid; printf 'status=valid\n' >"$staging/native-reboot-validation.txt"; else native_status=invalid; printf 'status=invalid\nreason=native-reboot-validator-rejected\n' >"$staging/native-reboot-validation.txt"; fi
		cat "$staging/native-validator-output.tmp" >>"$staging/native-reboot-validation.txt"; rm -- "$staging/native-validator-output.tmp"
	fi
else
	native_status=invalid; printf 'status=invalid\nreason=native-reboot-source-unsafe-or-oversize\n' >"$staging/native-reboot-validation.txt"
fi

initial_boot_id_sha256="$(printf '%s\n' "$initial_boot_id" | stream_sha256)"
final_boot_id_sha256="$(printf '%s\n' "$final_boot_id" | stream_sha256)"
case "$native_status" in valid) external_status=exact-validated-companion ;; invalid) external_status=invalid-companion ;; absent) external_status=absent ;; esac
{
	printf 'format_version=2\nexperiment=2026-07-22-a72-reject-cpu8-request\ncandidate_label=AJ\n'
	printf 'target=%s\nidentity_relative=%s\n' "$TARGET" "$IDENTITY_RELATIVE"
	printf 'ssh_batch_mode=yes\nssh_identities_only=yes\nssh_identity_agent=none\nssh_strict_host_key_checking=yes\n'
	printf 'wait_seconds=%s\none_cycle_attempt=yes\ndisconnect_probe_failures_required=2\n' "$wait_seconds"
	printf 'pre_snapshot_confirmed=yes\ndisconnect_confirmed=yes\nreconnect_confirmed=yes\npost_snapshot_confirmed=yes\nboot_id_changed=yes\n'
	printf 'initial_boot_id_sha256=%s\nfinal_boot_id_sha256=%s\n' "$initial_boot_id_sha256" "$final_boot_id_sha256"
	printf 'cycle_started_utc=%s\npre_snapshot_utc=%s\ndisconnect_observed_utc=%s\nreconnect_observed_utc=%s\npost_snapshot_utc=%s\n' "$cycle_started_utc" "$pre_snapshot_utc" "$disconnect_observed_utc" "$reconnect_observed_utc" "$post_snapshot_utc"
	printf 'cycle_started_epoch=%s\npre_snapshot_epoch=%s\ndisconnect_observed_epoch=%s\nreconnect_observed_epoch=%s\npost_snapshot_epoch=%s\n' "$cycle_started_epoch" "$pre_snapshot_epoch" "$disconnect_observed_epoch" "$reconnect_observed_epoch" "$post_snapshot_epoch"
	printf 'installed_full_sha256_input=%s\ninstalled_hash_basis=caller-supplied-prior-full-partition-readback\ninstalled_hash_reverified_during_recovery=no\n' "$installed_full_sha256"
	printf 'runtime_capture_planned=yes\nruntime_companion_status=%s\nruntime_companion_preserved=%s\nruntime_source_mtime_epoch=%s\n' "$runtime_status" "$runtime_preserved" "$runtime_mtime"
	printf 'native_reboot_capture_planned=yes\nnative_reboot_companion_status=%s\nnative_reboot_companion_preserved=%s\nnative_reboot_source_mtime_epoch=%s\n' "$native_status" "$native_preserved" "$native_mtime"
	printf 'collector_reboot_command_issued=no\nexternal_reboot_evidence_status=%s\n' "$external_status"
	printf 'device_write_operations=none\ndevice_partition_reads=none\nremote_pstore_delete_operations=none\nraw_collect_device_pstore_primitive_used=no\n'
} >"$staging/cycle.env"
chmod 0600 "$staging/cycle.env" "$staging/runtime-validation.txt" "$staging/native-reboot-validation.txt"

validation_output="$(python3 "$recovery_validator" --evidence "$staging" --expected-installed-full-sha256 "$installed_full_sha256" --allow-unfinalized --write-derived)"
printf '%s\n' "$validation_output" >"$staging/validation.txt"
chmod 0600 "$staging/validation.txt" "$staging/pstore-delta.tsv" "$staging/derived.env"
find "$staging" -type d -exec chmod 0700 {} +
find "$staging" -type f -exec chmod 0600 {} +
(
	cd -- "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256
) >"$staging/SHA256SUMS"
chmod 0600 "$staging/SHA256SUMS"
final_validation="$(python3 "$recovery_validator" --evidence "$staging" --expected-installed-full-sha256 "$installed_full_sha256")"
[[ "$(<"$staging/validation.txt")" == "$final_validation" ]] || die 'final recovery validation changed after manifest creation'
[[ ! -e "$output" && ! -L "$output" ]] || die 'recovery evidence destination appeared during capture'
mv -- "$staging" "$output"; staging=; trap - EXIT

classification="$(awk -F= '$1 == "classification" { print $2; count++ } END { exit count != 1 }' "$output/derived.env")"
printf 'evidence=%s\nclassification=%s\n' "$output" "$classification"
printf 'runtime_companion_status=%s\nnative_reboot_companion_status=%s\n' "$runtime_status" "$native_status"
printf 'collector_reboot_command_issued=no\ndevice_partition_reads=none\ndevice_write_operations=none\n'
