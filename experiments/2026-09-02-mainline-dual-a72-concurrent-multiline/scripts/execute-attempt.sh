#!/usr/bin/env bash

# Retarget the one-session topology executor to append the bounded concurrent
# multiline child before the nc session closes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=05e8fbe602715ef989e1534df5f6525855618c0b22b7967aeedd440b75f7eea4
readonly REMOTE_SHA256=f7f036d9dc4028e8883d4b0fc66b79ded8f1b594693e4a101d298ca305b4f839
readonly CLASSIFIER_SHA256=1f6c8f3ac1663db5aa796e529984dfb5a9acc3d5e1f60391336bedf34efb8d79
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/execute-integrated-attempt.sh"
remote="$script_dir/remote-integrated-concurrent-multiline.sh"
classifier="$script_dir/classify-attempt.py"
for item in "$source_executor" "$remote" "$classifier"; do
	[[ -f "$item" && ! -L "$item" ]] || die "required source is absent or unsafe: $item"
done
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'
[[ "$(sha256sum "$remote" | awk '{print $1}')" == "$REMOTE_SHA256" ]] || die 'remote workload wrapper changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] || die 'workload classifier changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-concurrent.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('source_executor="$script_dir/execute-parent-trigger.sh"',
     'source_executor="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/execute-parent-trigger.sh"', 1),
    ("989e94e2d8dfd89dff8e5df3cc9bf512ad7b88ceee49f972e6101249c9425a85",
     "f7f036d9dc4028e8883d4b0fc66b79ded8f1b594693e4a101d298ca305b4f839", 2),
    ('remote="$script_dir/remote-integrated-topology-ram.sh"',
     'remote="$script_dir/remote-integrated-concurrent-multiline.sh"', 1),
    ('trigger_wrapper="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/remote-integrated-topology-ram.sh"',
     'trigger_wrapper="$repo_root/experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/remote-integrated-concurrent-multiline.sh"', 1),
    ("97c207d41dc7d38a1f04334be34c1f6ff96973b8e6f174e96c1be8845db3cac0",
     "1f6c8f3ac1663db5aa796e529984dfb5a9acc3d5e1f60391336bedf34efb8d79", 2),
    ('classifier="$script_dir/classify-integrated-attempt.py"',
     'classifier="$script_dir/classify-attempt.py"', 1),
    ('("classify-parent-trigger.py", "classify-integrated-attempt.py", 2),',
     '("classify-parent-trigger.py", "classify-attempt.py", 2),\n'
     '    ("experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-attempt.py",\n'
     '     "experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/classify-attempt.py", 1),\n'
     '    (\'validator="$script_dir/validate-pretrigger.py"\',\n'
     '     \'validator="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/validate-pretrigger.py"\', 1),', 1),
    ("a72-mt6797-cpu-map-integrated-attempt-2",
     "a72-concurrent-multiline-attempt-2", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe concurrent executor derivation: expected {count}, "
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
