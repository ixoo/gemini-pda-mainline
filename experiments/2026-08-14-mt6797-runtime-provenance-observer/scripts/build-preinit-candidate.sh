#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
  printf 'usage: %s --bundle DIR --active-boot FILE --corrected-candidate DIR --output-parent DIR\n' "$0"
}

bundle=
active_boot=
corrected_candidate=
output_parent=
while (($#)); do
  case "$1" in
  --bundle|--active-boot|--corrected-candidate|--output-parent)
    (($# >= 2)) || die "$1 requires a value"
    case "$1" in
    --bundle) bundle=$2 ;;
    --active-boot) active_boot=$2 ;;
    --corrected-candidate) corrected_candidate=$2 ;;
    --output-parent) output_parent=$2 ;;
    esac
    shift 2
    ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; die "unknown argument: $1" ;;
  esac
done
[[ -n "${bundle}" && -n "${active_boot}" && -n "${corrected_candidate}" && \
   -n "${output_parent}" ]] || { usage >&2; exit 2; }

for command in awk basename chmod cmp dd dirname find grep install jq mkdir \
  mktemp mv python3 rm sha256sum sort tail tr truncate wc xargs; do
  command -v "${command}" >/dev/null 2>&1 || die "missing command: ${command}"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bundle="$(cd -- "${bundle}" && pwd -P)"
active_boot="$(cd -- "$(dirname -- "${active_boot}")" && pwd -P)/$(basename -- "${active_boot}")"
corrected_candidate="$(cd -- "${corrected_candidate}" && pwd -P)"
mkdir -p "${output_parent}"
output_parent="$(cd -- "${output_parent}" && pwd -P)"
assembler="${script_dir}/assemble-preinit.py"
kernel_field="${bundle}/outputs/Image.gz-dtb"
corrected_raw="${corrected_candidate}/provenance-observer-vendor-rndis.boot.img"

readonly REPOSITORY_COMMIT=b2d638fc2aec342e9641099982c4a4f202b54ef5
readonly SOURCE_COMMIT=d388d350cb2dda8f23b99be6fa5db9628896e87f
readonly PARENT_COMMIT=f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24
readonly PATCHED_COMMIT=2dbf7be3999120f297aedb9842bce320d759d26e
readonly PARENT_PATCH_SHA256=3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11
readonly RECOVERY_PATCH_SHA256=0ddf2b5b28bb0957a467d38bfece553b89bf6b81c85c365f293d00b94efbd3d1
readonly PACKAGE_MANIFEST_SHA256=8fee014106f2efdf2944227f9615bb6493d63da79b947e34e1d612a32cbd3862
readonly CORRECTED_MANIFEST_SHA256=ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a
readonly ASSEMBLER_SHA256=b7a02f4df0c8558124903be1ea5871fd8d5a1a545ff2292222d0bb5a25ba25d3
readonly ACTIVE_BOOT_SHA256=1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513
readonly CORRECTED_RAW_SHA256=1d303dda10b47248f51a1fb2c8f3b1a7b8098522536f4f54ff763c17e75ff310
readonly KERNEL_SHA256=5a8db7fba3b4eb83932042e1105039157d4c8bb70c5794c00b03f9ac46526725
readonly RAMDISK_SHA256=86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358
readonly APPENDED_DTB_SHA256=d70cb5f679ca1135280b80cfc0308e9c4c74bf6a5b8b1a0a8c281a50d4a3d787
readonly RAW_SHA256=455a85907827e823fea039a721b55f092783aa30130361ebfebef0d07c7eed11
readonly PADDED_SHA256=99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7

for input in "${assembler}" "${active_boot}" "${corrected_raw}" \
  "${corrected_candidate}/SHA256SUMS" "${kernel_field}" \
  "${bundle}/SHA256SUMS" "${bundle}/provenance/build.json"; do
  [[ -f "${input}" && ! -L "${input}" && -s "${input}" ]] ||
    die "unsafe input: ${input}"
done
[[ "$(sha256sum "${assembler}" | awk '{print $1}')" == "${ASSEMBLER_SHA256}" ]] ||
  die 'pre-init assembler changed'
[[ "$(sha256sum "${bundle}/SHA256SUMS" | awk '{print $1}')" == \
   "${PACKAGE_MANIFEST_SHA256}" ]] || die 'Buildbox manifest changed'
[[ "$(sha256sum "${corrected_candidate}/SHA256SUMS" | awk '{print $1}')" == \
   "${CORRECTED_MANIFEST_SHA256}" ]] || die 'corrected candidate manifest changed'
(cd "${bundle}" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'Buildbox artifact validation failed'
(cd "${corrected_candidate}" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'corrected candidate validation failed'
[[ "$(sha256sum "${active_boot}" | awk '{print $1}')" == \
   "${ACTIVE_BOOT_SHA256}" ]] || die 'active boot changed'
[[ "$(sha256sum "${corrected_raw}" | awk '{print $1}')" == \
   "${CORRECTED_RAW_SHA256}" ]] || die 'corrected observation image changed'
[[ "$(sha256sum "${kernel_field}" | awk '{print $1}')" == "${KERNEL_SHA256}" ]] ||
  die 'pre-init kernel field changed'

build_json="${bundle}/provenance/build.json"
jq -e --arg repository_commit "${REPOSITORY_COMMIT}" \
  --arg source_commit "${SOURCE_COMMIT}" \
  --arg parent_commit "${PARENT_COMMIT}" \
  --arg patched_commit "${PATCHED_COMMIT}" \
  --arg parent_patch_sha256 "${PARENT_PATCH_SHA256}" \
  --arg recovery_patch_sha256 "${RECOVERY_PATCH_SHA256}" '
  .repository_commit == $repository_commit and .repository_dirty == false and
  .purpose == "vendor-runtime-provenance-preinit-full-link-compile-review-only" and
  .build_mode == "provenance-preinit-recovery" and
  .source_commit == $source_commit and .parent_commit == $parent_commit and
  .patched_commit == $patched_commit and
  .parent_patch_sha256 == $parent_patch_sha256 and
  .recovery_patch_sha256 == $recovery_patch_sha256 and
  .normal_patch_application == true and .config_delta_exact == true and
  .observer_config_enabled == true and
  .preinit_recovery_config_enabled == true and
  .full_kernel_link == true and .unresolved_symbol_count == 0 and
  .recovery_deadline_seconds == 120 and .initcall_order_valid == true and
  .reset_action == "bounded-emergency-restart" and
  .dvfsp_hardware_write == "none" and .hardware_write == "reset-only" and
  .cpu8_cpu9_admission == "closed" and .boot_candidate == false
' "${build_json}" >/dev/null || die 'pre-init compile-review contract changed'

workdir="$(mktemp -d "${output_parent}/.provenance-preinit.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "${workdir}"; }
trap cleanup EXIT HUP INT TERM
stage="${workdir}/stage"
replica="${workdir}/replica"
mkdir "${stage}" "${replica}"
raw_name=provenance-preinit-recovery.boot.img
for root in "${stage}" "${replica}"; do
  python3 "${assembler}" --active-boot "${active_boot}" \
    --kernel-field "${kernel_field}" --corrected-raw "${corrected_raw}" \
    --output "${root}/${raw_name}" >"${root}/assembly.txt"
done
cmp -s "${stage}/${raw_name}" "${replica}/${raw_name}" ||
  die 'independent raw assemblies differ'

install -m 0600 "${stage}/${raw_name}" "${stage}/boot2-padded.img"
truncate -s 16777216 "${stage}/boot2-padded.img"
dd if=/dev/zero of="${replica}/boot2-padded.img" bs=1048576 count=16 status=none
dd if="${replica}/${raw_name}" of="${replica}/boot2-padded.img" \
  bs=1048576 conv=notrunc status=none
cmp -s "${stage}/boot2-padded.img" "${replica}/boot2-padded.img" ||
  die 'independent padding constructions differ'
raw_size="$(wc -c <"${stage}/${raw_name}" | tr -d ' ')"
tail_size=$((16777216 - raw_size))
((tail_size > 0)) || die 'raw candidate does not fit boot2'
tail -c "${tail_size}" "${stage}/boot2-padded.img" |
  cmp -n "${tail_size}" - /dev/zero >/dev/null || die 'padding is nonzero'
[[ "$(sha256sum "${stage}/${raw_name}" | awk '{print $1}')" == "${RAW_SHA256}" ]] ||
  die 'raw identity changed'
[[ "$(sha256sum "${stage}/boot2-padded.img" | awk '{print $1}')" == \
   "${PADDED_SHA256}" ]] || die 'padded identity changed'

grep -v '^output=' "${stage}/assembly.txt" >"${stage}/container-analysis.txt"
rm "${stage}/assembly.txt" "${replica}/assembly.txt"
{
  printf 'experiment=2026-08-14-mt6797-runtime-provenance-observer\n'
  printf 'derivative=preinit-recovery-changed-kernel\n'
  printf 'repository_commit=%s\nsource_commit=%s\nparent_commit=%s\npatched_commit=%s\n' \
    "${REPOSITORY_COMMIT}" "${SOURCE_COMMIT}" "${PARENT_COMMIT}" "${PATCHED_COMMIT}"
  printf 'kernel_sha256=%s\ncorrected_raw_sha256=%s\n' \
    "${KERNEL_SHA256}" "${CORRECTED_RAW_SHA256}"
  printf 'corrected_ramdisk_sha256=%s\nappended_dtb_sha256=%s\n' \
    "${RAMDISK_SHA256}" "${APPENDED_DTB_SHA256}"
  printf 'raw_sha256=%s\nraw_size=%s\npadded_sha256=%s\npadded_size=16777216\n' \
    "${RAW_SHA256}" "${raw_size}" "${PADDED_SHA256}"
  printf 'kernel_changed=yes\nappended_dtb_identical_to_corrected=yes\n'
  printf 'ramdisk_identical_to_corrected=yes\nheader_contract_preserved=yes\n'
  printf 'recovery_deadline_seconds=120\nautomatic_restart=one-emergency-restart\n'
  printf 'device_storage_access=none\ndvfsp_hardware_write=none\n'
  printf 'cpu8_cpu9_admission=closed\ndevice_access=none\n'
  printf 'boot_candidate=offline-container-review-pending\nruntime_result=not-tested\n'
} >"${stage}/provenance.txt"
(
  cd "${stage}"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"${workdir}/SHA256SUMS"
mv "${workdir}/SHA256SUMS" "${stage}/SHA256SUMS"
(cd "${stage}" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
  die 'output manifest failed'
chmod 0600 "${stage}"/*

output_name="gemian-runtime-provenance-preinit-${RAW_SHA256:0:12}"
output="${output_parent}/${output_name}"
[[ ! -e "${output}" && ! -L "${output}" ]] || die "refusing to overwrite ${output}"
mv "${stage}" "${output}"
stage=
rm -rf -- "${replica}"
rmdir "${workdir}"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=provenance-preinit-container\n'
printf 'artifact=%s\nraw_sha256=%s\npadded_sha256=%s\n' \
  "${output}" "${RAW_SHA256}" "${PADDED_SHA256}"
printf 'appended_dtb_identical_to_corrected=yes\nramdisk_identical_to_corrected=yes\n'
printf 'device_access=none\nruntime_result=not-tested\n'
