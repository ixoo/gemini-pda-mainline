#!/usr/bin/env bash

# Source-pin the proven Android-v0/LK candidate assembler and specialize it
# for the exact one-shot protected-clock package, DT, and evidence contract.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=390964a7a783a5ff73a3c638fe9785fb48fdef86cfffdf545f48f12444315505

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source candidate builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source candidate builder identity changed'

derived="$(mktemp "$script_dir/.derived-build-candidate-protected-clock.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Assemble the exact read-free clock-entry kernel with the serviceability DT\n# whose only additional change enables the clock-backend platform node.",
     "# Assemble the exact one-shot protected-clock kernel with the serviceability DT.\n# Only the clock backend and clock-only observer are enabled in the candidate DT.", 1),
    ("d8d98fccee89a77fd5a6bc1da3f55cb3d1366b60", "da8cad285d7c92d7dcd1d0cecc104d2f8908308a", 1),
    ("da921x-clock-entry-first-dmesg", "da921x-protected-clock-first-dmesg-call", 1),
    ("7.1.3-gemini-clock-entry-first-dmesg", "7.1.3-gemini-clock-one-read", 1),
    ("984acb29964a7e111da333d457d1bea48c6952cad2fd95c61b9bedf89d1d0c0e", "2a3a5507231d1a559ec0aa2b774cf2f2835347dd4cc55c677149edc93d251e77", 1),
    ("fd5e77c8194834b5da39f397bea2d4873ad8372e2802c8b6ec640518407b430e", "7e53cd8f5c1c0cd4b988e31cbccbd43a9d3c3d62b98052f87e57486d642ca544", 1),
    ("7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100", "31f72bcda3af4edb61d3fe18bcbaec50bef740e507b497ea617df5dd52ab772f", 1),
    ("0a19f77a527e15997430311358e5ae499271eb03573cf6785b2dffdaf52427a7", "0a671868f7be2994d79f294c606f2defe47f6a71824db6d3e3eb2a5444367437", 1),
    ("df7f396405c06aca97b8ebe866bb86cd17459636a83affd8f35220d28c0af099", "e6cec0c9ae786c3578dcaf9ee790b7c9c8638e084aa9350ea5e928b06fba0a7c", 1),
    ("7e3e5c81e128b4a5b565fe47d8186b19b7c663f59b3ed266d95ed02d9a6e30bd", "77bef6f2d7e185bca8f14b448da1872ae79e357bfa5fded849da0c885259bf5e", 1),
    ("37a41e9dd67235e154f918e4f7db930dbbe8566448c6afd4f1a1de2e49b92f5e", "fdd17c87ecfac4f1ba786540f65f38f90c495cc0479df7e4a21d7c9a16a8f0f4", 1),
    ("251e792573bd9961d3f2b90563cff85d851c6502008d97e1ae502fbacda49b83", "d71c1f7e1102c8326f685f5df762de14153ba3cd204a2f9c16a865f068211573", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6", 1),
    ("gemini-clkfdm", "gemini-clk1read", 1),
    ("gemini-mt6797-clock-entry-first-dmesg.boot.img", "gemini-mt6797-protected-clock-first-dmesg.boot.img", 1),
    ("clock-entry serviceability DTB", "protected-clock serviceability DTB", 1),
    ("portable-fetched-clock-entry-first-dmesg-package", "portable-fetched-protected-clock-first-dmesg-package", 1),
    (".clock-entry-first-dmesg.XXXXXXXX", ".protected-clock-first-dmesg.XXXXXXXX", 1),
    ("experiment=2026-08-23-mainline-clock-backend-first-dmesg-entry", "experiment=2026-08-23-mainline-protected-clock-first-dmesg-call", 1),
    ("control_dtb_source=runtime-proven-serviceability-plus-clock-status-okay", "control_dtb_source=runtime-proven-serviceability-plus-single-owner-clock-and-clock-only-observer", 1),
    ("runtime_hypothesis=clock-driver-registration-and-read-free-probe-entry", "runtime_hypothesis=exactly-one-handoff-owned-protected-clock-snapshot-returns", 1),
    ("candidate-clock-entry-first-dmesg-${RAW_SHA256:0:8}", "candidate-protected-clock-first-dmesg-${RAW_SHA256:0:8}", 1),
    ("clock-backend-first-dmesg-candidate-build", "protected-clock-first-dmesg-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

old = '''for gate in \\
\t'CONFIG_MODULES=y' \\
\t'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \\
\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \\
\t'CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y' \\
\t'CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION=y' \\
\t'# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set' \\
\t'# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set' \\
\t'# CONFIG_MTK_MT6797_A72_POWER is not set' \\
\t'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \\
\t'# CONFIG_KUNIT is not set' \\
\t'CONFIG_LOCALVERSION="-gemini-clock-entry-first-dmesg"'; do
'''
new = '''for gate in \\
\t'CONFIG_MODULES=y' \\
\t'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \\
\t'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \\
\t'CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y' \\
\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \\
\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y' \\
\t'CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION=y' \\
\t'# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set' \\
\t'# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set' \\
\t'# CONFIG_MTK_MT6797_A72_POWER is not set' \\
\t'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \\
\t'# CONFIG_KUNIT is not set' \\
\t'CONFIG_LOCALVERSION="-gemini-clock-one-read"'; do
'''
if text.count(old) != 1:
    raise SystemExit("unsafe candidate derivation: configuration gate block changed")
text = text.replace(old, new)

old = '''for symbol in PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION \\
\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\
\tPSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER \\
\tMTK_MT6797_PROTECTED_READBACK_OBSERVER; do
'''
new = '''for symbol in PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION \\
\tPSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \\
\tPSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \\
\tPSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION; do
'''
if text.count(old) != 1:
    raise SystemExit("unsafe candidate derivation: forbidden configuration block changed")
text = text.replace(old, new)

start = text.index("for marker in \\\n\t'GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1")
end = text.index("\n\nworkdir=", start)
markers = '''for marker in \\
\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A checkpoint=before-clock slot=1 crc32=183854b2' \\
\t'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A checkpoint=after-clock slot=2 crc32=d14b85aa' \\
\t'GEMINI_PROTECTED_READBACK_V1 clock ret=%d abi=%u generation=%llu muxsel=0x%08x ckdiv=0x%08x' \\
\t'GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0'; do
\t[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
\t\tdie "record or runtime marker is not unique: $marker"
done
for forbidden in \\
\t'GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d' \\
\t'GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A' \\
\t'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A' \\
\t'GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1' \\
\t'run-same-value-write-20260819-a' 'GAEL-20260816-A'; do
\t! grep -aFq "$forbidden" "$image" || die "forbidden Image token returned: $forbidden"
done'''
text = text[:start] + markers + text[end:]

old = '''\tprintf 'runtime_hypothesis=exactly-one-handoff-owned-protected-clock-snapshot-returns\\n'
\tprintf 'retained_record_commits_expected=maximum-2\\n'
\tprintf 'protected_clock_reads_expected=0\\nbigidvfs_reads_expected=0\\n'
\tprintf 'mapped_mmio_transactions_expected=0\\nclock_enables_expected=0\\n'
\tprintf 'DA921x_register_data_writes_expected=0\\ncpu8_cpu9_admission=closed\\n'
'''
new = '''\tprintf 'runtime_hypothesis=exactly-one-handoff-owned-protected-clock-snapshot-returns\\n'
\tprintf 'retained_record_commits_expected=maximum-2\\n'
\tprintf 'protected_clock_reads_expected=1\\nbigidvfs_reads_expected=0\\n'
\tprintf 'protected_clock_caller_retries_expected=0\\n'
\tprintf 'cspm_transaction_semantics=one-bounded-handoff-owned-read-with-existing-semaphore-poll\\n'
\tprintf 'mapped_clock_mmio_read_snapshots_expected=1\\nclock_enable_disable_pairs_expected=1\\n'
\tprintf 'secure_calls_expected=0\\nDA921x_register_data_writes_expected=0\\n'
\tprintf 'cpu8_cpu9_admission=closed\\n'
'''
if text.count(old) != 1:
    raise SystemExit("unsafe candidate derivation: provenance transaction block changed")
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
