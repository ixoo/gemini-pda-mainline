#!/usr/bin/env bash

# Source-pin the proven P27 assembler and retarget only the held-result repair
# package, provenance leaf, exact candidate identities, and experiment labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1d63bb7cf07ed2f20d699b79641f85f230bff468da3c9791c64e663ffaefb025
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-p27-held-result-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("b2ca2e5050d38e060aec61b841fde3d395ff589c", "870980dd907856f62c021ddbf8b1b9e7d4c3658e", 1),
    ("a49cadcdb2443a3167e5b93504340ce13f32c57bcfa1622da552acc823815870", "335e89cc31c99b85d891c2e54566024e5789f90437335e17d75fba493d959fc4", 1),
    ("a89ef31c81a6bc14974023bef037ae72aeca225c2b0279cd95e349d05fbf99ea", "9c9a160644106e03cc6be4e86190f9156cde3adbc9d6e8c28a99d4d862ba1eac", 1),
    ("dc185ae753a4dad86c3d84db8382e3d96cad183bc9120eaafe5fba949ad843a6", "3d093478a19b54c89c25c904beb29558b031f0912a8561e1ba7f52edab251c08", 1),
    ("a3bd117ee2b6d225f9704f3ad75f481d6951b22698e4ceab4546ccc20f74f5f6", "6d07112316ae6098c3a0d44bbd6f52b764fd921b52724204f4e71d56487e57f4", 1),
    ("65785e35cb5511bd8ad27dfefe4cde6e450e7a8db7ddeccbb69f7c712e986fb8", "8ac4ba2d4c08496251e05427980d2a607cf8f3389b84bdb1a76c5cc3cbb81400", 1),
    ("7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7", "ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2", 1),
    ("fbc299b0589de4cf19586436972c8d7219242d14b72589f15d8a2948db1859c3", "df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3", 1),
    ("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", 1),
    ("readonly RAW_SIZE=6959104", "readonly RAW_SIZE=6957056", 1),
    ("16 5f 1b 6d 48 8f 7e 3b 87 a0 3b 68 a1 d8 b4 5 dd 23 44 29 3 a4 fb c4 84 7b 12 14 56 86 1 d5", "f8 7a b4 d9 ed 83 d 42 64 68 38 28 65 94 4e f8 d9 7c bd 40 a4 fc b5 96 15 a2 b4 aa 6b b6 f6 46", 1),
    ("gemini-mt6797-a72-p27-runtime-attribution.boot.img", "gemini-mt6797-a72-p27-held-result-contract-repair.boot.img", 1),
    (".derived-build-a72-p27-attribution-inner.XXXXXXXX", ".derived-build-a72-p27-held-result-repair-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-p27-runtime-attribution", "experiment=2026-08-30-mainline-a72-p27-held-result-contract-repair", 1),
    ("validation=p27-runtime-attribution-package", "validation=p27-held-result-contract-repair-package", 1),
    ('output_name="candidate-a72-p27-runtime-attribution-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-p27-held-result-contract-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-p27-runtime-attribution-build", "validation=a72-p27-held-result-contract-repair-build", 1),
    ("unsafe P27 diagnostic candidate derivation", "unsafe held-result repair candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe held-result repair candidate derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
