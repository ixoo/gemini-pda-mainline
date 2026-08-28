#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --bundle DIR --active-boot FILE --output-parent DIR\n' "$0"
}

bundle=
active_boot=
output_parent=
while (($#)); do
	case "$1" in
	--bundle) bundle=${2:-}; shift 2 ;;
	--active-boot) active_boot=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ -n "$bundle" && -n "$active_boot" && -n "$output_parent" ]] ||
	{ usage >&2; exit 2; }

for command in awk chmod cmp dd find install jq mkdir mktemp mv python3 rm \
	sha256sum sort tail tr truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bundle="$(cd -- "$bundle" && pwd -P)"
active_boot="$(cd -- "$(dirname -- "$active_boot")" && pwd -P)/$(basename -- "$active_boot")"
mkdir -p "$output_parent"
output_parent="$(cd -- "$output_parent" && pwd -P)"
assembler="$script_dir/assemble.py"
kernel_field="$bundle/outputs/Image.gz-dtb"

readonly REPOSITORY_COMMIT=f3627d4e9dc23bd102b827eb8011bdac61b6f8a6
readonly SOURCE_COMMIT=59e00a9144d782e148332009a835b99c43382467
readonly COMPILE_MANIFEST_SHA256=6a1eb12128f69fe34ac2942a2a421d6d916939b22fb5966d7201e909489eadd9
readonly ASSEMBLER_SHA256=ed7d52e4bb5f6137c587b446171dfd3fafc8f78fa70e59dacd19b251c7ca5701
readonly PARENT_PATCHSET_SHA256=3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0
readonly ACCEPTED_ROLLBACK_PATCHSET_SHA256=76a00aeb9ebefe0c964e70e56b63977071d2f2b12b12ce52ecdb7bb298f8fdd3
readonly ONE_WAY_PATCHSET_SHA256=d9649e1453a05bc8a016da6fa371e97480ff62aebad3dedd87d148d5cb574890
readonly HELD_PATCHSET_SHA256=e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3
readonly LATE_PATCHSET_SHA256=f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91
readonly CPU9_PATCHSET_SHA256=17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b
readonly WINDOW_PATCHSET_SHA256=9ce572fbc87a1444bb71894dd4528f39dc065065a45b36db52a14791f167eeec
readonly TERMINAL_PATCHSET_SHA256=2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310
readonly COHERENCE_PATCHSET_SHA256=d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f
readonly MULTILINE_PATCHSET_SHA256=c7a9b020563c4abb74059bbf72705839c528a81d577c7031ddfb36de647fd896
readonly PARALLEL_PATCHSET_SHA256=94d3b07355e1ddb67f3f643165570255bb1f42131b3b67c074d270e8581989e2
readonly SCHEDULER_PHASE_PARENT_PATCHSET_SHA256=b2c971d4a1860ec09616a61dbd8a29fde488f7d99deb8bd6bfbf2c517b2c3493
readonly SCHEDULER_PATCHSET_SHA256=bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe
readonly REGISTER_PATCHSET_SHA256=71ef281aae8d0b99d0421b81bd3d61d82ab090125c4885977ba39d8280838469
readonly KERNEL_SHA256=de81aa06953bf1f6a24a97c88f10f1406f6af0b100f0b3f7b34674240eeefdfa
readonly ACTIVE_BOOT_SHA256=1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513
readonly ACTIVE_RAMDISK_SHA256=a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4
readonly EXPECTED_RAW_SHA256=d4ae9ee1b2f799e06e0195d8b113ef52cbd2491aa54e331bb79309e34c61922d
readonly EXPECTED_PADDED_SHA256=f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f

for input in "$assembler" "$active_boot" "$kernel_field" \
	"$bundle/SHA256SUMS" "$bundle/provenance/build.json"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "input is missing, empty, or unsafe: $input"
done
[[ "$(sha256sum "$assembler" | awk '{print $1}')" == "$ASSEMBLER_SHA256" ]] ||
	die 'assembler changed'
[[ "$(sha256sum "$bundle/SHA256SUMS" | awk '{print $1}')" == \
	"$COMPILE_MANIFEST_SHA256" ]] || die 'compile manifest changed'
(cd "$bundle" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'Buildbox bundle checksum validation failed'

require_json() {
	local field=$1 expected=$2
	[[ "$(jq -r ".${field}" "$bundle/provenance/build.json")" == "$expected" ]] ||
		die "compile provenance changed: ${field}"
}
require_json repository_commit "$REPOSITORY_COMMIT"
require_json source_commit "$SOURCE_COMMIT"
require_json parent_patchset_sha256 "$PARENT_PATCHSET_SHA256"
require_json accepted_rollback_patchset_sha256 "$ACCEPTED_ROLLBACK_PATCHSET_SHA256"
require_json one_way_patchset_sha256 "$ONE_WAY_PATCHSET_SHA256"
require_json held_patchset_sha256 "$HELD_PATCHSET_SHA256"
require_json late_patchset_sha256 "$LATE_PATCHSET_SHA256"
require_json cpu9_patchset_sha256 "$CPU9_PATCHSET_SHA256"
require_json window_patchset_sha256 "$WINDOW_PATCHSET_SHA256"
require_json terminal_patchset_sha256 "$TERMINAL_PATCHSET_SHA256"
require_json coherence_patchset_sha256 "$COHERENCE_PATCHSET_SHA256"
require_json multiline_patchset_sha256 "$MULTILINE_PATCHSET_SHA256"
require_json parallel_patchset_sha256 "$PARALLEL_PATCHSET_SHA256"
require_json scheduler_phase_parent_patchset_sha256 "$SCHEDULER_PHASE_PARENT_PATCHSET_SHA256"
require_json scheduler_patchset_sha256 "$SCHEDULER_PATCHSET_SHA256"
require_json register_patchset_sha256 "$REGISTER_PATCHSET_SHA256"
require_json build_mode register
require_json purpose a72-target-register-capsule-compile-review-only
require_json boot_candidate false
require_json baseline_source_exact_scheduler_unpark true
[[ "$(sha256sum "$kernel_field" | awk '{print $1}')" == "$KERNEL_SHA256" ]] ||
	die 'kernel field changed'
[[ "$(sha256sum "$active_boot" | awk '{print $1}')" == \
	"$ACTIVE_BOOT_SHA256" ]] || die 'active boot changed'

workdir="$(mktemp -d "$output_parent/.gemian-a72-register.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"
raw_name=gemian-a72-target-register-capsule.boot.img

python3 "$assembler" --active-boot "$active_boot" \
	--kernel-field "$kernel_field" --output "$stage/$raw_name" \
	>"$stage/assembly.txt"
python3 "$assembler" --active-boot "$active_boot" \
	--kernel-field "$kernel_field" --output "$replica/$raw_name" \
	>"$replica/assembly.txt"
cmp -s "$stage/$raw_name" "$replica/$raw_name" ||
	die 'two raw container assemblies differ'
grep -v '^output=' "$stage/assembly.txt" >"$stage/analysis.txt"
rm "$stage/assembly.txt" "$replica/assembly.txt"

raw_size="$(wc -c <"$stage/$raw_name" | tr -d ' ')"
target_size=$((16 * 1024 * 1024))
((raw_size > 0 && raw_size < target_size)) || die 'raw candidate does not fit boot2'
install -m 0600 "$stage/$raw_name" "$stage/boot2-padded.img"
truncate -s "$target_size" "$stage/boot2-padded.img"
dd if=/dev/zero of="$replica/boot2-padded.img" bs=1048576 count=16 status=none
dd if="$replica/$raw_name" of="$replica/boot2-padded.img" \
	bs=1048576 conv=notrunc status=none
cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img" ||
	die 'independent padded constructions differ'
tail_size=$((target_size - raw_size))
tail -c "$tail_size" "$stage/boot2-padded.img" |
	cmp -n "$tail_size" - /dev/zero >/dev/null || die 'padded tail is not zero'

raw_sha256="$(sha256sum "$stage/$raw_name" | awk '{print $1}')"
padded_sha256="$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')"
[[ "$raw_sha256" == "$EXPECTED_RAW_SHA256" ]] || die 'raw identity changed'
[[ "$padded_sha256" == "$EXPECTED_PADDED_SHA256" ]] || die 'padded identity changed'
{
	printf 'experiment=2026-08-28-a72-target-register-capsule\n'
	printf 'repository_commit=%s\nsource_commit=%s\n' \
		"$REPOSITORY_COMMIT" "$SOURCE_COMMIT"
	printf 'compile_manifest_sha256=%s\n' "$COMPILE_MANIFEST_SHA256"
	printf 'scheduler_patchset_sha256=%s\n' "$SCHEDULER_PATCHSET_SHA256"
	printf 'register_patchset_sha256=%s\n' "$REGISTER_PATCHSET_SHA256"
	printf 'kernel_field_sha256=%s\n' "$KERNEL_SHA256"
	printf 'active_boot_sha256=%s\nactive_ramdisk_sha256=%s\n' \
		"$ACTIVE_BOOT_SHA256" "$ACTIVE_RAMDISK_SHA256"
	printf 'raw_sha256=%s\nraw_size=%s\n' "$raw_sha256" "$raw_size"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$padded_sha256" "$target_size"
	printf 'raw_assemblies_identical=yes\npadded_constructions_identical=yes\n'
	printf 'device_access=none\npartition_write=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'candidate manifest failed'
chmod 0600 "$stage"/*

output_name="gemian-a72-target-register-capsule-${raw_sha256:0:12}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=gemian-a72-target-register-capsule-candidate\n'
printf 'artifact=%s\nraw_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$raw_sha256" "$padded_sha256"
printf 'device_access=none\nruntime_result=not-tested\n'
