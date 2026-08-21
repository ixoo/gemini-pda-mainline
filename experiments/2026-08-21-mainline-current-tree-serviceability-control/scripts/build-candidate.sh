#!/usr/bin/env bash

# Source-pin the proven external-DTB Android-v0 builder and specialize it for
# the exact current-tree serviceability control identities and closures.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=cb653690a9ab76d52fc40ea808d2df1bce107b19987616857f81b4f20abf3771

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.current-service-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Assemble the exact GAEL kernel with the runtime-proven Stage-27 DTB.",
     "# Assemble the exact current-tree serviceability control candidate.", 1),
    ("98996fdfbf09f8de2a6b86e488defef22fcc7968",
     "27622dfea13e042bd82f036c50664d3b978aee11", 1),
    ("da921x-modules-arm64-entry-ledger", "da921x-current-service-control", 1),
    ("7.1.3-gemini-entryled-a", "7.1.3-gemini-service-ctl", 1),
    ("37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84",
     "cae4361ad7cd4b2515526ff2b11863e4ff1eb8ea788a23cb24409795049c5483", 1),
    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe",
     "9aa5c9ae497314b7ab089ccf6aa7d2cf1bb2ae9239145456603f08439829a9d6", 1),
    ("7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806",
     "b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd", 1),
    ("e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323",
     "fdba1a02f7592febcbf18fc4c32f7edfe8da48d355241109d79901e37a4dd21b", 1),
    ("dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec",
     "39db10ecee35252b5f81fcb52b730f39a30268f6574bed12f55a45e77b92d090", 1),
    ("88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee",
     "7b9d852ad6b4dd524c16ac99878c00dc18ccb6075b49a093706ba61f017ff2a8", 1),
    ("a9d2f7d81b61eab7dd3afbaba715778ea2785088bf4d7b098043a803c8e86ce5",
     "1f59307bdce806bb1576a87266adad1393bcd4512240483ff2cb51848cc98760", 1),
    ("e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086",
     "691ff883f05158c9a62d6629befef93f54ba14e51ff4ed5d8ea97678f2fa5094", 1),
    ("68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67",
     "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3", 1),
    ("readonly RAW_SIZE=6879232", "readonly RAW_SIZE=6895616", 1),
    ("readonly BOOT_NAME=gemini-dtbctl", "readonly BOOT_NAME=gemini-svcctl", 1),
    ("readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-current-service-control.boot.img", 1),
    ("'Stage-27 control DTB'", "'current-tree serviceability DTB'", 1),
    (".lk-handoff-dtb-control.XXXXXXXX", ".current-service-control.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-runtime-proven-dtb-control",
     "portable-fetched-current-tree-serviceability-package", 1),
    ("control_dtb_source=runtime-proven-stage27-lifecycle",
     "control_dtb_source=current-package-plus-exact-proven-serviceability-contract", 2),
    ("experiment=2026-08-16-mainline-lk-handoff-dtb-control",
     "experiment=2026-08-21-mainline-current-tree-serviceability-control", 1),
    ("runtime_hypothesis=stage27_dtb_distinguishes_lk_dtb_processing_from_image_entry",
     "runtime_hypothesis=current-tree-serviceable-with-clock-entry-and-action-paths-disabled", 1),
    ("kernel_delta_from_stopped_gael=none",
     "kernel_delta_from_last-runtime-proven=current-canonical-series-plus-control-config", 1),
    ("dtb_delta_from_stopped_gael=exact-runtime-proven-stage27-dtb",
     "dtb_delta_from-package=exact-proven-serviceability-and-three-window-contract", 1),
    ("candidate-lk-handoff-dtb-control-${RAW_SHA256:0:8}",
     "candidate-current-service-control-${RAW_SHA256:0:8}", 1),
    ("validation=lk-handoff-dtb-control-candidate-build",
     "validation=current-tree-serviceability-control-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_config = r'''grep -qx 'CONFIG_MODULES=y' "$config" || die 'module policy changed'
grep -qx '# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set' "$config" ||
	die 'old ledger leaked into control'
grep -qx 'CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y' "$config" ||
	die 'arm64 entry ledger is absent'
grep -qx '# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set' "$config" ||
	die 'post-ramoops checkpoint leaked into control'
'''
new_config = r'''for gate in \
	'CONFIG_MODULES=y' \
	'CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y' \
	'# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set' \
	'CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y' \
	'CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y' \
	'CONFIG_NVMEM_MTK_ATAG_DEVINFO=y' \
	'CONFIG_CMDLINE_FORCE=y' \
	'# CONFIG_MTK_MT6797_A72_POWER is not set' \
	'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \
	'# CONFIG_REGULATOR_DA9211 is not set' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
for symbol in MTK_MT6797_DVFSP_CLOCK_BACKEND \
	MTK_MT6797_DVFSP_BIGIDVFS_BACKEND \
	MTK_MT6797_PROTECTED_READBACK_OBSERVER \
	PSTORE_GEMINI_PROTECTED_READBACK_LEDGER \
	PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER \
	PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER; do
	! grep -q "^CONFIG_${symbol}=y$" "$config" || die "forbidden configuration enabled: $symbol"
done
grep -qx 'CONFIG_LOCALVERSION="-gemini-service-ctl"' "$config" ||
	die 'unique release changed'
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" ||
	die 'maxcpus=8 closure is absent'
! grep -aFq 'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1' "$image" ||
	die 'clock-entry marker leaked into Image'
! grep -aFq 'run-same-value-write-20260819-a' "$image" ||
	die 'same-value action token leaked into Image'
'''
if text.count(old_config) != 1:
    raise SystemExit("unsafe candidate config-gate replacement")
text = text.replace(old_config, new_config)

old_provenance = "register_data_writes_expected=0\\ncpu8_cpu9_admission=closed"
new_provenance = (
    "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\\n"
    "DA921x_register_data_writes_expected=0\\n"
    "same_value_action_attribute_expected=absent\\n"
    "protected_backend_devices_expected=absent\\n"
    "cpu8_cpu9_admission=closed"
)
if text.count(old_provenance) != 1:
    raise SystemExit("unsafe candidate provenance replacement")
text = text.replace(old_provenance, new_provenance)

output.write_text(text, encoding="utf-8")
PY

chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
