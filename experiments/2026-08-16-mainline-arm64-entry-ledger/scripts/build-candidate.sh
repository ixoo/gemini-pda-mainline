#!/usr/bin/env bash

# Source-pin and mechanically derive the exact arm64 entry-ledger candidate
# builder from the reviewed pre-ramoops ledger builder.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=02d0b45f7ddd18f75aedeb76d59b9a2b077860c32b39be10d93fc2726b596097

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-pre-ramoops-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.derived-build-candidate.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Source-pin and mechanically derive the exact pre-ramoops ledger candidate\n# builder",
     "# Source-pin and mechanically derive the exact arm64 entry ledger\n# candidate builder", 1),
    ("ca56f0161f6d67900d0fc58719e9190e7d1bb4a3",
     "98996fdfbf09f8de2a6b86e488defef22fcc7968", 1),
    ("da921x-modules-pre-ramoops-ledger",
     "da921x-modules-arm64-entry-ledger", 1),
    ("7.1.3-gemini-preledger-a", "7.1.3-gemini-entryled-a", 1),
    ("8fbd12d6494c72882daa6b4d49fe2596e38796561b83a6252133c8587c89db5c",
     "37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84", 1),
    ("c68da1d645c750f9d60c4ab067e70bf8da276273d60eca78b72b06e7b70741e4",
     "539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe", 1),
    ("9f93f48aec1e215b07d89d38d8e4a653b041a46a0df939d542cc11e7e65efbca",
     "e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323", 1),
    ("9832806c73e8ae2b10f139bdac9bb4e11722df76bea216c2e49422ff496f4f7c",
     "dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec", 1),
    ("49b9c33a0dbb619e978b59bea22bfb89b2b884e4843d9236484a7f8520871812",
     "88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee", 1),
    ("c3fe6adb07c6ca5e93187a00fb141391a1516e2f4673bffccd20a61958e07808",
     "a9d2f7d81b61eab7dd3afbaba715778ea2785088bf4d7b098043a803c8e86ce5", 1),
    ("00455398cf1ffa3f57ad5083322e5541b0a58dbdec9ff63883b1427990cff8c3",
     "1249d907795ab80c5a290887847e497bf672e5bdf2c7617096a1209db464341c", 1),
    ("ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f",
     "a81939b41a64a362744580bec559baecb3fe13938187f34b3f1b9ad5f09527f2", 1),
    ('\\\\"readonly RAW_SIZE=6877184\\\\"',
     '\\\\"readonly RAW_SIZE=6879232\\\\"', 1),
    ("gemini-preledg", "gemini-entryled", 1),
    ("gemini-mt6797-pre-ramoops-ledger.boot.img",
     "gemini-mt6797-arm64-entry-ledger.boot.img", 1),
    (".pre-ramoops-ledger.XXXXXXXX", ".arm64-entry-ledger.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-pre-ramoops-ledger",
     "experiment=2026-08-16-mainline-arm64-entry-ledger", 1),
    ("runtime_hypothesis=four-stage-pre-ramoops-ledger-localization",
     "runtime_hypothesis=four-stage-arm64-entry-ledger-localization", 1),
    ("candidate-pre-ramoops-ledger-${RAW_SHA256:0:8}",
     "candidate-arm64-entry-ledger-${RAW_SHA256:0:8}", 1),
    ("validation=pre-ramoops-ledger-candidate-build",
     "validation=arm64-entry-ledger-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
        )
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
