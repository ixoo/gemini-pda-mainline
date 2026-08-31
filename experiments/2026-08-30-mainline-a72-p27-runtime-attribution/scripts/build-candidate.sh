#!/usr/bin/env bash

# Source-pin the proven production assembler and retarget only the P27
# diagnostic package, exact provenance leaf, candidate identities, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=32af830bb12fa7076c8f815fa2d680ac2ea56be11e4eeffa984ae656db3ccd44
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-ready-token-contract-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-p27-attribution.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
size_anchor = '    ("gemini-mt6797-a72-live-a34-predicate-repair.boot.img", "gemini-mt6797-a72-ready-token-contract-repair.boot.img", 1),'
size_replacement = (
    '    ("readonly RAW_SIZE=6955008", "readonly RAW_SIZE=6959104", 1),\n'
    + size_anchor
)
replacements = (
    ("8dc8e806331b1617795eb02aff27df559521e508", "b2ca2e5050d38e060aec61b841fde3d395ff589c", 1),
    ("118e0d8106330055b09d63085cfe27bf8818747bedc9402fbd48d3095e0384ee", "a49cadcdb2443a3167e5b93504340ce13f32c57bcfa1622da552acc823815870", 1),
    ("7553356a12a068c2bf5d917609936b98e7747dc54ce992c9b833121d9756d2c3", "a89ef31c81a6bc14974023bef037ae72aeca225c2b0279cd95e349d05fbf99ea", 1),
    ("671e5cf88bb81c1a8c2990d84ca100640875630d6dcb6886e83811af9b7a65e0", "dc185ae753a4dad86c3d84db8382e3d96cad183bc9120eaafe5fba949ad843a6", 1),
    ("022aa79d1ee3a279fb5c62ca7b5608701fb09a8fefa4c575b5396d9f107bf5ec", "a3bd117ee2b6d225f9704f3ad75f481d6951b22698e4ceab4546ccc20f74f5f6", 1),
    ("9e7f2640efba4c4a448b12887f3ba9084a6988f41a46dc2038c7468d59f9d4e3", "65785e35cb5511bd8ad27dfefe4cde6e450e7a8db7ddeccbb69f7c712e986fb8", 1),
    ("11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526", "7c2f1f76dfc7ab1645c0563a6d93bfd6e9c48a39c570c0d2f06beef8f796e0a7", 1),
    ("efe47cb1140c1aacc97e2b6405432514c35a7ef546068f47150d6139d03a2464", "fbc299b0589de4cf19586436972c8d7219242d14b72589f15d8a2948db1859c3", 1),
    ("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", 1),
    ("c8 6 14 f4 58 18 15 36 8 80 32 93 9f c3 2a 1a b9 29 48 ce bd 95 3d ed 37 93 df 97 d3 4a 27 96", "16 5f 1b 6d 48 8f 7e 3b 87 a0 3b 68 a1 d8 b4 5 dd 23 44 29 3 a4 fb c4 84 7b 12 14 56 86 1 d5", 1),
    (size_anchor, size_replacement, 1),
    ("gemini-mt6797-a72-ready-token-contract-repair.boot.img", "gemini-mt6797-a72-p27-runtime-attribution.boot.img", 1),
    (".derived-build-a72-ready-contract.XXXXXXXX", ".derived-build-a72-p27-attribution-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-ready-token-contract-repair", "experiment=2026-08-30-mainline-a72-p27-runtime-attribution", 1),
    ("validation=ready-token-contract-repair-package", "validation=p27-runtime-attribution-package", 1),
    ('output_name="candidate-a72-ready-token-contract-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-p27-runtime-attribution-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-ready-token-contract-repair-build", "validation=a72-p27-runtime-attribution-build", 1),
    ("unsafe READY-contract candidate derivation", "unsafe P27 diagnostic candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P27 diagnostic candidate derivation: expected {count}, found {actual}: {old}"
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
