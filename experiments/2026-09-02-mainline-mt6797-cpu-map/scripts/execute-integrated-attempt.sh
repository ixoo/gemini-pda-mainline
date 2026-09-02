#!/usr/bin/env bash

# Retarget the proven one-session executor so the exact CPU8/CPU9 trigger is
# followed immediately by the topology/RAM probe before the nc session closes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=12317b5e6e0d3ad32982d9fb90e37b9f656d2a202fb49e59b126ac75be48449f
readonly REMOTE_SHA256=989e94e2d8dfd89dff8e5df3cc9bf512ad7b88ceee49f972e6101249c9425a85
readonly CLASSIFIER_SHA256=97c207d41dc7d38a1f04334be34c1f6ff96973b8e6f174e96c1be8845db3cac0
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-parent-trigger.sh"
remote="$script_dir/remote-integrated-topology-ram.sh"
classifier="$script_dir/classify-integrated-attempt.py"
for item in "$source_executor" "$remote" "$classifier"; do
	[[ -f "$item" && ! -L "$item" ]] || die "required source is absent or unsafe: $item"
done
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'
[[ "$(sha256sum "$remote" | awk '{print $1}')" == "$REMOTE_SHA256" ]] || die 'integrated remote wrapper changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] || die 'integrated classifier changed'

derived=$(mktemp "$script_dir/.derived-execute-mt6797-integrated.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = '''    ('classifier="$script_dir/classify-completion-lock-repair-attempt.py"',
     'classifier="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-parent-trigger.py"', 1),
)'''
replacement = '''    ('classifier="$script_dir/classify-completion-lock-repair-attempt.py"',
     'classifier="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-parent-trigger.py"', 1),
    ("37c28c542989e02654561c45ecb5c5e95df327c21952af310be3dbe12b8bf3be",
     "989e94e2d8dfd89dff8e5df3cc9bf512ad7b88ceee49f972e6101249c9425a85", 1),
    ('trigger_wrapper="$script_dir/remote-completion-lock-repair-trigger.sh"',
     'trigger_wrapper="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/remote-integrated-topology-ram.sh"', 1),
)'''
if text.count(anchor) != 1:
    raise SystemExit("unsafe integrated remote-executor insertion")
text = text.replace(anchor, replacement, 1)
for old, new, count in (
    ("c41d58cf60e0f5c769f195b28933b1349963f3523e86248fa197b59b718f58b1",
     "97c207d41dc7d38a1f04334be34c1f6ff96973b8e6f174e96c1be8845db3cac0", 2),
    ("classify-parent-trigger.py", "classify-integrated-attempt.py", 2),
    ("a72-mt6797-cpu-map-attempt-1",
     "a72-mt6797-cpu-map-integrated-attempt-2", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe integrated executor derivation: expected {count}, "
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
