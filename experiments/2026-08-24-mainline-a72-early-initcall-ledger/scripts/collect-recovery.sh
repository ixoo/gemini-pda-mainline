#!/usr/bin/env bash

# Source-pin the bounded global-initcall collector and retarget only its exact
# classifier, candidate, deployment boot ID, outcomes, and private output name.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b5fb7f8d1fc919abac99a80adbebc9b3c344345e6da631cc36060b9ea82bab7b

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-global-initcall-ledger/scripts/collect-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived=$(mktemp "$script_dir/.derived-collect-recovery-a72-early-initcall.XXXXXXXX")
cleanup() { [[ ! -e "$derived" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "Collect one bounded, read-only, changed-ID Gemian recovery after boot2.",
        "Collect one bounded, read-only, changed-ID Gemian early-initcall recovery.",
        1,
    ),
    (
        "5250345332b75511dc30b3e8b5b743e78a0ae8d96214eb8fd89ae4e0eb30ef3a",
        "768c2060e0657933843cad252473e9970df283d4f26bf60d81d75e530d1aee82",
        1,
    ),
    (
        "e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a",
        "d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609",
        1,
    ),
    (
        "6ac4e0b6-2979-4a5b-851c-af7282fec216",
        "ca6e280a-1d4b-4db3-ae9e-9d3234d4082c",
        1,
    ),
    (
        "a72-global-initcall-attempt-1-recovery",
        "a72-early-initcall-attempt-1-recovery",
        1,
    ),
    (
        ".a72-global-initcall-recovery.XXXXXXXX",
        ".a72-early-initcall-recovery.XXXXXXXX",
        1,
    ),
    (
        "before-subsys-init-or-writer-refused|subsys-init-only|subsys-and-fs-initcalls",
        "before-pure-init-or-both-writers-refused|pure-primary-refused-only|pure-init-only|pure-plus-primary-refused|pure-and-core-initcalls",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe early-initcall collector derivation: expected {count}, "
            f"found {actual}: {old}"
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
