#!/usr/bin/env bash

# Source-pin the proven call-ledger Android-v0 builder and specialize it for
# the exact probe/gate package and candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e1c68f80e047d51a138359dd7c1e5c2dbc9cc26e8aa1acb8b91a67d124716dea

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-protected-readback-call-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.protected-readback-probe-gate-builder.XXXXXXXX")"
cleanup() { [[ ! -f "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

replacements = (
    (
        "# for the exact call-ledger package and candidate identities.",
        "# for the exact probe/gate package and candidate identities.",
        1,
    ),
    (
        "# Assemble the exact protected-readback call-ledger Android-v0/LK candidate.",
        "# Assemble the exact protected-readback probe/gate Android-v0/LK candidate.",
        1,
    ),
    (
        "readonly REPOSITORY_COMMIT=36027e9e5381cae6223ad64abe2a9e2368f0aba9",
        "readonly REPOSITORY_COMMIT=1343e6cac5807a48e8b7813b28df7094b814a01a",
        1,
    ),
    (
        "readonly PROFILE=protected-readback-call-ledger",
        "readonly PROFILE=protected-readback-probe-gate-ledger",
        1,
    ),
    (
        "readonly RELEASE=7.1.3-gemini-protected-readback-ledger",
        "readonly RELEASE=7.1.3-gemini-protected-readback-probe-gate",
        1,
    ),
    (
        "readonly IMAGE_SHA256=5b8682eb9eb5ed81ad238d1e265d0200c58fc009b1c9b1053531641ff721c60b",
        "readonly IMAGE_SHA256=9b314fcf4b5403ba696889d4f0b210ff68dc6dbc413faf6287ce425315e2075a",
        1,
    ),
    (
        "readonly IMAGE_GZIP_SHA256=2beabfc3f40f635e27d9085604416b301024098ad2a1ad4cebe99ac8000a5c59",
        "readonly IMAGE_GZIP_SHA256=7a0a380edc6fb7a048b5c6e4afb88239f8c335587944a5c70291ffd362deb893",
        1,
    ),
    (
        "readonly CONFIG_SHA256=a4565fec73f962a0ab1b0e7856b426b538c9fb9023f29fd112f31b2abf45298b",
        "readonly CONFIG_SHA256=621c58329ba311006c1d5910614d45e11ef1b959faff4e81618664b0e3d20b77",
        1,
    ),
    (
        "readonly SYSTEM_MAP_SHA256=a84c97a82aa81aef2c5a02fd95fbb8060fb3f789a34068fc2bb89c52feddd313",
        "readonly SYSTEM_MAP_SHA256=38a32ac2ebb9e718281c6e47c2f6518a97eb2cd1daad5bab3e169c152d145e57",
        1,
    ),
    (
        "readonly BUILD_JSON_SHA256=63e67a7895fc26d2ecfc4c2b0cd62d6bbf23939bf3a2de83e16c54619f496b80",
        "readonly BUILD_JSON_SHA256=966babff6b53cebe09e6228320b679ddeb75f3c904b3e74cb8621f1fcc700519",
        1,
    ),
    (
        "readonly PACKAGE_MANIFEST_SHA256=38a44be3495dc24df6c7c3d021239cb37ed1a486d021876fde077394ca9f596e",
        "readonly PACKAGE_MANIFEST_SHA256=22a722ce42045f61011555ab468d47f0a0eb7f559a85d5d7b7233a107ecf2489",
        1,
    ),
    (
        "readonly RAW_SHA256=199e618af834d140746c367f7789407da39ce61dd2b1f9bab40fe63150285c17",
        "readonly RAW_SHA256=c04de4167c392e046cfad0aad30b2801781a44b8963f9a37dbc69d8b0baca233",
        1,
    ),
    (
        "readonly PADDED_SHA256=3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        "readonly PADDED_SHA256=6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62",
        1,
    ),
    (
        "readonly BOOT_FILE=gemini-mt6797-protected-readback-ledger.boot.img",
        "readonly BOOT_FILE=gemini-mt6797-protected-readback-probe-gate.boot.img",
        1,
    ),
    (
        ".protected-readback-call-ledger-candidate.XXXXXXXX",
        ".protected-readback-probe-gate-candidate.XXXXXXXX",
        1,
    ),
    (
        "validation=portable-fetched-protected-readback-call-ledger-kernel-package",
        "validation=portable-fetched-protected-readback-probe-gate-kernel-package",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-call-ledger",
        "experiment=2026-08-21-mainline-protected-readback-probe-gate-ledger",
        1,
    ),
    (
        "runtime_hypothesis=retained-checkpoints-bracket-first-protected-clock-call",
        "runtime_hypothesis=retained-checkpoints-mark-probe-entry-and-final-pre-clock-gate",
        1,
    ),
    (
        'output_name=\\"candidate-protected-readback-ledger-${RAW_SHA256:0:8}\\"',
        'output_name=\\"candidate-protected-readback-probe-gate-${RAW_SHA256:0:8}\\"',
        1,
    ),
    (
        "validation=protected-readback-call-ledger-candidate-build",
        "validation=protected-readback-probe-gate-candidate-build",
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
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

old = r'''        "\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \\\n"
'''
new = old + r'''        "\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER=y' \\\n"
'''
if text.count(old) != 1:
    raise SystemExit("unsafe builder mode-gate insertion")
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
