#!/usr/bin/env bash

# Source-pin and derive the exact runtime-triggered DA921x preflight candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d009349c0d8446af61e0733e9752bcce88cfed648f8c94ef0e8ed40ff9672b55

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/scripts/build-candidate.sh"
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
    ("read-only preflight/ledger candidate",
     "runtime-triggered read-only preflight/ledger candidate", 1),
    ("f2837f05083bf2ee5e3caa28b3415d529ecd104b",
     "a3679cd38937bf9a7c9e25d19385e8f992506370", 2),
    ("da921x-readonly-preflight-ledger",
     "da921x-runtime-preflight-ledger", 3),
    ("2026-08-17-mainline-da921x-runtime-preflight-ledger",
     "2026-08-18-mainline-da921x-runtime-preflight-ledger", 1),
    ("7.1.3-gemini-da921x-preflight",
     "7.1.3-gemini-da921x-preflight-rt", 2),
    ("2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04",
     "617dec242ecc82222d6dc05df60e534c7e63fd84fad249504378901f094d6d11", 1),
    ("c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34",
     "a33fc7b29ed09e1d30a79447fc3ef9cc70775f31d5085c93ddfc07a103f546b0", 1),
    ("28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27",
     "2241843a550091422381ec59b4b57c7abc8d9ae757c2956edbd0acb5a11a19b3", 1),
    ("4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a",
     "1b2759aa513d73678e8f421c223e399ea0e9dcb8042029c26848b84e3f68d9f6", 1),
    ("939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb",
     "7a99af2e89749b515448fa8703a93fa54a11c64c654cd187e24af062037dcee7", 1),
    ("a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578",
     "cc94db055cbde031701f80de97f6ef9f6ed5f99cd4caf1b8d023a7a1c7eb6e99", 1),
    ("4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7",
     "5f1ce652cee1fe77a4d963849dd047a9fbed6b0a25ef8fb48bcde74cb30b665d", 2),
    ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
     "af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296", 2),
    ("readonly RAW_SIZE=6891520", "readonly RAW_SIZE=6893568", 1),
    ("gemini-preflt", "gemini-prefrt", 1),
    ("gemini-mt6797-da921x-preflight.boot.img",
     "gemini-mt6797-da921x-runtime-preflight.boot.img", 1),
    ("candidate-mainline-da921x-preflight-${RAW_SHA256:0:8}",
     "candidate-mainline-da921x-runtime-preflight-${RAW_SHA256:0:8}", 2),
    ("mt6797-gemini-pda-da921x-preflight.dtb",
     "mt6797-gemini-pda-da921x-runtime-preflight.dtb", 1),
    ("\t'CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y' \\\n",
     "\t'# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set' \\\n"
     "\t'CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y' \\\n", 1),
    ("DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads",
     "DA921x_runtime_operations=identity-reads,provider-reads,one-shot-triggered-preflight-reads", 1),
    ("I2C6_ledger_expected_entries=30",
     "I2C6_ledger_pretrigger_entries=20\\nI2C6_ledger_posttrigger_entries=30", 2),
    ("runtime_hypothesis=exact-I2C6-ledger-plus-stable-read-only-DA921x-preflight",
     "runtime_hypothesis=retain-exact-20-entry-ledger-before-one-shot-read-only-preflight", 1),
    ("kernel_delta_from-proven-provider=read-only-I2C6-ledger-plus-preflight",
     "kernel_delta_from-proven-provider=read-only-I2C6-ledger-plus-runtime-triggered-preflight", 1),
    ("mainline-da921x-readonly-preflight-candidate-build",
     "mainline-da921x-runtime-preflight-candidate-build", 1),
    ("mainline-da921x-readonly-preflight-wrapper",
     "mainline-da921x-runtime-preflight-wrapper", 1),
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
