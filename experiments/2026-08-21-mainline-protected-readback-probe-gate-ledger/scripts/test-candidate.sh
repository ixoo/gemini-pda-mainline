#!/usr/bin/env bash

# Source-pin the independent call-ledger container validator and specialize it
# for the exact probe/gate candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0bfe8d58402dbf524df1279e92ffc3b008398c557cc1ae9d446bf24b7b0e011b

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-protected-readback-call-ledger/scripts/test-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.protected-readback-probe-gate-validator.XXXXXXXX")"
cleanup() { [[ ! -f "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

replacements = (
    (
        "# specialize it for the exact call-ledger candidate.",
        "# specialize it for the exact probe/gate candidate.",
        1,
    ),
    (
        "Independently validate the exact protected-readback call-ledger candidate.",
        "Independently validate the exact protected-readback probe/gate candidate.",
        1,
    ),
    ("KERNEL_FIELD_SIZE = 5_561_048", "KERNEL_FIELD_SIZE = 5_561_139", 1),
    (
        'RAW_SHA256 = \\"199e618af834d140746c367f7789407da39ce61dd2b1f9bab40fe63150285c17\\"',
        'RAW_SHA256 = \\"c04de4167c392e046cfad0aad30b2801781a44b8963f9a37dbc69d8b0baca233\\"',
        1,
    ),
    (
        'PADDED_SHA256 = \\"3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a\\"',
        'PADDED_SHA256 = \\"6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62\\"',
        1,
    ),
    (
        'IMAGE_SHA256 = \\"5b8682eb9eb5ed81ad238d1e265d0200c58fc009b1c9b1053531641ff721c60b\\"',
        'IMAGE_SHA256 = \\"9b314fcf4b5403ba696889d4f0b210ff68dc6dbc413faf6287ce425315e2075a\\"',
        1,
    ),
    (
        'IMAGE_GZIP_SHA256 = \\"2beabfc3f40f635e27d9085604416b301024098ad2a1ad4cebe99ac8000a5c59\\"',
        'IMAGE_GZIP_SHA256 = \\"7a0a380edc6fb7a048b5c6e4afb88239f8c335587944a5c70291ffd362deb893\\"',
        1,
    ),
    (
        'CONFIG_SHA256 = \\"a4565fec73f962a0ab1b0e7856b426b538c9fb9023f29fd112f31b2abf45298b\\"',
        'CONFIG_SHA256 = \\"621c58329ba311006c1d5910614d45e11ef1b959faff4e81618664b0e3d20b77\\"',
        1,
    ),
    (
        'SYSTEM_MAP_SHA256 = \\"a84c97a82aa81aef2c5a02fd95fbb8060fb3f789a34068fc2bb89c52feddd313\\"',
        'SYSTEM_MAP_SHA256 = \\"38a32ac2ebb9e718281c6e47c2f6518a97eb2cd1daad5bab3e169c152d145e57\\"',
        1,
    ),
    (
        'BUILD_JSON_SHA256 = \\"63e67a7895fc26d2ecfc4c2b0cd62d6bbf23939bf3a2de83e16c54619f496b80\\"',
        'BUILD_JSON_SHA256 = \\"966babff6b53cebe09e6228320b679ddeb75f3c904b3e74cb8621f1fcc700519\\"',
        1,
    ),
    (
        'BOOT_FILE = \\"gemini-mt6797-protected-readback-ledger.boot.img\\"',
        'BOOT_FILE = \\"gemini-mt6797-protected-readback-probe-gate.boot.img\\"',
        1,
    ),
    (
        '== \\"36027e9e5381cae6223ad64abe2a9e2368f0aba9\\"',
        '== \\"1343e6cac5807a48e8b7813b28df7094b814a01a\\"',
        1,
    ),
    (
        'provenance[\\"build_profile\\"] == \\"protected-readback-call-ledger\\"',
        'provenance[\\"build_profile\\"] == \\"protected-readback-probe-gate-ledger\\"',
        1,
    ),
    (
        'provenance[\\"kernel_release\\"] == \\"7.1.3-gemini-protected-readback-ledger\\"',
        'provenance[\\"kernel_release\\"] == \\"7.1.3-gemini-protected-readback-probe-gate\\"',
        1,
    ),
    (
        "validation=protected-readback-call-ledger-candidate",
        "validation=protected-readback-probe-gate-candidate",
        1,
    ),
    (
        "runtime_markers=before-clock,after-clock,clock,bigidvfs,complete",
        "runtime_markers=probe-enter,gate-passed,clock,bigidvfs,complete",
        1,
    ),
    (
        "GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=before-clock slot=173 crc32=08f2fe56",
        "GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B checkpoint=probe-enter slot=173 crc32=06a9b43b",
        1,
    ),
    (
        "GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A checkpoint=after-clock slot=174 crc32=e477a18e",
        "GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B checkpoint=gate-passed slot=174 crc32=41e86ca4",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe validator derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

old = r'''        '        b"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\\n",\n'
'''
new = old + r'''        '        b"CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER=y\\n",\n'
'''
if text.count(old) != 1:
    raise SystemExit("unsafe validator mode-gate insertion")
text = text.replace(old, new)

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
