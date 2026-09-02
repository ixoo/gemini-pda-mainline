#!/usr/bin/env bash

# Source-pin the CPUHP lock-repair collector and retarget its exact candidate,
# tooling identities, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9827abc88d01cf1a29b74b09b83bfc318527b0c1990da3940c21190c6365c5f1
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-cpuhp-lock-repair-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source CPUHP lock-repair collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPUHP lock-repair collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-cpu-on-progress.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293",
     "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe", 1),
    ("9cd506a4052dd65a5b4c877ff514a66262ec960ab77032d32381329ada2522d5",
     "41f4eac6c2fc0f3faca53706a9dc056f2956dfa549d12e115dc5b641482e2940", 1),
    ("6aae843d3d9ab89230a7e67ad838280b7716dc927495b8f4fc5e1566a6314c21",
     "4ba88f79edae86e9af4448b72841bb465ea75d2b9c8fd05828075aeda97c4049", 1),
    ("09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d",
     "bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645", 1),
    ("__GEMINI_A72_CPU9_CPUHP_LOCK_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_CPU_ON_PROGRESS_PRETRIGGER_SCRIPT__", 1),
    ("remote-cpuhp-lock-repair-pretrigger.sh",
     "remote-cpu-on-progress-pretrigger.sh", 1),
    ("validate-cpuhp-lock-repair-pretrigger.py",
     "validate-cpu-on-progress-pretrigger.py", 1),
    ("a72-cpu9-cpuhp-lock-pretrigger-attempt-1",
     "a72-cpu9-cpu-on-progress-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-cpuhp-lock-probe.XXXXXXXX",
     ".gemini-a72-cpu9-cpu-on-progress-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpuhp-lock-command.XXXXXXXX",
     ".gemini-a72-cpu9-cpu-on-progress-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress collector derivation: expected "
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
