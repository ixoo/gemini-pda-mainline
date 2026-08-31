#!/usr/bin/env bash

# Source-pin the proven P27-repair assembler and retarget only the isolation
# result repair package, provenance leaf, exact candidate identities, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c67c23ea547dffebd0c6ee011ee92770f9e5f8806a7ef057fff0c11c77a21c92
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-p27-held-result-contract-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-isolation-held-result-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("870980dd907856f62c021ddbf8b1b9e7d4c3658e", "62557cd201438802cbbc0034e7635f16a716b191", 1),
    ("335e89cc31c99b85d891c2e54566024e5789f90437335e17d75fba493d959fc4", "d806a4900bc005c02a2470c2617700493b3e6a0c7ceed89e1e903b39227d6368", 1),
    ("9c9a160644106e03cc6be4e86190f9156cde3adbc9d6e8c28a99d4d862ba1eac", "387a36725b7769a87228408c2735ae883e0b1f9393f99e61674136832fceae22", 1),
    ("3d093478a19b54c89c25c904beb29558b031f0912a8561e1ba7f52edab251c08", "9cd410101eb8e3e7470b9d2b777bf8fa96a9bc0050f3f55d7bf57fd7a0a936cc", 1),
    ("6d07112316ae6098c3a0d44bbd6f52b764fd921b52724204f4e71d56487e57f4", "bb206991024a8b9f0b477b326b07bd61e880ebac964ed331495cf857f0225636", 1),
    ("8ac4ba2d4c08496251e05427980d2a607cf8f3389b84bdb1a76c5cc3cbb81400", "dba7276e80a2b7a00606ee7ed3c78588c20b9aed321cfb7fd9b403e05087571b", 1),
    ("ded617adef441801834d37256c9ef954f035a089bf9b2eb0c4faacd2c0acc8d2", "57fb4aae9cf3f5767e7b3d8ae95238d806e3ed55bfe2298d587f7fc550a3c7dd", 1),
    ("df243481ab19dec4d6899c3478391140cc6602f5a5435e11229f7afb0d68ebb3", "53b52ffcbe700866e4d96c3ae84e6cc98910ae0dc45a000c815f212a4ba9662f", 1),
    ("fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5", "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", 1),
    ("f8 7a b4 d9 ed 83 d 42 64 68 38 28 65 94 4e f8 d9 7c bd 40 a4 fc b5 96 15 a2 b4 aa 6b b6 f6 46", "29 5d 1b 4e b6 2c bf 1f ad d2 c2 c8 3c db 15 12 a4 52 1a 23 4d 72 84 27 13 21 f9 48 a1 9e ce 16", 1),
    ("gemini-mt6797-a72-p27-held-result-contract-repair.boot.img", "gemini-mt6797-a72-isolation-held-result-contract-repair.boot.img", 1),
    (".derived-build-a72-p27-held-result-repair-inner.XXXXXXXX", ".derived-build-a72-isolation-held-result-repair-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-p27-held-result-contract-repair", "experiment=2026-08-30-mainline-a72-isolation-held-result-contract-repair", 1),
    ("validation=p27-held-result-contract-repair-package", "validation=isolation-held-result-contract-repair-package", 1),
    ('output_name="candidate-a72-p27-held-result-contract-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-isolation-held-result-contract-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-p27-held-result-contract-repair-build", "validation=a72-isolation-held-result-contract-repair-build", 1),
    ("unsafe held-result repair candidate derivation", "unsafe isolation-result repair candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe isolation-result repair candidate derivation: expected "
            f"{count}, found {actual}: {old}"
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
