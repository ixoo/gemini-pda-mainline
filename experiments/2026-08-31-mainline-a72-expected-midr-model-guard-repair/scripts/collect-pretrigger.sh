#!/usr/bin/env bash

# Source-pin the bounded collector and retarget the exact model-guard
# candidate, read-only probe, validator, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d32e6d465c5cde5c4cddb0ebdfd385e47cc52bac0fb41693abce2fe7c22eae38
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-expected-midr-model-guard.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d",
     "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69", 1),
    ("9c4491e18cac8b403fa120cfd3f6c31735b3079130d9e02d8594f1aa2b31b8a2",
     "80e9a7220f329ce54d24101ce9ce73123af0e9d642b423a61a4709646f355dbb", 1),
    ("ec7f4879fb4f52c38d86fe7aeedda87453fcfec41c27c86618e4b3b0dbaad506",
     "2ff487b51656909fcc04d0b8a4c5503844dd3f9589f86bd32e8e6ba9bbb512d2", 1),
    ("c0426f2c197df439ef7108082c12d72a70b0c36722d7828952706bf3de508ab3",
     "323b49071d93c0a13fc25a957c80ba5a82ba9b0f94c1ee5e3197a12d056c408e", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-r0p1-expected-pair-repair", 1),',
     '("a72-isolation-held-result-contract-repair", "a72-expected-midr-model-guard-repair", 1),', 1),
    (".derived-collect-a72-r0p1-expected-pair-repair-inner.XXXXXXXX",
     ".derived-collect-a72-expected-midr-model-guard-inner.XXXXXXXX", 1),
    ("r0p1 expected-pair repair collector derivation",
     "expected-MIDR model-guard repair collector derivation", 1),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe model-guard collector derivation: {old}")
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
