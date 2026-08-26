#!/usr/bin/env bash

# Source-pin the bounded read-only failure-stage probe and retarget its exact
# installed candidate plus movement-detail expectation.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=37d31b04e83b5ea3863c4640fc34ddedda95e635bc47702ab4aeb251a7b89942
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod grep mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/scripts/remote-live-probe.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-live-probe-platform-movement.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("exact failure-stage candidate", "exact movement-attribution candidate", 1),
    ("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1),
    ("$BB printf '%s\\n' platform_register_observations_expected=26", "$BB printf '%s\\n' platform_register_observations_expected=26\n$BB printf '%s\\n' platform_movement_detail_expected=one-on-platform-eagain", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe movement probe derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
if [[ "${1:-}" == --self-test ]]; then
	/bin/sh -n "$derived"
	grep -F 'readonly INSTALLED_FULL_SHA256=9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78' "$derived" >/dev/null ||
		die 'derived candidate identity missing'
	grep -F 'platform_movement_detail_expected=one-on-platform-eagain' "$derived" >/dev/null ||
		die 'derived movement expectation missing'
	printf 'remote_probe_derivation=pass\ndevice_action=none\n'
	cleanup
	trap - EXIT HUP INT TERM
	exit 0
fi
set +e
/bin/sh "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
