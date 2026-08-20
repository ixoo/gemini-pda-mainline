#!/usr/bin/env bash

# Source-pin and derive the exact Gate-6 same-value-write boot candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6bd48a4e1647db97535f0d562c52acbc3323af7753753fe0f873cce89f2a7efe

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-18-mainline-da921x-runtime-preflight-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source builder is missing or unsafe'
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
    ("runtime-triggered read-only preflight/ledger candidate",
     "Gate-6 same-value-write candidate", 1),
    ("a3679cd38937bf9a7c9e25d19385e8f992506370",
     "7c012d736f78898be08bfd8430a25c8708a62e1d", 1),
    ("da921x-runtime-preflight-ledger", "da921x-same-value-write", 3),
    ("2026-08-18-mainline-da921x-same-value-write",
     "2026-08-19-mainline-da921x-same-value-write-implementation", 1),
    ("7.1.3-gemini-da921x-preflight-rt",
     "7.1.3-gemini-da921x-same-write", 1),
    ("617dec242ecc82222d6dc05df60e534c7e63fd84fad249504378901f094d6d11",
     "595056ac4cee9ff0a5b79287dca18bdc24f48374ffa7a3ef2647a0255cf1773c", 1),
    ("a33fc7b29ed09e1d30a79447fc3ef9cc70775f31d5085c93ddfc07a103f546b0",
     "9327bd97af0ef8b2470c6eb769b0f96b562b855d4049289d3e0890c2739a5b29", 1),
    ("2241843a550091422381ec59b4b57c7abc8d9ae757c2956edbd0acb5a11a19b3",
     "61590965540ad27624b64c8906a58f87d36ed15821e769f5ec93871f39695614", 1),
    ("1b2759aa513d73678e8f421c223e399ea0e9dcb8042029c26848b84e3f68d9f6",
     "321606b03dbeff1facfe8c9fa1404550457458eb862320054d0e1d823b8a91b2", 1),
    ("7a99af2e89749b515448fa8703a93fa54a11c64c654cd187e24af062037dcee7",
     "4c39328d8a75d173ac262ba07159064d1069a0d1097964a23a48aaef40e19bd2", 1),
    ("cc94db055cbde031701f80de97f6ef9f6ed5f99cd4caf1b8d023a7a1c7eb6e99",
     "e6932a0803b69071b64fc7c4a4ec8fa98c08112eec1e06f2c48a039c54ec5e20", 1),
    ("5f1ce652cee1fe77a4d963849dd047a9fbed6b0a25ef8fb48bcde74cb30b665d",
     "b84f3ba8d86ea9f1b34234794e71be786853da7d1942ce755b175f6c7289509d", 1),
    ("af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296",
     "b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22", 1),
    ("readonly RAW_SIZE=6893568", "readonly RAW_SIZE=6895616", 1),
    ("gemini-prefrt", "gemini-da921x-w", 1),
    ("gemini-mt6797-da921x-runtime-preflight.boot.img",
     "gemini-mt6797-da921x-same-value-write.boot.img", 1),
    ("candidate-mainline-da921x-runtime-preflight-${RAW_SHA256:0:8}",
     "candidate-mainline-da921x-same-value-write-${RAW_SHA256:0:8}", 1),
    ("mt6797-gemini-pda-da921x-runtime-preflight.dtb",
     "mt6797-gemini-pda-da921x-same-value-write.dtb", 1),
    ("    (\"DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads\",\n",
     "    (\"DA921x_register_data_writes_expected=0\",\n"
     "     \"DA921x_register_data_writes_expected=1-exact-0xda-0x46\", 2),\n"
     "    (\"DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads\",\n", 1),
    ("one-shot-triggered-preflight-reads",
     "one-shot-same-value-write-with-readbacks", 1),
    ("I2C6_ledger_posttrigger_entries=30",
     "I2C6_ledger_posttrigger_entries=32", 1),
    ("retain-exact-20-entry-ledger-before-one-shot-read-only-preflight",
     "retain-exact-20-entry-ledger-before-one-shot-same-value-write", 1),
    ("read-only-I2C6-ledger-plus-runtime-triggered-preflight",
     "ledger-v2-plus-bounded-same-value-write", 1),
    ("mainline-da921x-runtime-preflight-candidate-build",
     "mainline-da921x-same-value-write-candidate-build", 1),
    ("mainline-da921x-runtime-preflight-wrapper",
     "mainline-da921x-same-value-write-wrapper", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
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
