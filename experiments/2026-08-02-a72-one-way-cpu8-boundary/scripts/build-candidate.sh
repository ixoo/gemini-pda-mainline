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

for command in awk basename chmod cmp dd find grep install jq mkdir mktemp \
  mv python3 rm sha256sum sort tail tr truncate wc xargs; do
  command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bundle="$(cd -- "$bundle" && pwd -P)"
active_boot="$(cd -- "$(dirname -- "$active_boot")" && pwd -P)/$(basename -- "$active_boot")"
mkdir -p "$output_parent"
output_parent="$(cd -- "$output_parent" && pwd -P)"
assembler="$script_dir/assemble.py"
kernel_field="$bundle/outputs/Image.gz-dtb"
readonly REPOSITORY_COMMIT=bd499e234e0849dbc96a5c7274b414564f016b6d
readonly PARENT_PATCHSET_SHA256=3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0
readonly ACCEPTED_ROLLBACK_PATCHSET_SHA256=76a00aeb9ebefe0c964e70e56b63977071d2f2b12b12ce52ecdb7bb298f8fdd3
readonly ONE_WAY_PATCHSET_SHA256=d9649e1453a05bc8a016da6fa371e97480ff62aebad3dedd87d148d5cb574890
readonly KERNEL_SHA256=e65a74cf5445a9e22a537b760e566a5a21d3d314e81689dd01c52bd11e7c6676
readonly ACTIVE_BOOT_SHA256=1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513
readonly ACTIVE_RAMDISK_SHA256=a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4
readonly EXPECTED_RAW_SHA256=aae1a0f9a3d9a3c73a4930478c2e0db672d3a12ce020ad852d9e274c7f54858a
readonly EXPECTED_PADDED_SHA256=fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda

for input in "$assembler" "$active_boot" "$kernel_field" \
  "$bundle/SHA256SUMS" "$bundle/provenance/build.json"; do
  [[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
    die "input is missing, empty, or unsafe: $input"
done
(cd "$bundle" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'Buildbox bundle checksum validation failed'
[[ "$(jq -er '.repository_commit' "$bundle/provenance/build.json")" == \
  "$REPOSITORY_COMMIT" ]] || die 'repository commit changed'
[[ "$(jq -er '.parent_patchset_sha256' "$bundle/provenance/build.json")" == \
  "$PARENT_PATCHSET_SHA256" ]] || die 'parent observer patchset changed'
[[ "$(jq -er '.accepted_rollback_patchset_sha256' "$bundle/provenance/build.json")" == \
  "$ACCEPTED_ROLLBACK_PATCHSET_SHA256" ]] || die 'accepted rollback patchset changed'
[[ "$(jq -er '.one_way_patchset_sha256' "$bundle/provenance/build.json")" == \
  "$ONE_WAY_PATCHSET_SHA256" ]] || die 'one-way patchset changed'
[[ "$(jq -er '.purpose' "$bundle/provenance/build.json")" == \
  one-way-compile-review-only ]] || die 'Buildbox purpose changed'
[[ "$(jq -er '.boot_candidate' "$bundle/provenance/build.json")" == false ]] ||
  die 'compile bundle incorrectly claims boot-candidate status'
[[ "$(sha256sum "$kernel_field" | awk '{print $1}')" == "$KERNEL_SHA256" ]] ||
  die 'kernel field changed'
[[ "$(sha256sum "$active_boot" | awk '{print $1}')" == \
  "$ACTIVE_BOOT_SHA256" ]] || die 'active boot changed'

workdir="$(mktemp -d "$output_parent/.gemian-a72-one-way.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"
raw_name=gemian-a72-one-way-cpu8.boot.img

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
  printf 'experiment=2026-08-02-a72-one-way-cpu8-boundary\n'
  printf 'repository_commit=%s\nparent_patchset_sha256=%s\n' \
    "$REPOSITORY_COMMIT" "$PARENT_PATCHSET_SHA256"
  printf 'accepted_rollback_patchset_sha256=%s\n' \
    "$ACCEPTED_ROLLBACK_PATCHSET_SHA256"
  printf 'one_way_patchset_sha256=%s\n' "$ONE_WAY_PATCHSET_SHA256"
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

output_name="gemian-a72-one-way-cpu8-${raw_sha256:0:12}"
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
printf 'validation=gemian-a72-one-way-cpu8-candidate\n'
printf 'artifact=%s\nraw_sha256=%s\npadded_sha256=%s\n' \
  "$output" "$raw_sha256" "$padded_sha256"
printf 'device_access=none\nruntime_result=not-tested\n'
