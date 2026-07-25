#!/usr/bin/env bash

# Bind AJ attempt 2's exact runtime/native-reboot evidence to the later,
# deliberately unpaired Gemian snapshot, then read live-GPT boot2 exactly once.
# There is no device write or reboot path in this verifier.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly AJ_PADDED_SHA256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
readonly RUNTIME_SHA256=7cb5b63ad0ef24838cd63afc30d2af53df3ee7ae442a82453931cbca22929093
readonly NATIVE_SHA256=62be933afa872bdf25b42bf403bb0e044e9b57ac0325d1ccffbd51ca70bb2e11
readonly NATIVE_VALIDATOR_SHA256=c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd
readonly SNAPSHOT_MANIFEST_SHA256=bc5862e09ff87216d098cc35930a291b9911b348d13327e8d2de098ae116715c
readonly PREVIOUS_GEMIAN_BOOT_SHA256=c831f4c5d5e28b4b6a8a6d0f22fb258ce2d8385bfb0d5d2c3918d7908ff2a79a
readonly RETURNED_GEMIAN_BOOT_SHA256=fc23e897afb61177e976a77265435d467bdc8917a5c7d9f7c6bc132fc04e5b7b

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --runtime-capture FILE --native-reboot-capture FILE --recovery-snapshot DIR --output NEW_FILE --expected-installed-full-sha256 SHA256\n' "$0" >&2
}

runtime_capture=
native_capture=
snapshot=
output=
expected_hash=
while (($#)); do
	case "$1" in
	--runtime-capture|--native-reboot-capture|--recovery-snapshot|--output|--expected-installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--runtime-capture) [[ -z "$runtime_capture" ]] || die '--runtime-capture duplicated'; runtime_capture=$2 ;;
		--native-reboot-capture) [[ -z "$native_capture" ]] || die '--native-reboot-capture duplicated'; native_capture=$2 ;;
		--recovery-snapshot) [[ -z "$snapshot" ]] || die '--recovery-snapshot duplicated'; snapshot=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--expected-installed-full-sha256) [[ -z "$expected_hash" ]] || die '--expected-installed-full-sha256 duplicated'; expected_hash=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$runtime_capture" && -n "$native_capture" && -n "$snapshot" && -n "$output" ]] || { usage; exit 2; }
[[ "$runtime_capture$native_capture$snapshot$output" != *$'\n'* ]] || die 'paths must be single-line values'
[[ "$expected_hash" == "$AJ_PADDED_SHA256" ]] || die 'expected checksum is not Candidate AJ'
[[ "$PREVIOUS_GEMIAN_BOOT_SHA256" != "$RETURNED_GEMIAN_BOOT_SHA256" ]] || die 'Gemian boot transition identity collapsed'
for command in awk basename chmod dirname find git grep python3 shasum sort ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
runtime_root="$repo_root/artifacts/runtime-captures"
pstore_root="$repo_root/artifacts/device-pstore"
identity="$repo_root/$IDENTITY_RELATIVE"
native_validator="$script_dir/validate-native-reboot.py"
readonly script_dir repo_root runtime_root pstore_root identity native_validator
file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
field() {
	local file=$1 key=$2
	awk -F= -v wanted="$key" '$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }' "$file"
}

for root in "$repo_root/artifacts" "$runtime_root" "$pstore_root"; do
	[[ -d "$root" && ! -L "$root" && "$(file_mode "$root")" == 700 ]] || die "private root is absent or unsafe: $root"
	[[ "$(cd -- "$root" && pwd -P)" == "$root" ]] || die "private root contains an intermediate symlink: $root"
done
case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$native_capture" in /*) ;; *) native_capture="$repo_root/${native_capture#./}" ;; esac
case "$snapshot" in /*) ;; *) snapshot="$repo_root/${snapshot#./}" ;; esac
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac

capture_dir="$(dirname -- "$runtime_capture")"
[[ "$(dirname -- "$capture_dir")" == "$runtime_root" && -d "$capture_dir" && ! -L "$capture_dir" && "$(file_mode "$capture_dir")" == 700 ]] || die 'runtime capture is not one safe private child'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
[[ "$(dirname -- "$capture_dir")" == "$runtime_root" ]] || die 'runtime capture directory escaped its private root'
[[ "$runtime_capture" == "$capture_dir/runtime.txt" && "$native_capture" == "$capture_dir/native-reboot.txt" ]] || die 'attempt-2 capture filenames or colocation changed'
for evidence in "$runtime_capture" "$native_capture"; do
	[[ -f "$evidence" && ! -L "$evidence" && "$(file_mode "$evidence")" == 600 ]] || die "evidence is absent or unsafe: $evidence"
	git -C "$repo_root" check-ignore -q -- "$evidence" || die "evidence is not private: $evidence"
done
[[ "$(file_sha256 "$runtime_capture")" == "$RUNTIME_SHA256" ]] || die 'attempt-2 runtime capture identity changed'
[[ "$(file_sha256 "$native_capture")" == "$NATIVE_SHA256" ]] || die 'attempt-2 native reboot capture identity changed'
[[ -f "$native_validator" && ! -L "$native_validator" && "$(file_sha256 "$native_validator")" == "$NATIVE_VALIDATOR_SHA256" ]] || die 'native reboot validator source identity changed'
python3 "$native_validator" --capture "$native_capture" --runtime-capture "$runtime_capture" \
	--expected-installed-full-sha256 "$expected_hash" >/dev/null || die 'exact native reboot evidence validation failed'

[[ "$(dirname -- "$snapshot")" == "$pstore_root" && -d "$snapshot" && ! -L "$snapshot" && "$(file_mode "$snapshot")" == 700 ]] || die 'snapshot is not one safe private child'
snapshot="$(cd -- "$snapshot" && pwd -P)"
[[ "$(dirname -- "$snapshot")" == "$pstore_root" ]] || die 'snapshot escaped its private root'
git -C "$repo_root" check-ignore -q -- "$snapshot" || die 'snapshot is not private'
manifest="$snapshot/SHA256SUMS"
[[ -f "$manifest" && ! -L "$manifest" && "$(file_mode "$manifest")" == 600 ]] || die 'snapshot manifest is absent or unsafe'
[[ "$(file_sha256 "$manifest")" == "$SNAPSHOT_MANIFEST_SHA256" ]] || die 'raw recovery snapshot manifest identity changed'
expected_inventory=$'./SHA256SUMS\n./candidate-l-evidence.txt\n./cycle.txt\n./metadata.txt\n./pstore\n./pstore-members-verbose.txt\n./pstore-members.txt\n./pstore.tar\n./pstore/console-ramoops'
actual_inventory="$(cd -- "$snapshot" && find . -mindepth 1 -print | sort)"
[[ "$actual_inventory" == "$expected_inventory" ]] || die 'snapshot filesystem inventory changed'
[[ -z "$(find "$snapshot" -type l -print -quit)" ]] || die 'snapshot contains a symlink'
for member in candidate-l-evidence.txt cycle.txt metadata.txt pstore-members-verbose.txt pstore-members.txt pstore.tar pstore/console-ramoops; do
	[[ -f "$snapshot/$member" && ! -L "$snapshot/$member" && "$(file_mode "$snapshot/$member")" == 600 ]] || die "snapshot member is absent or unsafe: $member"
done
[[ -d "$snapshot/pstore" && ! -L "$snapshot/pstore" && "$(file_mode "$snapshot/pstore")" == 700 ]] || die 'snapshot pstore directory is unsafe'
(cd -- "$snapshot" && shasum -a 256 -c SHA256SUMS >/dev/null) || die 'snapshot internal manifest verification failed'

[[ "$(field "$snapshot/metadata.txt" kernel)" == 3.18.41+ ]] || die 'snapshot kernel identity changed'
[[ "$(field "$snapshot/metadata.txt" architecture)" == aarch64 ]] || die 'snapshot architecture changed'
[[ "$(field "$snapshot/metadata.txt" boot_id_sha256)" == "$RETURNED_GEMIAN_BOOT_SHA256" ]] || die 'snapshot boot identity changed'
[[ "$(field "$snapshot/cycle.txt" wait_for_cycle)" == no && "$(field "$snapshot/cycle.txt" boot_id_changed)" == no ]] || die 'snapshot falsely became a paired cycle'
[[ "$(field "$snapshot/cycle.txt" disconnect_observed_utc)" == not-requested && "$(field "$snapshot/cycle.txt" reconnect_observed_utc)" == not-requested ]] || die 'snapshot observer scope changed'
for key in initial_boot_id_sha256 final_boot_id_sha256 archive_pre_boot_id_sha256 archive_post_boot_id_sha256; do
	[[ "$(field "$snapshot/cycle.txt" "$key")" == "$RETURNED_GEMIAN_BOOT_SHA256" ]] || die "snapshot boot binding changed: $key"
done
[[ "$(field "$snapshot/cycle.txt" capture_kernel)" == 3.18.41+ && "$(field "$snapshot/cycle.txt" expected_kernel)" == 3.18.41+ && "$(field "$snapshot/cycle.txt" capture_arch)" == aarch64 ]] || die 'snapshot recovery identity changed'

[[ "$(dirname -- "$output")" == "$pstore_root" && "$(basename -- "$output")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.txt$ ]] || die '--output must be one new simple .txt child of artifacts/device-pstore'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite integrity evidence'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not private'
[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || die 'exact Gemini SSH identity is absent or unsafe'
git -C "$repo_root" check-ignore -q -- "$identity" || die 'exact Gemini SSH identity is not private'

{
	printf '__AJ_ATTEMPT2_POST_RETURN_BEGIN__\n'
	printf 'evidence_scope=exact-runtime-native-plus-unpaired-post-return-snapshot\npaired_cycle_observer=no\n'
	printf 'runtime_capture_sha256=%s\nnative_reboot_capture_sha256=%s\nnative_reboot_validator_sha256=%s\n' "$RUNTIME_SHA256" "$NATIVE_SHA256" "$NATIVE_VALIDATOR_SHA256"
	printf 'recovery_snapshot_sha256s_sha256=%s\nsnapshot_internal_manifest=verified\n' "$SNAPSHOT_MANIFEST_SHA256"
	printf 'snapshot_wait_for_cycle=no\nsnapshot_boot_id_changed=no\n'
	printf 'previous_gemian_boot_id_sha256=%s\nreturned_gemian_boot_id_sha256=%s\n' "$PREVIOUS_GEMIAN_BOOT_SHA256" "$RETURNED_GEMIAN_BOOT_SHA256"
} >"$output"
chmod 0600 "$output"
set +e
# The two locally expanded values are fixed lowercase SHA-256 pins, not
# untrusted remote-shell input.
# shellcheck disable=SC2029
ssh -o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 \
	-o LogLevel=ERROR -o WarnWeakCrypto=no \
	-o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=yes \
	-i "$identity" "$TARGET" \
	"sudo -n -- /bin/sh -s '$RETURNED_GEMIAN_BOOT_SHA256' '$expected_hash'" >>"$output" 2>&1 <<'REMOTE'
set -eu
expected_boot_id_sha256=$1
expected_full_sha256=$2
test "$(id -u)" = 0
test "$(uname -r)" = 3.18.41+
test "$(uname -m)" = aarch64
root_source=$(findmnt -n -o SOURCE /)
root_canonical=$(readlink -f "$root_source")
test "$root_canonical" = /dev/mmcblk0p29
boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | awk '{ print $1 }')
test "$boot_id_sha256" = "$expected_boot_id_sha256"

rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" { print }')
test "$(printf '%s\n' "$rows" | awk 'NF { count++ } END { print count + 0 }')" = 1
read -r target partlabel type size ro mountpoint extra <<ROWS
$rows
ROWS
printf '%s\n' "$target" | grep -Eq '^/dev/mmcblk0p[0-9]+$' || exit 31
test -b "$target"
kname=${target##*/}
parent=$(lsblk -dnro PKNAME "$target")
major_minor=$(lsblk -dnro MAJ:MIN "$target")
test "$type" = part
test "$size" = 16777216
test "$ro" = 0
test -z "$mountpoint"
test -z "${extra:-}"
test "$partlabel" = boot2
test "$parent" = mmcblk0
test "$(blockdev --getsize64 "$target")" = 16777216
test "$(blockdev --getro "$target")" = 0
test "$(cat "/sys/class/block/$kname/ro")" = 0
partition_number=$(cat "/sys/class/block/$kname/partition")
printf '%s\n' "$partition_number" | grep -Eq '^[0-9]+$' || exit 41
by_partlabel=$(readlink -f /dev/disk/by-partlabel/boot2)
test "$by_partlabel" = "$target"
test "$target" != /dev/mmcblk0p29

printf '%s\n' "$major_minor" | grep -Eq '^[0-9]+:[0-9]+$' || exit 42
mount_matches=$(awk -v target_major_minor="$major_minor" '$3 == target_major_minor { print }' /proc/self/mountinfo) || exit 36
mounted=no
test -z "$mount_matches" || mounted=yes
test "$mounted" = no || exit 32
swap_inventory=$(swapon --noheadings --raw --show=NAME) || exit 38
swap=no
while read -r swap_source; do
	test -n "$swap_source" || continue
	swap_resolved=$(readlink -f "$swap_source") || exit 40
	test "$swap_resolved" != "$target" || swap=yes
done <<SWAPS
$swap_inventory
SWAPS
test "$swap" = no || exit 34
holder=$(find "/sys/class/block/$kname/holders" -mindepth 1 -maxdepth 1 -print -quit) || exit 39
test -z "$holder" || exit 35

full_sha256=$(sha256sum "$target" | awk '{ print $1 }')
boot_id_after_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | awk '{ print $1 }')
printf '__AJ_ATTEMPT2_LIVE_BOOT2_BEGIN__\n'
printf 'kernel=3.18.41+\narchitecture=aarch64\nroot_source=/dev/mmcblk0p29\n'
printf 'live_boot_id_sha256=%s\n' "$boot_id_sha256"
printf 'boot2_path=%s\nboot2_kname=%s\nboot2_partlabel=boot2\nboot2_type=part\nboot2_parent=mmcblk0\n' "$target" "$kname"
printf 'boot2_size=16777216\nboot2_read_only_flag=0\nboot2_mountpoint=absent\nboot2_major_minor=%s\n' "$major_minor"
printf 'by_partlabel_path=%s\nroot_conflict=no\nmounted=%s\nswap=%s\nholders=none\n' "$by_partlabel" "$mounted" "$swap"
printf 'full_partition_sha256=%s\nexpected_full_partition_sha256=%s\n' "$full_sha256" "$expected_full_sha256"
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
printf 'live_boot_id_after_sha256=%s\n__AJ_ATTEMPT2_LIVE_BOOT2_END__\n' "$boot_id_after_sha256"
REMOTE
ssh_rc=$?
set -e
((ssh_rc == 0)) || die "read-only attempt-2 boot2 verification failed (ssh exit $ssh_rc); partial evidence was preserved"
printf '__AJ_ATTEMPT2_POST_RETURN_END__\n' >>"$output"

value() { field "$output" "$1"; }
[[ "$(grep -c '^__AJ_ATTEMPT2_POST_RETURN_BEGIN__$' "$output")" == 1 && "$(grep -c '^__AJ_ATTEMPT2_POST_RETURN_END__$' "$output")" == 1 ]] || die 'outer evidence markers changed'
[[ "$(grep -c '^__AJ_ATTEMPT2_LIVE_BOOT2_BEGIN__$' "$output")" == 1 && "$(grep -c '^__AJ_ATTEMPT2_LIVE_BOOT2_END__$' "$output")" == 1 ]] || die 'live evidence markers changed'
[[ "$(awk 'END { print NR + 0 }' "$output")" == 38 ]] || die 'attempt-2 integrity record inventory changed'
[[ "$(value evidence_scope)" == exact-runtime-native-plus-unpaired-post-return-snapshot && "$(value paired_cycle_observer)" == no ]] || die 'evidence scope changed'
[[ "$(value runtime_capture_sha256)" == "$RUNTIME_SHA256" && "$(value native_reboot_capture_sha256)" == "$NATIVE_SHA256" && "$(value native_reboot_validator_sha256)" == "$NATIVE_VALIDATOR_SHA256" ]] || die 'runtime/native evidence binding changed'
[[ "$(value recovery_snapshot_sha256s_sha256)" == "$SNAPSHOT_MANIFEST_SHA256" && "$(value snapshot_internal_manifest)" == verified && "$(value snapshot_wait_for_cycle)" == no && "$(value snapshot_boot_id_changed)" == no ]] || die 'unpaired snapshot binding changed'
[[ "$(value previous_gemian_boot_id_sha256)" == "$PREVIOUS_GEMIAN_BOOT_SHA256" && "$(value returned_gemian_boot_id_sha256)" == "$RETURNED_GEMIAN_BOOT_SHA256" ]] || die 'Gemian boot transition binding changed'
[[ "$(value kernel)" == 3.18.41+ && "$(value architecture)" == aarch64 && "$(value root_source)" == /dev/mmcblk0p29 ]] || die 'live Gemian identity changed'
[[ "$(value live_boot_id_sha256)" == "$RETURNED_GEMIAN_BOOT_SHA256" && "$(value live_boot_id_after_sha256)" == "$RETURNED_GEMIAN_BOOT_SHA256" ]] || die 'live Gemian boot changed during read'
[[ "$(value boot2_path)" =~ ^/dev/mmcblk0p[0-9]+$ && "$(value by_partlabel_path)" == "$(value boot2_path)" ]] || die 'live-GPT boot2 resolution changed'
[[ "$(value boot2_kname)" =~ ^mmcblk0p[0-9]+$ && "$(value boot2_major_minor)" =~ ^[0-9]+:[0-9]+$ ]] || die 'boot2 block identity changed'
[[ "$(value boot2_partlabel)" == boot2 && "$(value boot2_type)" == part && "$(value boot2_parent)" == mmcblk0 && "$(value boot2_size)" == 16777216 && "$(value boot2_read_only_flag)" == 0 ]] || die 'boot2 geometry changed'
[[ "$(value boot2_mountpoint)" == absent && "$(value root_conflict)" == no && "$(value mounted)" == no && "$(value swap)" == no && "$(value holders)" == none ]] || die 'boot2 is active or in use'
[[ "$(value full_partition_sha256)" == "$expected_hash" && "$(value expected_full_partition_sha256)" == "$expected_hash" ]] || die 'boot2 does not contain exact Candidate AJ'
[[ "$(value device_partition_reads)" == one-full-boot2-read-only && "$(value device_write_operations)" == none ]] || die 'storage-access record changed'

printf 'validation=candidate-aj-attempt-2-post-return-boot2-integrity\n'
printf 'evidence=%s\nboot2_full_partition_sha256=%s\n' "$output" "$expected_hash"
printf 'paired_cycle_observer=no\nrecovery_boot_id_stable_during_read=yes\n'
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
