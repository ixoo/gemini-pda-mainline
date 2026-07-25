#!/usr/bin/env bash

# Read exactly the live-GPT boot2 partition after a validated recovery cycle.
# This is intentionally not an installer derivative and contains no write path.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly INSTALLED_FULL_SHA256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
readonly CANDIDATE_AJ_SHA256=77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1
readonly RUNTIME_VALIDATOR_SHA256=e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089
readonly NATIVE_VALIDATOR_SHA256=c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd
readonly RECOVERY_VALIDATOR_SHA256=a42df5750fad1773efaa9d9c4ccf7a9170d600dbfcf8ebb7d2850c222fd0379e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --recovery-evidence DIR --output NEW_FILE --expected-installed-full-sha256 SHA256\n' "$0" >&2
}

recovery_evidence=
output=
expected_hash=
while (($#)); do
	case "$1" in
	--recovery-evidence|--output|--expected-installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--recovery-evidence) [[ -z "$recovery_evidence" ]] || die '--recovery-evidence duplicated'; recovery_evidence=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--expected-installed-full-sha256) [[ -z "$expected_hash" ]] || die '--expected-installed-full-sha256 duplicated'; expected_hash=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$recovery_evidence" && -n "$output" ]] || { usage; exit 2; }
[[ "$expected_hash" == "$INSTALLED_FULL_SHA256" ]] || die 'expected installed full-partition checksum is not Candidate AJ'
[[ "$recovery_evidence$output" != *$'\n'* ]] || die 'paths must be single-line values'
for command in awk basename chmod dirname git grep python3 shasum ssh stat; do
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
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }

# Pin the complete evidence interpreter stack before evidence or device access.
for pin in \
	"$candidate_identity:$CANDIDATE_AJ_SHA256:Candidate AJ identity" \
	"$runtime_validator:$RUNTIME_VALIDATOR_SHA256:runtime validator" \
	"$native_validator:$NATIVE_VALIDATOR_SHA256:native reboot validator" \
	"$recovery_validator:$RECOVERY_VALIDATOR_SHA256:recovery validator"; do
	path=${pin%%:*}; rest=${pin#*:}; expected=${rest%%:*}; label=${rest#*:}
	[[ -f "$path" && ! -L "$path" && "$(file_sha256 "$path")" == "$expected" ]] || die "$label source identity changed or is unsafe"
done
pinned="$(python3 - "$candidate_identity" <<'PY'
import importlib.util
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("aj_post_cycle_pins", path)
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
[[ "$pinned" == "$INSTALLED_FULL_SHA256" ]] || die 'Candidate AJ padded identity changed'

artifacts_root="$repo_root/artifacts"
[[ -d "$artifacts_root" && ! -L "$artifacts_root" && "$(file_mode "$artifacts_root")" == 700 ]] || die 'artifacts root is absent or unsafe'
artifacts_root="$(cd -- "$artifacts_root" && pwd -P)"
[[ "$artifacts_root" == "$repo_root/artifacts" ]] || die 'artifacts root contains an intermediate symlink'
private_root="$artifacts_root/device-pstore"
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || die 'private pstore root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
[[ "$private_root" == "$artifacts_root/device-pstore" ]] || die 'private pstore root contains an intermediate symlink'
case "$recovery_evidence" in /*) ;; *) recovery_evidence="$repo_root/${recovery_evidence#./}" ;; esac
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(dirname -- "$recovery_evidence")" == "$private_root" && -d "$recovery_evidence" && ! -L "$recovery_evidence" && "$(file_mode "$recovery_evidence")" == 700 ]] || die 'recovery evidence is not one exact private child'
[[ "$(dirname -- "$output")" == "$private_root" && "$(basename -- "$output")" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.txt$ ]] || die '--output must be one new simple .txt child of artifacts/device-pstore'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite post-cycle integrity evidence'
git -C "$repo_root" check-ignore -q -- "$recovery_evidence" || die 'recovery evidence is not private under Git ignore policy'
git -C "$repo_root" check-ignore -q -- "$output" || die 'post-cycle output is not private under Git ignore policy'
python3 "$recovery_validator" --evidence "$recovery_evidence" --expected-installed-full-sha256 "$expected_hash" >/dev/null || die 'recovery evidence did not pass exact final validation'
final_boot_id_sha256="$(awk -F= '$1 == "final_boot_id_sha256" { print $2; count++ } END { exit count != 1 }' "$recovery_evidence/cycle.env")" || die 'final recovery boot ID checksum is absent or duplicated'
[[ "$final_boot_id_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'final recovery boot ID checksum is malformed'
[[ -f "$identity" && ! -L "$identity" && "$(file_mode "$identity")" == 600 ]] || die 'exact Gemini SSH identity is absent or unsafe'
[[ "$(cd -- "$(dirname -- "$identity")" && pwd -P)/$(basename -- "$identity")" == "$identity" ]] || die 'exact Gemini SSH identity path contains an intermediate symlink'
git -C "$repo_root" check-ignore -q -- "$identity" || die 'exact Gemini SSH identity is not private'

: >"$output"
chmod 0600 "$output"
set +e
ssh -o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=5 \
	-o ServerAliveCountMax=3 -o IdentitiesOnly=yes -o IdentityAgent=none \
	-o StrictHostKeyChecking=yes -i "$identity" "$TARGET" \
	"sudo -n -- /bin/sh -s '$final_boot_id_sha256' '$expected_hash'" >"$output" 2>&1 <<'REMOTE'
set -eu
expected_boot_id_sha256=$1
expected_full_sha256=$2
test "$(id -u)" = 0
test "$(uname -r)" = 3.18.41+
test "$(uname -m)" = aarch64
test "$(findmnt -n -o SOURCE /)" = /dev/mmcblk0p29
boot_id=$(cat /proc/sys/kernel/random/boot_id)
boot_id_sha256=$(printf '%s\n' "$boot_id" | sha256sum | awk '{ print $1 }')
test "$boot_id_sha256" = "$expected_boot_id_sha256"

targets=$(lsblk -nrpo PATH,PARTLABEL | awk '$2 == "boot2" { print $1 }')
test "$(printf '%s\n' "$targets" | awk 'NF { count++ } END { print count + 0 }')" = 1
target=$targets
printf '%s\n' "$target" | grep -Eq '^/dev/mmcblk0p[0-9]+$' || exit 31
test -b "$target"
kname=$(lsblk -nro KNAME "$target")
type=$(lsblk -nro TYPE "$target")
size=$(lsblk -bnro SIZE "$target")
ro=$(lsblk -nro RO "$target")
mountpoint=$(lsblk -nro MOUNTPOINT "$target")
partlabel=$(lsblk -nro PARTLABEL "$target")
parent=$(lsblk -nro PKNAME "$target")
major_minor=$(lsblk -nro MAJ:MIN "$target")
test "$type" = part
test "$size" = 16777216
test "$ro" = 0
test -z "$mountpoint"
test "$partlabel" = boot2
test "$parent" = mmcblk0
test "$(blockdev --getsize64 "$target")" = 16777216
test "$(blockdev --getro "$target")" = 0
test -f "/sys/class/block/$kname/partition"
by_partlabel=$(readlink -f /dev/disk/by-partlabel/boot2)
test "$by_partlabel" = "$target"
test "$target" != /dev/mmcblk0p29
mount_inventory=$(findmnt -rn -o SOURCE,MAJ:MIN) || exit 36
mounted=no
while read -r mounted_source mounted_major_minor; do
	if test "$mounted_source" = "$target" || test "$mounted_major_minor" = "$major_minor"; then mounted=yes; fi
done <<MOUNTS
$mount_inventory
MOUNTS
test "$mounted" = no || exit 32
test -r /proc/swaps || exit 37
swap_inventory=$(awk 'NR > 1 { print $1 }' /proc/swaps) || exit 38
swap=no
while read -r swap_source; do
	if test "$swap_source" = "$target"; then swap=yes; fi
done <<SWAPS
$swap_inventory
SWAPS
test "$swap" = no || exit 34
holder=$(find "/sys/class/block/$kname/holders" -mindepth 1 -maxdepth 1 -print -quit) || exit 39
test -z "$holder" || exit 35

full_sha256=$(sha256sum "$target" | awk '{ print $1 }')
boot_id_after=$(cat /proc/sys/kernel/random/boot_id)
boot_id_after_sha256=$(printf '%s\n' "$boot_id_after" | sha256sum | awk '{ print $1 }')
printf '__AJ_POST_CYCLE_BOOT2_BEGIN__\n'
printf 'kernel=3.18.41+\narchitecture=aarch64\nroot_source=/dev/mmcblk0p29\n'
printf 'boot_id_sha256=%s\n' "$boot_id_sha256"
printf 'boot2_path=%s\nboot2_kname=%s\nboot2_partlabel=boot2\nboot2_type=part\nboot2_parent=mmcblk0\n' "$target" "$kname"
printf 'boot2_size=16777216\nboot2_read_only_flag=0\nboot2_mountpoint=absent\nboot2_major_minor=%s\n' "$major_minor"
printf 'by_partlabel_path=%s\nroot_conflict=no\nmounted=%s\nswap=%s\nholders=none\n' "$by_partlabel" "$mounted" "$swap"
printf 'full_partition_sha256=%s\nexpected_full_partition_sha256=%s\n' "$full_sha256" "$expected_full_sha256"
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
printf 'boot_id_after_sha256=%s\n__AJ_POST_CYCLE_BOOT2_END__\n' "$boot_id_after_sha256"
REMOTE
ssh_rc=$?
set -e
((ssh_rc == 0)) || die "read-only exact-Gemian boot2 verification failed (ssh exit $ssh_rc); mismatch evidence was preserved"

value() {
	local key=$1
	awk -F= -v wanted="$key" '$1 == wanted { print substr($0, length($1) + 2); count++ } END { exit count != 1 }' "$output"
}
[[ "$(grep -c '^__AJ_POST_CYCLE_BOOT2_BEGIN__$' "$output")" == 1 && "$(grep -c '^__AJ_POST_CYCLE_BOOT2_END__$' "$output")" == 1 ]] || die 'post-cycle boot2 record markers changed'
[[ "$(awk 'END { print NR + 0 }' "$output")" == 25 ]] || die 'post-cycle boot2 record inventory changed'
[[ "$(value kernel)" == 3.18.41+ && "$(value architecture)" == aarch64 && "$(value root_source)" == /dev/mmcblk0p29 ]] || die 'post-cycle recovery identity changed'
[[ "$(value boot_id_sha256)" == "$final_boot_id_sha256" && "$(value boot_id_after_sha256)" == "$final_boot_id_sha256" ]] || die 'recovery boot ID changed during boot2 read'
[[ "$(value boot2_path)" =~ ^/dev/mmcblk0p[0-9]+$ && "$(value by_partlabel_path)" == "$(value boot2_path)" ]] || die 'live-GPT boot2 resolution changed'
[[ "$(value boot2_kname)" =~ ^mmcblk0p[0-9]+$ && "$(value boot2_major_minor)" =~ ^[0-9]+:[0-9]+$ ]] || die 'live-GPT boot2 block identity changed'
[[ "$(value boot2_partlabel)" == boot2 && "$(value boot2_type)" == part && "$(value boot2_parent)" == mmcblk0 && "$(value boot2_size)" == 16777216 && "$(value boot2_read_only_flag)" == 0 ]] || die 'live-GPT boot2 geometry changed'
[[ "$(value boot2_mountpoint)" == absent && "$(value root_conflict)" == no && "$(value mounted)" == no && "$(value swap)" == no && "$(value holders)" == none ]] || die 'boot2 is active or in use'
[[ "$(value full_partition_sha256)" == "$expected_hash" && "$(value expected_full_partition_sha256)" == "$expected_hash" ]] || die 'post-cycle boot2 full-partition checksum is not Candidate AJ; mismatch evidence was preserved'
[[ "$(value device_partition_reads)" == one-full-boot2-read-only && "$(value device_write_operations)" == none ]] || die 'post-cycle storage-access record changed'
printf 'validation=candidate-aj-post-cycle-boot2-integrity\n'
printf 'evidence=%s\nboot2_full_partition_sha256=%s\n' "$output" "$expected_hash"
printf 'recovery_boot_id_stable=yes\ndevice_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
