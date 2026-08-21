#!/usr/bin/env bash

# Source-pin the current-tree serviceability builder and specialize it for the
# exact independently attributable manual-checkpoint control.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a4b063354893c896687b5f9b37dde1dcd1a4e03eb69e6a4a801bba056e7e73ba

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# the exact current-tree serviceability control identities and closures.",
     "# the exact manual-checkpoint control identities and closures.", 1),
    ("27622dfea13e042bd82f036c50664d3b978aee11",
     "c1d59f3b1783f70e92b4ab27d11c5809f9722869", 1),
    ("da921x-current-service-control", "da921x-manual-checkpoint-control", 1),
    ("7.1.3-gemini-service-ctl", "7.1.3-gemini-checkpoint-ctl", 1),
    ("cae4361ad7cd4b2515526ff2b11863e4ff1eb8ea788a23cb24409795049c5483",
     "e796316372ed008aed2abccd4ed2acadf640105f6a641aff2dd0e48e61245959", 1),
    ("9aa5c9ae497314b7ab089ccf6aa7d2cf1bb2ae9239145456603f08439829a9d6",
     "638a9732387c5b742905ed2b71698be9cda69cfb231ecf8400fb6c2a4ee9800a", 1),
    ("fdba1a02f7592febcbf18fc4c32f7edfe8da48d355241109d79901e37a4dd21b",
     "411692b59d20ed2ed67fd64274e4f980119ff0607df4297342594a13b4ecf321", 1),
    ("39db10ecee35252b5f81fcb52b730f39a30268f6574bed12f55a45e77b92d090",
     "100b461163bfce3e4c15b69c5e7b2effdcfb760942ce4e55b9af61ade82468fa", 1),
    ("7b9d852ad6b4dd524c16ac99878c00dc18ccb6075b49a093706ba61f017ff2a8",
     "39e5bb68be28a2b41fc1250a0271b38b2b9d103afe81961e14b6d6060d5a593e", 1),
    ("1f59307bdce806bb1576a87266adad1393bcd4512240483ff2cb51848cc98760",
     "9d5fef4e7a100813c5d53451ae2a24a5c37efc37db7e19ef34a4f90df146e69d", 1),
    ("691ff883f05158c9a62d6629befef93f54ba14e51ff4ed5d8ea97678f2fa5094",
     "4338ac1ee770ea23087694f7c166226c2297874fd595751d1a235565ecee3805", 1),
    ("7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3",
     "53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c", 1),
    ("readonly RAW_SIZE=6895616", "readonly RAW_SIZE=6893568", 1),
    ("readonly BOOT_NAME=gemini-svcctl", "readonly BOOT_NAME=gemini-chkctl", 1),
    ("readonly BOOT_FILE=gemini-mt6797-current-service-control.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-control.boot.img", 1),
    ("'current-tree serviceability DTB'", "'manual-checkpoint serviceability DTB'", 1),
    (".current-service-control.XXXXXXXX", ".manual-checkpoint-control.XXXXXXXX", 1),
    ("portable-fetched-current-tree-serviceability-package",
     "portable-fetched-manual-checkpoint-control-package", 1),
    ("experiment=2026-08-21-mainline-current-tree-serviceability-control",
     "experiment=2026-08-21-mainline-manual-checkpoint-control", 1),
    ("runtime_hypothesis=current-tree-serviceable-with-clock-entry-and-action-paths-disabled",
     "runtime_hypothesis=shared-writer-completes-two-local-readbacks-on-serviceable-base", 1),
    ("kernel_delta_from_last-runtime-proven=current-canonical-series-plus-control-config",
     "kernel_delta_from-last-runtime-proven=manual-writer-and-late-initcall-only", 1),
    ("dtb_delta_from-package=exact-proven-serviceability-and-three-window-contract",
     "dtb_delta_from-package=exact-proven-serviceability-and-three-window-contract", 1),
    ("candidate-current-service-control-${RAW_SHA256:0:8}",
     "candidate-manual-checkpoint-control-${RAW_SHA256:0:8}", 1),
    ("validation=current-tree-serviceability-control-candidate-build",
     "validation=manual-checkpoint-control-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_config = r'''for gate in \
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
new_config = r'''for gate in \
	'CONFIG_MODULES=y' \
	'# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
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
	PSTORE_GEMINI_PRE_RAMOOPS_LEDGER \
	PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER \
	PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER; do
	! grep -q "^CONFIG_${symbol}=y$" "$config" || die "forbidden configuration enabled: $symbol"
done
grep -qx 'CONFIG_LOCALVERSION="-gemini-checkpoint-ctl"' "$config" ||
	die 'unique release changed'
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" ||
	die 'maxcpus=8 closure is absent'
for marker in \
	'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-first slot=173 crc32=9576f05d' \
	'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-second slot=174 crc32=c90b9e18' \
	'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "manual-checkpoint marker is not unique: $marker"
done
for forbidden in 'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1' \
	'run-same-value-write-20260819-a' 'GAEL-20260816-A'; do
	! grep -aFq "$forbidden" "$image" || die "forbidden Image token returned: $forbidden"
done
'''
if text.count(old_config) != 1:
    raise SystemExit("unsafe candidate config-gate replacement")
text = text.replace(old_config, new_config)

marker_anchor = "text = text.replace(old_config, new_config)\n\nold_provenance = "
marker_insertion = '''text = text.replace(old_config, new_config)

old_markers = r\'''for marker in 'GAEL-20260816-A E0' 'GAEL-20260816-A E1' \\
\t'GAEL-20260816-A E2' 'GAEL-20260816-A E3'; do
\t[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
\t\tdie "entry-ledger marker is not unique: $marker"
done
\'''
new_markers = r\'''for marker in \\
\t'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-first slot=173 crc32=9576f05d' \\
\t'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-second slot=174 crc32=c90b9e18' \\
\t'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1'; do
\t[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
\t\tdie "manual-checkpoint marker is not unique: $marker"
done
\'''
if text.count(old_markers) != 1:
    raise SystemExit("unsafe candidate marker-gate replacement")
text = text.replace(old_markers, new_markers)

old_provenance = '''
if text.count(marker_anchor) != 1:
    raise SystemExit("unsafe marker-gate insertion anchor")
text = text.replace(marker_anchor, marker_insertion)

old_provenance = r'''new_provenance = (
    "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\\n"
    "DA921x_register_data_writes_expected=0\\n"
    "same_value_action_attribute_expected=absent\\n"
    "protected_backend_devices_expected=absent\\n"
    "cpu8_cpu9_admission=closed"
)'''
new_provenance = r'''new_provenance = (
    "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\\n"
    "DA921x_register_data_writes_expected=0\\n"
    "manual_checkpoint_retained_writes_expected=2\\n"
    "manual_checkpoint_local_full_readbacks_expected=2\\n"
    "protected_calls_expected=0\\n"
    "same_value_action_attribute_expected=absent\\n"
    "protected_backend_devices_expected=absent\\n"
    "cpu8_cpu9_admission=closed"
)'''
if text.count(old_provenance) != 1:
    raise SystemExit("unsafe candidate provenance specialization")
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
