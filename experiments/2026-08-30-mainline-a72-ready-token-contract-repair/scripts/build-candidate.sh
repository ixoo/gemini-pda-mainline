#!/usr/bin/env bash

# Source-pin the proven production assembler and retarget only the repaired
# READY-token package, exact provenance leaf, candidate identities, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5593879f5a6ac5aa22ae33621973a17a205f7930503c0d8713dc4fbaf6206b5a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-30-mainline-a72-live-a34-predicate-repair/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-ready-contract.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f361a704af745e503388bdaf63c4e161c7bb50fe", "8dc8e806331b1617795eb02aff27df559521e508", 1),
    ("f9210bf11c6861977427f3af0d748c515c71ed70f935ba7e90ef2f8567bdb76d", "118e0d8106330055b09d63085cfe27bf8818747bedc9402fbd48d3095e0384ee", 1),
    ("717302bda5819b3ad5e0e824c28726d10f0099c8072b86b71df97a87425eb22c", "7553356a12a068c2bf5d917609936b98e7747dc54ce992c9b833121d9756d2c3", 1),
    ("e883aee92a5f53a57142d6ad850d0d101e95e62c9945760919cff7aa68518a9f", "671e5cf88bb81c1a8c2990d84ca100640875630d6dcb6886e83811af9b7a65e0", 1),
    ("4ee372c3b481a46f40ca548a5f7c0afa3db9eb26bdcf3016dec03de00ae376c7", "022aa79d1ee3a279fb5c62ca7b5608701fb09a8fefa4c575b5396d9f107bf5ec", 1),
    ("5751e3a36319866d6b84995945fc4fca291d65151e4e710e4031ee39c75a0dde", "9e7f2640efba4c4a448b12887f3ba9084a6988f41a46dc2038c7468d59f9d4e3", 1),
    ("7f3a23acec8060642b7c0d52a16b30cdfb7d52a55a70c984a008becb35a09c99", "11eb595964b191d83f08b33260462fae1dba3dfba0d26e99ce1552a444864526", 1),
    ("8fb8194b975989700f0c48b5ce1ab621feed515e4a5174fd36f4fd2039698a80", "efe47cb1140c1aacc97e2b6405432514c35a7ef546068f47150d6139d03a2464", 1),
    ("7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", "a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", 1),
    ("a6 90 59 5f 89 c9 b4 e8 f2 27 ea c6 eb 8b fc 98 1b a9 f2 e 6c 61 8b 67 60 96 38 8e f1 b7 43 ca", "c8 6 14 f4 58 18 15 36 8 80 32 93 9f c3 2a 1a b9 29 48 ce bd 95 3d ed 37 93 df 97 d3 4a 27 96", 1),
    ("gemini-mt6797-a72-live-a34-predicate-repair.boot.img", "gemini-mt6797-a72-ready-token-contract-repair.boot.img", 1),
    (".derived-build-a72-live-a34-repair.XXXXXXXX", ".derived-build-a72-ready-contract-inner.XXXXXXXX", 1),
    ("experiment=2026-08-30-mainline-a72-live-a34-predicate-repair", "experiment=2026-08-30-mainline-a72-ready-token-contract-repair", 1),
    ("validation=live-a34-predicate-repair-package", "validation=ready-token-contract-repair-package", 1),
    ('output_name="candidate-a72-live-a34-predicate-repair-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-ready-token-contract-repair-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-live-a34-predicate-repair-build", "validation=a72-ready-token-contract-repair-build", 1),
    ("unsafe live-A34-repair candidate derivation", "unsafe READY-contract candidate derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-contract candidate derivation: expected {count}, found {actual}: {old}"
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
