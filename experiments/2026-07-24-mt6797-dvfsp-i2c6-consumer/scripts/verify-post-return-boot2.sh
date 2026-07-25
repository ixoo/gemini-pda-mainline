#!/usr/bin/env bash

# Bind exact AP runtime/native-reboot evidence to a changed, stable Gemian boot,
# then resolve logical boot2 from the live GPT and read it exactly once. This
# verifier contains no device write or reboot path.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly IDENTITY_RELATIVE=artifacts/credentials/gemini_ed25519
readonly AP_PADDED_SHA256=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9
readonly CANDIDATE_AP_SHA256=c17ceffbd015f1ed7dca2e6d170839a2c4f0df38c921ee87f8806643c3132914

# Calibrate these only after the exact runtime/native transcript exists and the
# returned Gemian boot ID is known. The syntax gate precedes source, evidence,
# host, and device probes.
readonly RUNTIME_SHA256=c892b1c3a7bf65e97ce46da45bfda1980eb7780e392fee1d0426516c648188d7
readonly NATIVE_SHA256=d3d6573ee1e811ed5fe2b0b3e004dab9458625b0e1031993708379c114f41aa1
readonly NATIVE_VALIDATOR_SHA256=d8f0e148bab6e8b51b151099b6dadcd264ae6a4d2d2f505e19bb6e83eccc452c
readonly CANDIDATE_BOOT_ID_SHA256=560c39119d1d6fd96163575237a8c5bb72060958c3a91d73d9bf578cf999e08e
readonly RETURNED_GEMIAN_BOOT_ID_SHA256=01eac9cb47a27c161762892faddef47b0347d2b93778b5a3bd285b1e9c31724d

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --runtime-capture FILE --native-reboot-capture FILE --output NEW_FILE --expected-installed-full-sha256 SHA256 --expected-runtime-outcome PASS|FAIL\n' "$0" >&2
}
is_sha256() { [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }

runtime_capture=
native_capture=
output=
expected_hash=
expected_runtime_outcome=
while (($#)); do
	case "$1" in
	--runtime-capture|--native-reboot-capture|--output|--expected-installed-full-sha256|--expected-runtime-outcome)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--runtime-capture)
			[[ -z "$runtime_capture" ]] || die '--runtime-capture duplicated'
			runtime_capture=$2
			;;
		--native-reboot-capture)
			[[ -z "$native_capture" ]] || die '--native-reboot-capture duplicated'
			native_capture=$2
			;;
		--output)
			[[ -z "$output" ]] || die '--output duplicated'
			output=$2
			;;
		--expected-installed-full-sha256)
			[[ -z "$expected_hash" ]] || \
				die '--expected-installed-full-sha256 duplicated'
			expected_hash=$2
			;;
		--expected-runtime-outcome)
			[[ -z "$expected_runtime_outcome" ]] || \
				die '--expected-runtime-outcome duplicated'
			expected_runtime_outcome=$2
			;;
		esac
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage
		die "unknown option: $1"
		;;
	esac
done
[[ -n "$runtime_capture" && -n "$native_capture" && -n "$output" && \
	-n "$expected_hash" && -n "$expected_runtime_outcome" ]] || {
	usage
	exit 2
}
[[ "$expected_runtime_outcome" == PASS || \
	"$expected_runtime_outcome" == FAIL ]] || \
	die 'expected runtime outcome must be PASS or FAIL'
[[ "$runtime_capture$native_capture$output" != *$'\n'* ]] || \
	die 'paths must be single-line values'
for pin in "$AP_PADDED_SHA256" "$CANDIDATE_AP_SHA256" "$RUNTIME_SHA256" \
	"$NATIVE_SHA256" "$NATIVE_VALIDATOR_SHA256" \
	"$CANDIDATE_BOOT_ID_SHA256" "$RETURNED_GEMIAN_BOOT_ID_SHA256"; do
	is_sha256 "$pin" || \
		die 'Candidate AP post-return production pins remain unresolved'
done
is_sha256 "$expected_hash" || \
	die 'expected checksum must be one lowercase SHA-256 value'
[[ "$expected_hash" == "$AP_PADDED_SHA256" ]] || \
	die 'expected checksum is not Candidate AP'
[[ "$CANDIDATE_BOOT_ID_SHA256" != "$RETURNED_GEMIAN_BOOT_ID_SHA256" ]] || \
	die 'AP-to-Gemian boot transition identity collapsed'

for command in awk basename chmod dirname git grep python3 readlink shasum ssh \
	stat; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
runtime_root="$repo_root/artifacts/runtime-captures"
evidence_root="$repo_root/artifacts/device-pstore"
identity="$repo_root/$IDENTITY_RELATIVE"
candidate_identity="$script_dir/candidate_ap.py"
native_validator="$script_dir/validate-native-reboot.py"
readonly script_dir repo_root runtime_root evidence_root identity
readonly candidate_identity native_validator

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
field() {
	local file=$1 key=$2
	awk -F= -v wanted="$key" \
		'$1 == wanted { print substr($0, length($1) + 2); count++ }
		 END { exit count != 1 }' "$file"
}

# Source and selected artifact identity are resolved before private evidence
# paths and before SSH. A partially calibrated verifier therefore stays inert.
[[ -f "$candidate_identity" && ! -L "$candidate_identity" && \
	"$(file_sha256 "$candidate_identity")" == "$CANDIDATE_AP_SHA256" ]] || \
	die 'Candidate AP identity source changed'
[[ -f "$native_validator" && ! -L "$native_validator" && \
	"$(file_sha256 "$native_validator")" == "$NATIVE_VALIDATOR_SHA256" ]] || \
	die 'native reboot validator source changed'
pinned_full_sha256="$(python3 - "$candidate_identity" <<'PY'
import importlib.util
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("ap_post_return_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AP identity module")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
if module.PADDED_SHA256 == module.AO_PADDED_SHA256:
    raise RuntimeError("Candidate AP padded identity equals Candidate AO")
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AP production artifact pins are unresolved or invalid'
[[ "$pinned_full_sha256" == "$AP_PADDED_SHA256" ]] || \
	die 'Candidate AP padded identity changed'

for root in "$repo_root/artifacts" "$runtime_root" "$evidence_root"; do
	[[ -d "$root" && ! -L "$root" && "$(file_mode "$root")" == 700 ]] || \
		die "private root is absent or unsafe: $root"
	[[ "$(cd -- "$root" && pwd -P)" == "$root" ]] || \
		die "private root contains an intermediate symlink: $root"
done
case "$runtime_capture" in
/*) ;;
*) runtime_capture="$repo_root/${runtime_capture#./}" ;;
esac
case "$native_capture" in
/*) ;;
*) native_capture="$repo_root/${native_capture#./}" ;;
esac
case "$output" in
/*) ;;
*) output="$repo_root/${output#./}" ;;
esac

capture_dir="$(dirname -- "$runtime_capture")"
[[ "$(dirname -- "$capture_dir")" == "$runtime_root" && \
	"$(basename -- "$capture_dir")" == candidate-ap-* ]] || \
	die 'runtime capture is not one Candidate AP private child'
[[ -d "$capture_dir" && ! -L "$capture_dir" && \
	"$(file_mode "$capture_dir")" == 700 ]] || \
	die 'runtime capture directory is unsafe'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
[[ "$(dirname -- "$capture_dir")" == "$runtime_root" ]] || \
	die 'runtime capture directory escaped its private root'
[[ "$runtime_capture" == "$capture_dir/runtime.txt" && \
	"$native_capture" == "$capture_dir/native-reboot.txt" ]] || \
	die 'AP capture filenames or colocation changed'
for evidence in "$runtime_capture" "$native_capture"; do
	[[ -f "$evidence" && ! -L "$evidence" && \
		"$(file_mode "$evidence")" == 600 ]] || \
		die "evidence is absent or unsafe: $evidence"
	git -C "$repo_root" check-ignore -q -- "$evidence" || \
		die "evidence is not private: $evidence"
done
[[ "$(file_sha256 "$runtime_capture")" == "$RUNTIME_SHA256" ]] || \
	die 'AP runtime capture identity changed'
[[ "$(file_sha256 "$native_capture")" == "$NATIVE_SHA256" ]] || \
	die 'AP native reboot capture identity changed'

native_validation="$(python3 "$native_validator" \
	--capture "$native_capture" \
	--runtime-capture "$runtime_capture" \
	--expected-installed-full-sha256 "$expected_hash" \
	--expected-runtime-outcome "$expected_runtime_outcome")" || \
	die 'exact AP native reboot evidence validation failed'
printf '%s\n' "$native_validation" | \
	grep -qx 'validation=candidate-ap-native-reboot-request' || \
	die 'AP native reboot validation label changed'
candidate_boot_id="$(printf '%s\n' "$native_validation" | awk -F= \
	'$1 == "candidate_boot_id" {
		print substr($0, length($1) + 2); count++
	}
	END { exit count != 1 }')" || \
	die 'validated AP boot ID is absent or duplicated'
[[ "$candidate_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]] || \
	die 'validated AP boot ID is malformed'
candidate_boot_id_sha256="$(
	printf '%s\n' "$candidate_boot_id" | shasum -a 256 | awk '{ print $1 }'
)"
[[ "$candidate_boot_id_sha256" == "$CANDIDATE_BOOT_ID_SHA256" ]] || \
	die 'AP runtime boot-ID hash changed'

[[ "$(dirname -- "$output")" == "$evidence_root" && \
	"$(basename -- "$output")" =~ ^candidate-ap-post-return-[A-Za-z0-9._-]+\.txt$ ]] || \
	die '--output must be one new Candidate AP .txt child of artifacts/device-pstore'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite post-return evidence'
git -C "$repo_root" check-ignore -q -- "$output" || \
	die 'post-return output is not private'
[[ -f "$identity" && ! -L "$identity" && \
	"$(file_mode "$identity")" == 600 ]] || \
	die 'exact Gemini SSH identity is absent or unsafe'
git -C "$repo_root" check-ignore -q -- "$identity" || \
	die 'exact Gemini SSH identity is not private'

{
	printf '__AP_POST_RETURN_BEGIN__\n'
	printf 'evidence_scope=exact-runtime-native-plus-changed-gemian-readback\n'
	printf 'runtime_capture_sha256=%s\n' "$RUNTIME_SHA256"
	printf 'native_reboot_capture_sha256=%s\n' "$NATIVE_SHA256"
	printf 'native_reboot_validator_sha256=%s\n' "$NATIVE_VALIDATOR_SHA256"
	printf 'runtime_outcome=%s\n' "$expected_runtime_outcome"
	printf 'candidate_boot_id_sha256=%s\n' "$CANDIDATE_BOOT_ID_SHA256"
	printf 'returned_gemian_boot_id_sha256=%s\n' \
		"$RETURNED_GEMIAN_BOOT_ID_SHA256"
} >"$output"
chmod 0600 "$output"

set +e
# The locally expanded values are fixed lowercase SHA-256 pins, never
# untrusted remote-shell input.
# shellcheck disable=SC2029
ssh -o BatchMode=yes -o ConnectTimeout=5 \
	-o ServerAliveInterval=5 -o ServerAliveCountMax=3 \
	-o LogLevel=ERROR -o WarnWeakCrypto=no \
	-o IdentitiesOnly=yes -o IdentityAgent=none \
	-o StrictHostKeyChecking=yes -i "$identity" "$TARGET" \
	"sudo -n -- /bin/sh -s '$RETURNED_GEMIAN_BOOT_ID_SHA256' '$expected_hash'" \
	>>"$output" 2>&1 <<'REMOTE'
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

rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | \
	awk '$2 == "boot2" { print }')
test "$(printf '%s\n' "$rows" | \
	awk 'NF { count++ } END { print count + 0 }')" = 1
read -r target partlabel type size ro mountpoint extra <<ROWS
$rows
ROWS
printf '%s\n' "$target" | grep -Eq '^/dev/mmcblk0p[0-9]+$' || exit 31
test -b "$target"
kname=${target##*/}
parent=$(lsblk -dnro PKNAME "$target")
major_minor=$(lsblk -dnro MAJ:MIN "$target")
test "$partlabel" = boot2
test "$type" = part
test "$size" = 16777216
test "$ro" = 0
test -z "$mountpoint"
test -z "${extra:-}"
test "$parent" = mmcblk0
test "$(blockdev --getsize64 "$target")" = 16777216
test "$(blockdev --getro "$target")" = 0
test "$(cat "/sys/class/block/$kname/ro")" = 0
test "$(readlink -f /dev/disk/by-partlabel/boot2)" = "$target"
test "$target" != /dev/mmcblk0p29
printf '%s\n' "$major_minor" | grep -Eq '^[0-9]+:[0-9]+$' || exit 32

mount_matches=$(awk -v target_major_minor="$major_minor" \
	'$3 == target_major_minor { print }' /proc/self/mountinfo)
test -z "$mount_matches" || exit 33
swap_inventory=$(swapon --noheadings --raw --show=NAME)
while read -r swap_source; do
	test -n "$swap_source" || continue
	test "$(readlink -f "$swap_source")" != "$target" || exit 34
done <<SWAPS
$swap_inventory
SWAPS
holder=$(find "/sys/class/block/$kname/holders" \
	-mindepth 1 -maxdepth 1 -print -quit)
test -z "$holder" || exit 35

full_sha256=$(sha256sum "$target" | awk '{ print $1 }')
test "$full_sha256" = "$expected_full_sha256"
boot_id_after_sha256=$(
	sha256sum /proc/sys/kernel/random/boot_id | awk '{ print $1 }'
)
test "$boot_id_after_sha256" = "$boot_id_sha256"
printf '__AP_LIVE_BOOT2_BEGIN__\n'
printf 'kernel=3.18.41+\narchitecture=aarch64\n'
printf 'root_source=/dev/mmcblk0p29\n'
printf 'live_boot_id_sha256=%s\n' "$boot_id_sha256"
printf 'boot2_path=%s\nboot2_kname=%s\n' "$target" "$kname"
printf 'boot2_partlabel=boot2\nboot2_type=part\nboot2_parent=mmcblk0\n'
printf 'boot2_size=16777216\nboot2_read_only_flag=0\n'
printf 'boot2_mountpoint=absent\nboot2_major_minor=%s\n' "$major_minor"
printf 'by_partlabel_path=%s\n' "$target"
printf 'root_conflict=no\nmounted=no\nswap=no\nholders=none\n'
printf 'full_partition_sha256=%s\n' "$full_sha256"
printf 'expected_full_partition_sha256=%s\n' "$expected_full_sha256"
printf 'device_partition_reads=one-full-boot2-read-only\n'
printf 'device_write_operations=none\n'
printf 'live_boot_id_after_sha256=%s\n' "$boot_id_after_sha256"
printf '__AP_LIVE_BOOT2_END__\n'
REMOTE
ssh_rc=$?
set -e
((ssh_rc == 0)) || \
	die "read-only AP boot2 verification failed (ssh exit $ssh_rc); partial evidence was preserved"
printf '__AP_POST_RETURN_END__\n' >>"$output"

value() { field "$output" "$1"; }
for marker in __AP_POST_RETURN_BEGIN__ __AP_LIVE_BOOT2_BEGIN__ \
	__AP_LIVE_BOOT2_END__ __AP_POST_RETURN_END__; do
	[[ "$(grep -c "^${marker}$" "$output")" == 1 ]] || \
		die "post-return marker changed: $marker"
done
[[ "$(value evidence_scope)" == \
	exact-runtime-native-plus-changed-gemian-readback ]] || \
	die 'post-return evidence scope changed'
[[ "$(value runtime_capture_sha256)" == "$RUNTIME_SHA256" && \
	"$(value native_reboot_capture_sha256)" == "$NATIVE_SHA256" && \
	"$(value native_reboot_validator_sha256)" == \
	"$NATIVE_VALIDATOR_SHA256" ]] || \
	die 'runtime/native evidence binding changed'
[[ "$(value runtime_outcome)" == "$expected_runtime_outcome" ]] || \
	die 'post-return runtime outcome binding changed'
[[ "$(value candidate_boot_id_sha256)" == "$CANDIDATE_BOOT_ID_SHA256" && \
	"$(value returned_gemian_boot_id_sha256)" == \
	"$RETURNED_GEMIAN_BOOT_ID_SHA256" ]] || \
	die 'AP-to-Gemian transition binding changed'
[[ "$(value kernel)" == 3.18.41+ && \
	"$(value architecture)" == aarch64 && \
	"$(value root_source)" == /dev/mmcblk0p29 ]] || \
	die 'live Gemian identity changed'
[[ "$(value live_boot_id_sha256)" == \
	"$RETURNED_GEMIAN_BOOT_ID_SHA256" && \
	"$(value live_boot_id_after_sha256)" == \
	"$RETURNED_GEMIAN_BOOT_ID_SHA256" ]] || \
	die 'live Gemian boot changed during verification'
[[ "$(value boot2_path)" =~ ^/dev/mmcblk0p[0-9]+$ && \
	"$(value by_partlabel_path)" == "$(value boot2_path)" ]] || \
	die 'live-GPT boot2 resolution changed'
[[ "$(value boot2_kname)" =~ ^mmcblk0p[0-9]+$ && \
	"$(value boot2_major_minor)" =~ ^[0-9]+:[0-9]+$ ]] || \
	die 'boot2 block identity changed'
[[ "$(value boot2_partlabel)" == boot2 && \
	"$(value boot2_type)" == part && \
	"$(value boot2_parent)" == mmcblk0 && \
	"$(value boot2_size)" == 16777216 && \
	"$(value boot2_read_only_flag)" == 0 ]] || \
	die 'boot2 geometry changed'
[[ "$(value boot2_mountpoint)" == absent && \
	"$(value root_conflict)" == no && \
	"$(value mounted)" == no && "$(value swap)" == no && \
	"$(value holders)" == none ]] || \
	die 'boot2 is active or in use'
[[ "$(value full_partition_sha256)" == "$expected_hash" && \
	"$(value expected_full_partition_sha256)" == "$expected_hash" ]] || \
	die 'boot2 does not contain exact Candidate AP'
[[ "$(value device_partition_reads)" == one-full-boot2-read-only && \
	"$(value device_write_operations)" == none ]] || \
	die 'post-return storage-access record changed'

printf 'validation=candidate-ap-post-return-boot2-integrity\n'
printf 'evidence=%s\n' "$output"
printf 'boot2_full_partition_sha256=%s\n' "$expected_hash"
printf 'recovery_boot_id_stable_during_read=yes\n'
printf 'device_partition_reads=one-full-boot2-read-only\n'
printf 'device_write_operations=none\n'
