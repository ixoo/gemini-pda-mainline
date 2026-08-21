#!/usr/bin/env bash

# Source-pin and specialize the independent serviceability candidate validator
# for the exact manual-checkpoint Image, configuration, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=332aa7baf063f817552c3394ef55c6448aa19c9703703fc6148475d9520b355a

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/test-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] ||
	die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-validator.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ('"""Independently validate the current-tree serviceability-control candidate."""',
     '"""Independently validate the manual-checkpoint control candidate."""', 1),
    ("RAW_SIZE = 6_895_616", "RAW_SIZE = 6_893_568", 1),
    ("KERNEL_FIELD_SIZE = 4_818_388", "KERNEL_FIELD_SIZE = 4_815_224", 1),
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
    ("gemini-mt6797-current-service-control.boot.img",
     "gemini-mt6797-manual-checkpoint-control.boot.img", 1),
    ("gemini-service-control-dtb-mutation.", "gemini-manual-checkpoint-dtb-mutation.", 1),
    ('b"gemini-svcctl"', 'b"gemini-chkctl"', 1),
    ("validation=mainline-current-tree-serviceability-control-candidate",
     "validation=mainline-manual-checkpoint-control-candidate", 1),
    ('print("clock_entry_writer=absent")',
     'print("manual_checkpoint_writer=present-exact")\n'
     '    print("manual_checkpoint_calls=2")\n'
     '    print("protected_calls=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe validator derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old_config = '''        "CONFIG_MODULES=y\\n",
        "CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y\\n",'''
new_config = '''        "CONFIG_MODULES=y\\n",
        "# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y\\n",'''
if text.count(old_config) != 1:
    raise SystemExit("unsafe required-config replacement")
text = text.replace(old_config, new_config)

old_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-service-ctl\\"\\n",'
new_localversion = '        "CONFIG_LOCALVERSION=\\"-gemini-checkpoint-ctl\\"\\n",'
if text.count(old_localversion) != 1:
    raise SystemExit("unsafe localversion replacement")
text = text.replace(old_localversion, new_localversion)

old_forbidden_config = '''        "MTK_MT6797_PROTECTED_READBACK_OBSERVER",
        "PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",'''
new_forbidden_config = '''        "MTK_MT6797_PROTECTED_READBACK_OBSERVER",
        "PSTORE_GEMINI_PRE_RAMOOPS_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",'''
if text.count(old_forbidden_config) != 1:
    raise SystemExit("unsafe forbidden-config replacement")
text = text.replace(old_forbidden_config, new_forbidden_config)

old_markers = '''    for marker in (
        b"GAEL-20260816-A E0",
        b"GAEL-20260816-A E1",
        b"GAEL-20260816-A E2",
        b"GAEL-20260816-A E3",
    ):
        require(image.count(marker) == 1, f"entry marker changed: {marker!r}")
    for forbidden in (b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1", b"run-same-value-write-20260819-a"):
        require(forbidden not in image, f"forbidden Image token returned: {forbidden!r}")'''
new_markers = '''    for marker in (
        b"GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-first slot=173 crc32=9576f05d",
        b"GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A checkpoint=manual-second slot=174 crc32=c90b9e18",
        b"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1",
    ):
        require(image.count(marker) == 1, f"manual marker changed: {marker!r}")
    for forbidden in (
        b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1",
        b"run-same-value-write-20260819-a",
        b"GAEL-20260816-A",
    ):
        require(forbidden not in image, f"forbidden Image token returned: {forbidden!r}")'''
if text.count(old_markers) != 1:
    raise SystemExit("unsafe Image-marker replacement")
text = text.replace(old_markers, new_markers)

old_symbols = '''    for forbidden in ("same_value", "clock_backend", "protected_readback", "bigidvfs"):
        require(forbidden not in system_map.lower(), f"forbidden symbol returned: {forbidden}")'''
new_symbols = '''    for required in (
        " T gemini_protected_readback_ledger_checkpoint\\n",
        " t gemini_protected_readback_manual_control_init\\n",
        "__initcall__kmod_gemini_protected_readback_ledger__",
    ):
        require(system_map.count(required) == 1, f"manual symbol changed: {required}")
    for forbidden in (
        "same_value",
        "clock_backend",
        "bigidvfs",
        "protected_readback_observer",
    ):
        require(forbidden not in system_map.lower(), f"forbidden symbol returned: {forbidden}")'''
if text.count(old_symbols) != 1:
    raise SystemExit("unsafe System.map replacement")
text = text.replace(old_symbols, new_symbols)

provenance_anchor = '        "DA921x_register_data_writes_expected=0\\n",\n'
provenance_extra = (
    provenance_anchor
    + '        "manual_checkpoint_retained_writes_expected=2\\n",\n'
    + '        "manual_checkpoint_local_full_readbacks_expected=2\\n",\n'
    + '        "protected_calls_expected=0\\n",\n'
)
if text.count(provenance_anchor) != 1:
    raise SystemExit("unsafe provenance insertion")
text = text.replace(provenance_anchor, provenance_extra)

output.write_text(text, encoding="utf-8")
PY

chmod 0700 "$derived"
set +e
python3 "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
