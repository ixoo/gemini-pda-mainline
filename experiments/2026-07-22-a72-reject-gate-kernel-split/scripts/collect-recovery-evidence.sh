#!/usr/bin/env bash

# Capture exactly one known-good -> unavailable -> changed-known-good cycle.
# This wrapper never requests a reboot, reads a device partition, writes the
# device, or removes a remote pstore record.  Candidate AI attribution is
# optional and comes only from the separately validated USB runtime transcript.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly RECOVERY_KERNEL=3.18.41+
readonly RECOVERY_ARCH=aarch64
readonly RECOVERY_ROOT=/dev/mmcblk0p29
readonly MAX_PSTORE_TAR_BYTES=4194304
readonly MAX_RUNTIME_BYTES=2097152
readonly INSTALLED_FULL_SHA256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
readonly VALIDATOR_SHA256=234e33e013c86d3491377e902593113695e417ad0087aabda8858b35cbb5a1c7
readonly RUNTIME_VALIDATOR_SHA256=a1ca2a1a7a33eda0f9f52bbee8d964f3ed3004566183792f2eb4f446cffb1e38

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

usage() {
	cat <<'EOF'
usage: collect-recovery-evidence.sh --output DIR \
       --installed-full-sha256 SHA256 [--runtime-capture PLANNED_RUNTIME_TXT] \
       [--wait-seconds N]

Capture one read-only recovery cycle for Candidate AI.  The target and key are
fixed to gemini@192.168.1.50 and artifacts/credentials/gemini_ed25519.  N must
be at least 1200 seconds. DIR must be one new direct child of
artifacts/device-pstore/.

If --runtime-capture is omitted, changed pstore is still preserved but the
result is INCONCLUSIVE.  If supplied, PLANNED_RUNTIME_TXT must be an absent
artifacts/runtime-captures/NAME/runtime.txt at startup, produced during the
observed disconnect interval, and pass Candidate AI's exact runtime validator.

This command does not reboot, write, read a partition, or delete remote pstore.
It requires passwordless sudo solely for read-only recovery metadata/pstore.
EOF
}

output=
installed_full_sha256=
runtime_capture=
wait_seconds=1200
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires DIR'
		[[ -z "$output" ]] || die '--output was provided more than once'
		output=$2
		shift 2
		;;
	--installed-full-sha256)
		(($# >= 2)) || die '--installed-full-sha256 requires SHA256'
		[[ -z "$installed_full_sha256" ]] || \
			die '--installed-full-sha256 was provided more than once'
		installed_full_sha256=$2
		shift 2
		;;
	--runtime-capture)
		(($# >= 2)) || die '--runtime-capture requires PLANNED_RUNTIME_TXT'
		[[ -z "$runtime_capture" ]] || die '--runtime-capture was provided more than once'
		runtime_capture=$2
		shift 2
		;;
	--wait-seconds)
		(($# >= 2)) || die '--wait-seconds requires N'
		wait_seconds=$2
		shift 2
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
((wait_seconds >= 1200)) || die '--wait-seconds must be at least 1200'
((wait_seconds <= 86400)) || die '--wait-seconds must not exceed 86400'
[[ "$output" != *$'\n'* && "$runtime_capture" != *$'\n'* ]] || \
	die 'paths must be single-line values'

for command in awk basename chmod cp date dirname find git grep mkdir mktemp mv \
	python3 rm shasum sleep sort ssh stat tar wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
validator="$script_dir/validate-recovery-evidence.py"
runtime_validator="$script_dir/validate-runtime.py"
identity="$repo_root/$IDENTITY_RELATIVE"
readonly script_dir repo_root validator runtime_validator identity

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_size() { stat -f '%z' "$1" 2>/dev/null || stat -c '%s' "$1"; }
file_mtime() { stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
stream_sha256() { shasum -a 256 | awk '{ print $1 }'; }

[[ -f "$validator" && ! -L "$validator" ]] || die 'recovery validator is absent or unsafe'
[[ "$(file_sha256 "$validator")" == "$VALIDATOR_SHA256" ]] || \
	die 'recovery validator source identity changed'
[[ -f "$runtime_validator" && ! -L "$runtime_validator" ]] || \
	die 'Candidate AI runtime validator is absent or unsafe'
[[ "$(file_sha256 "$runtime_validator")" == "$RUNTIME_VALIDATOR_SHA256" ]] || \
	die 'Candidate AI runtime validator source identity changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'exact Gemini SSH identity is absent or unsafe'
[[ "$(file_mode "$identity")" == 600 ]] || die 'exact Gemini SSH identity mode is not 0600'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == "$identity" ]] || \
	die 'exact Gemini SSH identity path contains a symlink'
git -C "$repo_root" check-ignore -q -- "$identity" || \
	die 'exact Gemini SSH identity is not private under Git ignore policy'

artifacts_root="$repo_root/artifacts"
private_root="$artifacts_root/device-pstore"
runtime_root="$artifacts_root/runtime-captures"
if [[ ! -e "$artifacts_root" ]]; then
	mkdir -m 0700 "$artifacts_root"
fi
[[ -d "$artifacts_root" && ! -L "$artifacts_root" ]] || die 'artifacts root is unsafe'
[[ "$(file_mode "$artifacts_root")" == 700 ]] || die 'artifacts root mode is not 0700'
artifacts_root="$(cd -- "$artifacts_root" && pwd -P)"
[[ "$artifacts_root" == "$repo_root/artifacts" ]] || die 'artifacts root contains a symlink'
if [[ ! -e "$private_root" ]]; then
	mkdir -m 0700 "$private_root"
fi
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private pstore root is unsafe'
[[ "$(file_mode "$private_root")" == 700 ]] || die 'private pstore root mode is not 0700'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$private_root" == "$artifacts_root/device-pstore" ]] || \
	die 'private pstore root contains a symlink'
readonly artifacts_root private_root

case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac
[[ "$(dirname -- "$output")" == "$private_root" ]] || \
	die '--output must be one direct child of artifacts/device-pstore/'
output_name="$(basename -- "$output")"
[[ "$output_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || \
	die '--output must have a simple directory name'
git -C "$repo_root" check-ignore -q -- "$output" || die '--output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite recovery evidence'

runtime_requested=no
if [[ -n "$runtime_capture" ]]; then
	runtime_requested=yes
	[[ -d "$runtime_root" && ! -L "$runtime_root" ]] || \
		die 'private runtime-capture root is absent or unsafe'
	[[ "$(file_mode "$runtime_root")" == 700 ]] || \
		die 'private runtime-capture root mode is not 0700'
	runtime_root="$(cd -- "$runtime_root" && pwd -P)"
	case "$runtime_capture" in
	/*) ;;
	*) runtime_capture="$repo_root/${runtime_capture#./}" ;;
	esac
	[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || \
		die '--runtime-capture filename must be runtime.txt'
	runtime_capture_dir="$(dirname -- "$runtime_capture")"
	[[ "$(dirname -- "$runtime_capture_dir")" == "$runtime_root" ]] || \
		die '--runtime-capture must be one planned runtime-capture child'
	[[ "$(basename -- "$runtime_capture_dir")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || \
		die '--runtime-capture parent name is unsafe'
	git -C "$repo_root" check-ignore -q -- "$runtime_capture" || \
		die '--runtime-capture is not ignored by Git'
	[[ ! -e "$runtime_capture" && ! -L "$runtime_capture" ]] || \
		die 'planned runtime capture must be absent before the recovery cycle'
fi
readonly runtime_requested

staging="$(mktemp -d "$private_root/.candidate-ai-recovery.XXXXXX")"
cleanup() {
	if [[ -n "${staging:-}" && -d "$staging" && ! -L "$staging" && \
		"$(dirname -- "$staging")" == "$private_root" && \
		"$(basename -- "$staging")" == .candidate-ai-recovery.* ]]; then
		rm -rf -- "$staging"
	fi
}
trap cleanup EXIT
chmod 0700 "$staging"

ssh_options=(
	-o BatchMode=yes
	-o ConnectTimeout=5
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=3
	-o IdentitiesOnly=yes
	-o IdentityAgent=none
	-o StrictHostKeyChecking=yes
	-i "$identity"
)
readonly ssh_options

# The substitutions in this payload must expand on the recovery target.
# shellcheck disable=SC2016
remote_state_script='set -eu
test "$(id -u)" = 0
printf "kernel=%s\n" "$(uname -r)"
printf "architecture=%s\n" "$(uname -m)"
printf "root_source=%s\n" "$(findmnt -n -o SOURCE /)"
printf "boot_id=%s\n" "$(cat /proc/sys/kernel/random/boot_id)"
if test -d /sys/fs/pstore; then
	printf "pstore_directory=present\n"
else
	printf "pstore_directory=absent\n"
fi'
readonly remote_state_script

remote_state() {
	printf '%s\n' "$remote_state_script" | \
		ssh "${ssh_options[@]}" "$TARGET" 'sudo -n -- /bin/sh -s'
}

ssh_up() {
	ssh -n "${ssh_options[@]}" "$TARGET" true >/dev/null 2>&1
}

state_value() {
	local key=$1
	local text=$2
	printf '%s\n' "$text" | awk -F= -v wanted="$key" \
		'$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }'
}

state_is_expected() {
	local text=$1
	local key_count line_count
	key_count="$(printf '%s\n' "$text" | awk -F= \
		'$1 ~ /^(kernel|architecture|root_source|boot_id|pstore_directory)$/ { count++ } END { print count + 0 }')"
	line_count="$(printf '%s\n' "$text" | awk 'END { print NR + 0 }')"
	[[ "$key_count" == 5 && "$line_count" == 5 ]] || return 1
	[[ "$(state_value kernel "$text" 2>/dev/null || true)" == "$RECOVERY_KERNEL" ]] || return 1
	[[ "$(state_value architecture "$text" 2>/dev/null || true)" == "$RECOVERY_ARCH" ]] || return 1
	[[ "$(state_value root_source "$text" 2>/dev/null || true)" == "$RECOVERY_ROOT" ]] || return 1
	[[ "$(state_value pstore_directory "$text" 2>/dev/null || true)" == present ]] || return 1
	local boot_id
	boot_id="$(state_value boot_id "$text" 2>/dev/null || true)"
	[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
}

snapshot() {
	local phase=$1
	local expected_boot_id=${2:-}
	local directory="$staging/$phase"
	local before after boot_id boot_id_sha member member_name member_type
	mkdir -m 0700 "$directory" "$directory/pstore"
	before="$(remote_state)" || die "$phase recovery state capture failed"
	state_is_expected "$before" || die "$phase recovery state is not exact 3.18.41+ root /dev/mmcblk0p29"
	boot_id="$(state_value boot_id "$before")"
	if [[ -n "$expected_boot_id" && "$boot_id" != "$expected_boot_id" ]]; then
		die "$phase snapshot is not bound to the expected recovery boot ID"
	fi
	ssh -n "${ssh_options[@]}" "$TARGET" \
		'sudo -n -- tar -C /sys/fs/pstore -cf - .' >"$directory/pstore.tar" || \
		die "$phase read-only pstore archive failed"
	[[ "$(file_size "$directory/pstore.tar")" -le "$MAX_PSTORE_TAR_BYTES" ]] || \
		die "$phase pstore archive exceeds the safety bound"
	tar -tf "$directory/pstore.tar" >"$directory/pstore-members.txt" || \
		die "$phase pstore member listing failed"
	member_count=0
	while IFS= read -r member || [[ -n "$member" ]]; do
		if [[ "$member" == . || "$member" == ./ ]]; then
			continue
		fi
		[[ "$member" == ./* ]] || die "$phase pstore archive member is unsafe: $member"
		member_name=${member#./}
		[[ "$member_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || \
			die "$phase pstore archive member is unsafe: $member"
		member_count=$((member_count + 1))
		((member_count <= 64)) || die "$phase pstore archive has too many members"
	done <"$directory/pstore-members.txt"
	[[ "$(sort "$directory/pstore-members.txt" | awk 'seen[$0]++ { duplicate=1 } END { print duplicate + 0 }')" == 0 ]] || \
		die "$phase pstore archive has duplicate members"
	tar -tvf "$directory/pstore.tar" >"$directory/pstore-members.verbose"
	while IFS= read -r verbose || [[ -n "$verbose" ]]; do
		member_type=${verbose:0:1}
		case "$member_type" in
		-) ;;
		d) [[ "$verbose" == *' ./' || "$verbose" == *' .' ]] || \
			die "$phase pstore archive has an unexpected directory" ;;
		*) die "$phase pstore archive has a non-regular entry" ;;
		esac
	done <"$directory/pstore-members.verbose"
	rm -- "$directory/pstore-members.verbose"
	tar -C "$directory/pstore" -xf "$directory/pstore.tar"
	[[ -z "$(find "$directory/pstore" -mindepth 1 ! -type f -print -quit)" ]] || \
		die "$phase pstore extraction contains a non-regular entry"
	: >"$directory/pstore-inventory.tsv"
	while IFS= read -r -d '' member_path; do
		member_name="$(basename -- "$member_path")"
		[[ "$member_name" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]*$ ]] || \
			die "$phase extracted pstore name is unsafe"
		chmod 0600 "$member_path"
		printf '%s\t%s\t%s\n' "$(file_sha256 "$member_path")" \
			"$(file_size "$member_path")" "$member_name" \
			>>"$directory/pstore-inventory.tsv"
	done < <(find "$directory/pstore" -mindepth 1 -maxdepth 1 -type f -print0 | sort -z)
	after="$(remote_state)" || die "$phase recovery state changed during pstore capture"
	[[ "$after" == "$before" ]] || die "$phase recovery state changed during pstore capture"
	boot_id_sha="$(printf '%s\n' "$boot_id" | stream_sha256)"
	{
		printf 'capture_phase=%s\n' "$phase"
		printf 'kernel=%s\n' "$RECOVERY_KERNEL"
		printf 'architecture=%s\n' "$RECOVERY_ARCH"
		printf 'root_source=%s\n' "$RECOVERY_ROOT"
		printf 'boot_id_sha256=%s\n' "$boot_id_sha"
		printf 'pstore_directory=present\n'
	} >"$directory/state.env"
	chmod 0600 "$directory/state.env" "$directory/pstore.tar" \
		"$directory/pstore-members.txt" "$directory/pstore-inventory.tsv"
	printf '%s\n' "$boot_id"
}

cycle_started_epoch="$(date +%s)"
cycle_started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
initial_boot_id="$(snapshot pre)"
pre_snapshot_epoch="$(date +%s)"
pre_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

deadline_epoch=$((pre_snapshot_epoch + wait_seconds))
disconnect_failures=0
while (( $(date +%s) < deadline_epoch )); do
	if ssh_up; then
		disconnect_failures=0
	else
		disconnect_failures=$((disconnect_failures + 1))
		if ((disconnect_failures >= 2)); then
			break
		fi
	fi
	now="$(date +%s)"
	remaining=$((deadline_epoch - now))
	((remaining > 0)) || break
	((remaining > 3)) && remaining=3
	sleep "$remaining"
done
((disconnect_failures >= 2)) || \
	die "target did not remain disconnected before the ${wait_seconds}s deadline"
disconnect_observed_epoch="$(date +%s)"
disconnect_observed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

final_state=
while (( $(date +%s) < deadline_epoch )); do
	candidate_state="$(remote_state 2>/dev/null || true)"
	if state_is_expected "$candidate_state"; then
		candidate_recovery_boot_id="$(state_value boot_id "$candidate_state")"
		if [[ "$candidate_recovery_boot_id" != "$initial_boot_id" ]]; then
			final_state=$candidate_state
			break
		fi
	fi
	now="$(date +%s)"
	remaining=$((deadline_epoch - now))
	((remaining > 0)) || break
	((remaining > 3)) && remaining=3
	sleep "$remaining"
done
[[ -n "$final_state" ]] || \
	die "changed exact recovery boot did not return before the ${wait_seconds}s deadline"
final_boot_id="$(state_value boot_id "$final_state")"
[[ "$final_boot_id" != "$initial_boot_id" ]] || die 'recovery boot ID did not change'
reconnect_observed_epoch="$(date +%s)"
reconnect_observed_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

post_boot_id="$(snapshot post "$final_boot_id")"
[[ "$post_boot_id" == "$final_boot_id" ]] || die 'post snapshot boot ID changed'
post_snapshot_epoch="$(date +%s)"
post_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

runtime_source_mtime_epoch=unavailable
candidate_boot_id=unavailable
candidate_boot_id_sha256=unavailable
candidate_ai_attribution=absent
classification=INCONCLUSIVE
if [[ "$runtime_requested" == yes ]]; then
	[[ -f "$runtime_capture" && ! -L "$runtime_capture" ]] || \
		die 'planned Candidate AI runtime transcript was not produced'
	[[ -d "$(dirname -- "$runtime_capture")" && ! -L "$(dirname -- "$runtime_capture")" ]] || \
		die 'Candidate AI runtime transcript parent is unsafe'
	[[ "$(file_mode "$(dirname -- "$runtime_capture")")" == 700 ]] || \
		die 'Candidate AI runtime transcript parent mode is not 0700'
	[[ "$(file_mode "$runtime_capture")" == 600 ]] || \
		die 'Candidate AI runtime transcript mode is not 0600'
	[[ "$(file_size "$runtime_capture")" -le "$MAX_RUNTIME_BYTES" ]] || \
		die 'Candidate AI runtime transcript exceeds its size bound'
	runtime_source_mtime_epoch="$(file_mtime "$runtime_capture")"
	[[ "$runtime_source_mtime_epoch" =~ ^[0-9]+$ ]] || \
		die 'Candidate AI runtime transcript mtime is malformed'
	((runtime_source_mtime_epoch >= pre_snapshot_epoch && \
		runtime_source_mtime_epoch <= reconnect_observed_epoch + 1)) || \
		die 'Candidate AI runtime transcript was not produced during this cycle'
	runtime_source_sha256="$(file_sha256 "$runtime_capture")"
	cp -p -- "$runtime_capture" "$staging/candidate-ai-runtime.txt"
	chmod 0600 "$staging/candidate-ai-runtime.txt"
	[[ "$(file_sha256 "$runtime_capture")" == "$runtime_source_sha256" && \
		"$(file_sha256 "$staging/candidate-ai-runtime.txt")" == "$runtime_source_sha256" ]] || \
		die 'Candidate AI runtime transcript changed while copied'
	python3 "$runtime_validator" --capture "$staging/candidate-ai-runtime.txt" \
		--expected-installed-full-sha256 "$installed_full_sha256" \
		>"$staging/runtime-validation.txt" || die 'Candidate AI runtime companion is invalid'
	chmod 0600 "$staging/runtime-validation.txt"
	candidate_boot_id="$(awk '
		{
			line=$0
			sub(/\r$/, "", line)
			sub(/^GEMINI-AC-USB# /, "", line)
			if (line ~ /^boot_id=/) {
				print substr(line, 9)
				count++
			}
		}
		END { exit count != 1 }
	' "$staging/candidate-ai-runtime.txt")" || die 'Candidate AI runtime boot ID is absent or duplicated'
	[[ "$candidate_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || \
		die 'Candidate AI runtime boot ID is malformed'
	candidate_boot_id_sha256="$(printf '%s\n' "$candidate_boot_id" | stream_sha256)"
	[[ "$candidate_boot_id_sha256" != "$(printf '%s\n' "$initial_boot_id" | stream_sha256)" && \
		"$candidate_boot_id_sha256" != "$(printf '%s\n' "$final_boot_id" | stream_sha256)" ]] || \
		die 'Candidate AI runtime boot ID equals a recovery boot ID'
	candidate_ai_attribution=exact-runtime-companion
	classification=ATTRIBUTED
fi

initial_boot_id_sha256="$(printf '%s\n' "$initial_boot_id" | stream_sha256)"
final_boot_id_sha256="$(printf '%s\n' "$final_boot_id" | stream_sha256)"
{
	printf 'format_version=1\n'
	printf 'experiment=2026-07-22-a72-reject-gate-kernel-split\n'
	printf 'candidate_label=AI\n'
	printf 'target=%s\nidentity_relative=%s\n' "$TARGET" "$IDENTITY_RELATIVE"
	printf 'ssh_batch_mode=yes\nssh_identities_only=yes\n'
	printf 'ssh_identity_agent=none\nssh_strict_host_key_checking=yes\n'
	printf 'wait_seconds=%s\none_cycle_attempt=yes\n' "$wait_seconds"
	printf 'disconnect_probe_failures_required=2\n'
	printf 'pre_snapshot_confirmed=yes\ndisconnect_confirmed=yes\n'
	printf 'reconnect_confirmed=yes\npost_snapshot_confirmed=yes\n'
	printf 'boot_id_changed=yes\n'
	printf 'initial_boot_id_sha256=%s\nfinal_boot_id_sha256=%s\n' \
		"$initial_boot_id_sha256" "$final_boot_id_sha256"
	printf 'cycle_started_utc=%s\npre_snapshot_utc=%s\n' \
		"$cycle_started_utc" "$pre_snapshot_utc"
	printf 'disconnect_observed_utc=%s\nreconnect_observed_utc=%s\n' \
		"$disconnect_observed_utc" "$reconnect_observed_utc"
	printf 'post_snapshot_utc=%s\n' "$post_snapshot_utc"
	printf 'cycle_started_epoch=%s\npre_snapshot_epoch=%s\n' \
		"$cycle_started_epoch" "$pre_snapshot_epoch"
	printf 'disconnect_observed_epoch=%s\nreconnect_observed_epoch=%s\n' \
		"$disconnect_observed_epoch" "$reconnect_observed_epoch"
	printf 'post_snapshot_epoch=%s\n' "$post_snapshot_epoch"
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'installed_hash_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'installed_hash_reverified_during_recovery=no\n'
	printf 'runtime_capture_requested=%s\n' "$runtime_requested"
	printf 'runtime_source_mtime_epoch=%s\n' "$runtime_source_mtime_epoch"
	printf 'candidate_boot_id=%s\ncandidate_boot_id_sha256=%s\n' \
		"$candidate_boot_id" "$candidate_boot_id_sha256"
	printf 'candidate_ai_attribution=%s\nclassification=%s\n' \
		"$candidate_ai_attribution" "$classification"
	printf 'reboot_command_issued=no\ndevice_write_operations=none\n'
	printf 'device_partition_reads=none\nremote_pstore_delete_operations=none\n'
	printf 'raw_collect_device_pstore_primitive_used=no\n'
} >"$staging/cycle.env"
chmod 0600 "$staging/cycle.env"

validation_output="$(python3 "$validator" --evidence "$staging" \
	--expected-installed-full-sha256 "$installed_full_sha256" \
	--allow-unfinalized --write-delta)"
printf '%s\n' "$validation_output" >"$staging/validation.txt"
chmod 0600 "$staging/validation.txt" "$staging/pstore-delta.tsv"
find "$staging" -type d -exec chmod 0700 {} +
find "$staging" -type f -exec chmod 0600 {} +
(
	cd -- "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | \
		xargs -0 shasum -a 256
) >"$staging/SHA256SUMS"
chmod 0600 "$staging/SHA256SUMS"
final_validation_output="$(python3 "$validator" --evidence "$staging" \
	--expected-installed-full-sha256 "$installed_full_sha256")"
[[ "$(<"$staging/validation.txt")" == "$final_validation_output" ]] || \
	die 'final recovery validation output changed after publication manifest'

[[ ! -e "$output" && ! -L "$output" ]] || die 'recovery evidence destination appeared during capture'
mv -- "$staging" "$output"
staging=
trap - EXIT
[[ "$(file_mode "$output")" == 700 ]] || die 'published recovery evidence mode is not 0700'

printf 'evidence=%s\n' "$output"
printf 'classification=%s\n' "$classification"
printf 'candidate_ai_attribution=%s\n' "$candidate_ai_attribution"
printf 'remote_pstore_deletion=none\nreboot_command=none\ndevice_write_operations=none\n'
