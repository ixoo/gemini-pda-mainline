#!/usr/bin/env bash

# Source-pin the independent protected-readback container validator and
# specialize it for the exact raw-entry-ledger candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=dba6ba9fd59e67afeac5292542ec5d21691cb83735c9c7091b4f3e0ff3d0bbbb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/test-candidate.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

workdir="$(mktemp -d "$repo_root/artifacts/.protected-readback-raw-entry-ledger-validator.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
derived="$workdir/test-candidate.py"

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

replacements = (
    ("Independently validate the exact protected-readback observer candidate.", "Independently validate the exact protected-readback raw-entry-ledger candidate.", 1),
    ("RAW_SIZE = 7_636_992", "RAW_SIZE = 7_639_040", 1),
    ("KERNEL_FIELD_SIZE = 5_560_167", "KERNEL_FIELD_SIZE = 5_562_214", 1),
    ("RAW_SHA256 = \"a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c\"", "RAW_SHA256 = \"0ad7160c2089811f4cdbd1de2a996939ef6273dee02be9e28e372fc2509bf597\"", 1),
    ("PADDED_SHA256 = \"30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a\"", "PADDED_SHA256 = \"7c403a38197f948eff8cc02779ac55d1a172e3898e8663cc98fb8e22a2dc41a9\"", 1),
    ("IMAGE_SHA256 = \"670d963560c654df75f7282959141a0170d04eb2babf26a9ea56869e321b36e3\"", "IMAGE_SHA256 = \"0cdbc3a1f4ee463e1c1b4fc7a8c801e6745036637ea7020987d7ad20a94a1c64\"", 1),
    ("IMAGE_GZIP_SHA256 = \"95d11ee7f26cba1085d24af60f6d60b029fcaf8dfca3e93df5e9bbf55dc013e5\"", "IMAGE_GZIP_SHA256 = \"85fe1316faf413dc1567f6be198681117b99fc0e4728df4b8455bf46c511eb0d\"", 1),
    ("CONFIG_SHA256 = \"6b47a8d9014044ff7a9769304d2bb02cf2c56bcf6407a316f8c6068a51af89f0\"", "CONFIG_SHA256 = \"d97fc1cfe6bd5e18d24a838c65d21156cb54edd82b6932b55d7c4c24f191c293\"", 1),
    ("SYSTEM_MAP_SHA256 = \"71db0783b2504fd6dfaac567b7ca0020e1610ad7ec2a23b3f0d49f569fd5990a\"", "SYSTEM_MAP_SHA256 = \"8abb1c83362c8a3be36fe7b18d8ab0fc1964aaf780922d06389851514d9430a7\"", 1),
    ("BUILD_JSON_SHA256 = \"21de87b3ce8ac54abf23dfd774bc80b722220c2297b08e96eeecb8f0b35006d4\"", "BUILD_JSON_SHA256 = \"28cdea5e2c6da29932ca432391b52ef31cc0303023a6d2b250cd677b1da31c5e\"", 1),
    ("BOOT_FILE = \"gemini-mt6797-protected-readback-ro.boot.img\"", "BOOT_FILE = \"gemini-mt6797-protected-readback-raw.boot.img\"", 1),
    ("== \"1bd49d97673731509f0e2c7dcadbb2f03ed343ca\"", "== \"b7bd915994ce7c2a944cc79669aac0c076ad9541\"", 1),
    ("provenance[\"build_profile\"] == \"protected-readback-observer\"", "provenance[\"build_profile\"] == \"protected-readback-raw-entry-ledger\"", 1),
    ("provenance[\"kernel_release\"] == \"7.1.3-gemini-protected-readback-ro\"", "provenance[\"kernel_release\"] == \"7.1.3-gemini-protected-raw\"", 1),
    ("validation=protected-readback-observer-candidate", "validation=protected-readback-raw-entry-ledger-candidate", 1),
    ("runtime_markers=clock,bigidvfs,complete", "runtime_markers=before-clock,after-clock,clock,complete", 1),
    ('        b"GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d",\n', "", 1),
    ("GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0", "GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe validator derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

insertions = (
    (
        '        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",\n',
        '        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",\n'
        '        b"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y\\n",\n'
        '        b"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\\n",\n'
        '        b"# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER is not set\\n",\n'
        '        b"# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set\\n",\n'
        '        b"# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set\\n",\n'
        '        b"# CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER is not set\\n",\n'
        '        b"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\\n",\n',
        1,
    ),
    (
        '        b"mt6797_readback_observer_driver_init",\n',
        '        b"mt6797_readback_observer_driver_init",\n'
        '        b"gemini_protected_readback_ledger_checkpoint",\n',
        1,
    ),
    (
        '        b"GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0",\n',
        '        b"GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0",\n'
        '        b"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=before-clock slot=173 crc32=08f2fe56",\n'
        '        b"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=after-clock slot=174 crc32=e477a18e",\n',
        1,
    ),
)
for old, new, count in insertions:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe validator insertion: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

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
