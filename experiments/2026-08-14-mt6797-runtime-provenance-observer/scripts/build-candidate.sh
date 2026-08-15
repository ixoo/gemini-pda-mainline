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
[[ -n "${bundle}" && -n "${active_boot}" && -n "${output_parent}" ]] ||
  { usage >&2; exit 2; }

for command in awk basename chmod cmp dd find grep install jq mkdir mktemp \
  mv python3 rm sha256sum sort tail tr truncate wc xargs; do
  command -v "${command}" >/dev/null 2>&1 || die "missing command: ${command}"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bundle="$(cd -- "${bundle}" && pwd -P)"
active_boot="$(cd -- "$(dirname -- "${active_boot}")" && pwd -P)/$(basename -- "${active_boot}")"
mkdir -p "${output_parent}"
output_parent="$(cd -- "${output_parent}" && pwd -P)"
assembler="${script_dir}/assemble.py"
kernel_field="${bundle}/outputs/Image.gz-dtb"

readonly REPOSITORY_COMMIT=3556a9b07b841cc3ba99f0a5a5e9c2a03575e009
readonly SOURCE_COMMIT=d388d350cb2dda8f23b99be6fa5db9628896e87f
readonly PATCHED_COMMIT=f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24
readonly PATCH_SHA256=3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11
readonly PACKAGE_SHA256SUMS=4ed3b81a09f992bb0c80e66d35aa0f9a91bab72b9a14f288f284648abcb76821
readonly ASSEMBLER_SHA256=3e9ec896c3ff3e7f4f9849cd8f87c5fba28e65368a4abe335c2309773e826c2e
readonly KERNEL_SHA256=d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d
readonly ACTIVE_BOOT_SHA256=1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513
readonly ACTIVE_RAMDISK_SHA256=a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4
readonly EXPECTED_RAW_SHA256=e354ee4b8265d2226e49d2c9376ec3e6e39eee83fd413490de29de1c1500b72b
readonly EXPECTED_PADDED_SHA256=b17400c59f0a68db602c66cb5d83ec1c6161e98dcbd3e5d3ffece0b5c69f23a9

for input in "${assembler}" "${active_boot}" "${kernel_field}" \
  "${bundle}/SHA256SUMS" "${bundle}/provenance/build.json"; do
  [[ -f "${input}" && ! -L "${input}" && -s "${input}" ]] ||
    die "input is missing, empty, or unsafe: ${input}"
done
[[ "$(sha256sum "${assembler}" | awk '{print $1}')" == "${ASSEMBLER_SHA256}" ]] ||
  die 'assembler identity changed'
[[ "$(sha256sum "${bundle}/SHA256SUMS" | awk '{print $1}')" == \
   "${PACKAGE_SHA256SUMS}" ]] || die 'Buildbox package manifest changed'
(cd "${bundle}" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'Buildbox package checksum validation failed'

build_json="${bundle}/provenance/build.json"
[[ "$(jq -er '.repository_commit' "${build_json}")" == "${REPOSITORY_COMMIT}" ]] ||
  die 'repository commit changed'
[[ "$(jq -er '.source_commit' "${build_json}")" == "${SOURCE_COMMIT}" ]] ||
  die 'vendor source commit changed'
[[ "$(jq -er '.patched_commit' "${build_json}")" == "${PATCHED_COMMIT}" ]] ||
  die 'generated vendor commit changed'
[[ "$(jq -er '.patch_sha256' "${build_json}")" == "${PATCH_SHA256}" ]] ||
  die 'observer patch changed'
jq -e '
  .purpose == "vendor-runtime-provenance-full-link-compile-review-only" and
  .build_mode == "provenance-observer" and
  .normal_patch_application == true and .config_delta_exact == true and
  .dct_project == "k97v1_64_bsp" and .dct_project_matches_config == true and
  .full_kernel_link == true and .unresolved_symbol_count == 0 and
  .hardware_write == "none" and .cpu8_cpu9_admission == "closed" and
  .boot_candidate == false
' "${build_json}" >/dev/null || die 'compile-only provenance contract changed'
[[ "$(sha256sum "${kernel_field}" | awk '{print $1}')" == "${KERNEL_SHA256}" ]] ||
  die 'kernel field changed'
[[ "$(sha256sum "${active_boot}" | awk '{print $1}')" == \
   "${ACTIVE_BOOT_SHA256}" ]] || die 'known-good Gemian boot input changed'

workdir="$(mktemp -d "${output_parent}/.gemini-provenance-observer.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "${workdir}"; }
trap cleanup EXIT
stage="${workdir}/stage"
replica="${workdir}/replica"
mkdir "${stage}" "${replica}"
raw_name=gemian-runtime-provenance-observer.boot.img

python3 "${assembler}" --active-boot "${active_boot}" \
  --kernel-field "${kernel_field}" --output "${stage}/${raw_name}" \
  >"${stage}/assembly.txt"
python3 "${assembler}" --active-boot "${active_boot}" \
  --kernel-field "${kernel_field}" --output "${replica}/${raw_name}" \
  >"${replica}/assembly.txt"
cmp -s "${stage}/${raw_name}" "${replica}/${raw_name}" ||
  die 'two raw container assemblies differ'
grep -v '^output=' "${stage}/assembly.txt" >"${stage}/analysis.txt"
rm "${stage}/assembly.txt" "${replica}/assembly.txt"

raw_size="$(wc -c <"${stage}/${raw_name}" | tr -d ' ')"
target_size=$((16 * 1024 * 1024))
((raw_size > 0 && raw_size < target_size)) || die 'raw candidate does not fit'
install -m 0600 "${stage}/${raw_name}" "${stage}/boot2-padded.img"
truncate -s "${target_size}" "${stage}/boot2-padded.img"
dd if=/dev/zero of="${replica}/boot2-padded.img" \
  bs=1048576 count=16 status=none
dd if="${replica}/${raw_name}" of="${replica}/boot2-padded.img" \
  bs=1048576 conv=notrunc status=none
cmp -s "${stage}/boot2-padded.img" "${replica}/boot2-padded.img" ||
  die 'independent padded constructions differ'
tail_size=$((target_size - raw_size))
tail -c "${tail_size}" "${stage}/boot2-padded.img" |
  cmp -n "${tail_size}" - /dev/zero >/dev/null || die 'padded tail is not zero'

raw_sha256="$(sha256sum "${stage}/${raw_name}" | awk '{print $1}')"
padded_sha256="$(sha256sum "${stage}/boot2-padded.img" | awk '{print $1}')"
[[ "${raw_sha256}" == "${EXPECTED_RAW_SHA256}" ]] || die 'raw identity changed'
[[ "${padded_sha256}" == "${EXPECTED_PADDED_SHA256}" ]] ||
  die 'padded identity changed'
{
  printf 'experiment=2026-08-14-mt6797-runtime-provenance-observer\n'
  printf 'repository_commit=%s\nsource_commit=%s\npatched_commit=%s\n' \
    "${REPOSITORY_COMMIT}" "${SOURCE_COMMIT}" "${PATCHED_COMMIT}"
  printf 'patch_sha256=%s\npackage_sha256sums=%s\n' \
    "${PATCH_SHA256}" "${PACKAGE_SHA256SUMS}"
  printf 'kernel_field_sha256=%s\nactive_boot_sha256=%s\n' \
    "${KERNEL_SHA256}" "${ACTIVE_BOOT_SHA256}"
  printf 'ramdisk_sha256=%s\nraw_sha256=%s\nraw_size=%s\n' \
    "${ACTIVE_RAMDISK_SHA256}" "${raw_sha256}" "${raw_size}"
  printf 'padded_sha256=%s\npadded_size=%s\n' \
    "${padded_sha256}" "${target_size}"
  printf 'raw_assemblies_identical=yes\npadded_constructions_identical=yes\n'
  printf 'container_review=offline\nboot_candidate=container-review-pending\n'
  printf 'device_access=none\npartition_write=none\nruntime_result=not-tested\n'
} >"${stage}/provenance.txt"
(
  cd "${stage}"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"${stage}/SHA256SUMS"
(cd "${stage}" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'candidate manifest failed'
chmod 0600 "${stage}"/*

output_name="gemian-runtime-provenance-observer-${raw_sha256:0:12}"
artifact="${workdir}/${output_name}"
mv -n "${stage}" "${artifact}"
stage=
output="${output_parent}/${output_name}"
[[ ! -e "${output}" && ! -L "${output}" ]] || die "refusing to overwrite ${output}"
mv -n "${artifact}" "${output}"
rm -rf -- "${replica}"
rmdir "${workdir}"
workdir=
trap - EXIT
printf 'validation=gemian-runtime-provenance-observer-container\n'
printf 'artifact=%s\nraw_sha256=%s\npadded_sha256=%s\n' \
  "${output}" "${raw_sha256}" "${padded_sha256}"
printf 'device_access=none\nruntime_result=not-tested\n'
