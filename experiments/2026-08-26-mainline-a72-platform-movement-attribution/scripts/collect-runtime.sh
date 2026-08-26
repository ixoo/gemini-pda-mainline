#!/usr/bin/env bash

# Source-pin the no-reboot failure-stage collector and retarget its exact
# movement candidate identities, probe, validator, and decision gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c2ddc0360c63039bdc4569953d72f08e77e170fad0c310572752474b9ac0e91e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-platform-movement.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1),
    ("PROBE_SHA256=37d31b04e83b5ea3863c4640fc34ddedda95e635bc47702ab4aeb251a7b89942", "PROBE_SHA256=0ca3407536cb3f399e6e31fab443bd097511237feaf455f434364a2e03c0c78a", 1),
    ("VALIDATOR_SHA256=29005d94a93518901f9509e81b48c358defb521e617a097a4e013272a0287c7f", "VALIDATOR_SHA256=518262924b0b50ad9a45af57eeb4c5a54ebd7f6b08972c69c14b66760f31ee6e", 1),
    ("a72-platform-provider-clock-stage-attempt-1", "a72-platform-movement-attempt-1", 1),
    (".gemini-a72-platform-provider-clock-stage.XXXXXXXX", ".gemini-a72-platform-movement.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-provider-clock-stage-decision", "runtime_gate=serviceable-platform-movement-decision", 1),
    ("exact one-shot platform/provider/protected-clock failure-stage decision", "exact one-shot platform movement attribution decision", 1),
    ("unsafe platform/provider/protected-clock-stage collector derivation", "unsafe platform-movement collector derivation", 1),
    (".derived-collect-a72-platform-provider-clock-stage-nested.XXXXXXXX", ".derived-collect-platform-movement-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe movement collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
