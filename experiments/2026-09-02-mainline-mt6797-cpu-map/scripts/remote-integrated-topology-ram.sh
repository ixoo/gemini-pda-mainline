#!/usr/bin/env bash

# Materialize one boot-bound device script that admits both A72s and then
# immediately runs the topology/RAM probe in the same shell and nc session.
set -euo pipefail
export LC_ALL=C
umask 077

readonly TRIGGER_SHA256=37c28c542989e02654561c45ecb5c5e95df327c21952af310be3dbe12b8bf3be
readonly PROBE_SHA256=daf71fbd3badf5a646afb042730205889624ff03751afe845f69c572a93fea46
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
for command in mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
trigger_wrapper="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/remote-completion-lock-repair-trigger.sh"
probe_wrapper="$script_dir/remote-bounded-topology-ram.sh"
[[ -f "$trigger_wrapper" && ! -L "$trigger_wrapper" ]] || die 'trigger wrapper is absent or unsafe'
[[ -f "$probe_wrapper" && ! -L "$probe_wrapper" ]] || die 'topology/RAM wrapper is absent or unsafe'
[[ "$(sha256sum "$trigger_wrapper" | awk '{print $1}')" == "$TRIGGER_SHA256" ]] || die 'trigger wrapper changed'
[[ "$(sha256sum "$probe_wrapper" | awk '{print $1}')" == "$PROBE_SHA256" ]] || die 'topology/RAM wrapper changed'

trigger=$(mktemp "${TMPDIR:-/tmp}/.gemini-mt6797-integrated-trigger.XXXXXXXX")
probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-mt6797-integrated-probe.XXXXXXXX")
cleanup() { rm -f -- "${trigger:-}" "${probe:-}"; }
trap cleanup EXIT HUP INT TERM
"$trigger_wrapper" --boot-id "$boot_id" >"$trigger"
"$probe_wrapper" --boot-id "$boot_id" >"$probe"
python3 - "$trigger" "$probe" <<'PY'
from pathlib import Path
import sys

trigger = Path(sys.argv[1]).read_text(encoding="utf-8")
probe = Path(sys.argv[2]).read_text(encoding="utf-8")
old = 'exit "$trigger_write_status"\n'
new = '''if [ "$trigger_write_status" -ne 0 ] || [ "$remount_ro_status" -ne 0 ]; then
\texit 3
fi
'''
if trigger.count(old) != 1:
    raise SystemExit("unsafe integrated trigger continuation")
if trigger.count("__GEMINI_A72_LIVE_TRIGGER_BEGIN__") != 1:
    raise SystemExit("trigger begin boundary changed")
if trigger.count("__GEMINI_A72_LIVE_TRIGGER_END__") != 4:
    raise SystemExit("trigger end boundary changed")
if probe.count("__GEMINI_A72_RAM_COHERENCY_BEGIN__") != 1:
    raise SystemExit("probe begin boundary changed")
if probe.count("__GEMINI_A72_RAM_COHERENCY_END__") != 2:
    raise SystemExit("probe end boundary changed")
sys.stdout.write(trigger.replace(old, new, 1))
sys.stdout.write("\n")
sys.stdout.write(probe)
PY
