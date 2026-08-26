#!/usr/bin/env bash

# Source-pin the movement-attribution collector, retarget its exact candidate
# identities, and replace its legacy one-line netcat payload on the wire with
# bounded in-memory commands. A successful mainline boot remains running.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6f3c92d6359603e8fea65b03fe834eb951c3fad680f24e33e5223cafe831849d
readonly NETCAT_HELPER_SHA256=ae08662ae767e13facd500fe7ccbcc2a77f494e11cae86582904ca4ca2629a70
readonly MATERIALIZER_SHA256=f84c7160bd2d39e2db1f785e75e61f0b043f214ae866546f54bd3372906b22b8
readonly MATERIALIZED_PROBE_SHA256=de72e6cf61aec14c2deb56ee67a133ad323612d87812914e96a2644bca91d1c9
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod ln mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-26-mainline-a72-platform-movement-attribution/scripts/collect-runtime.sh"
netcat_helper="$script_dir/netcat-bounded-exec.py"
materializer="$script_dir/materialize-live-probe.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ -f "$netcat_helper" && ! -L "$netcat_helper" && -x "$netcat_helper" ]] ||
	die 'bounded netcat helper is missing or unsafe'
[[ -f "$materializer" && ! -L "$materializer" && -x "$materializer" ]] ||
	die 'probe materializer is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'
[[ "$(sha256sum "$netcat_helper" | awk '{print $1}')" == "$NETCAT_HELPER_SHA256" ]] ||
	die 'bounded netcat helper changed'
[[ "$(sha256sum "$materializer" | awk '{print $1}')" == "$MATERIALIZER_SHA256" ]] ||
	die 'probe materializer changed'

real_nc=$(command -v nc)
[[ "$real_nc" == /* && -f "$real_nc" && -x "$real_nc" ]] || die 'real netcat is missing or unsafe'
derived=$(mktemp "$script_dir/.derived-collect-cpu-status-mask.XXXXXXXX")
shim_dir=$(mktemp -d "${TMPDIR:-/tmp}/.gemini-cpu-status-mask-netcat.XXXXXXXX")
materialized_probe="$shim_dir/materialized-live-probe.sh"
cleanup() {
	[[ ! -e "${derived:-}" ]] || rm -f -- "$derived"
	[[ ! -d "${shim_dir:-}" ]] || rm -rf -- "$shim_dir"
}
trap cleanup EXIT HUP INT TERM
"$materializer" --output "$materialized_probe" >/dev/null
[[ "$(sha256sum "$materialized_probe" | awk '{print $1}')" == "$MATERIALIZED_PROBE_SHA256" ]] ||
	die 'materialized probe changed after creation'
ln -s "$netcat_helper" "$shim_dir/nc"

python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", 1),
    ("PROBE_SHA256=0ca3407536cb3f399e6e31fab443bd097511237feaf455f434364a2e03c0c78a", "PROBE_SHA256=124f15e09c9c2812b35e91a3a30d347458729a7b2333b216d730ff6824e2dc86", 1),
    ("VALIDATOR_SHA256=518262924b0b50ad9a45af57eeb4c5a54ebd7f6b08972c69c14b66760f31ee6e", "VALIDATOR_SHA256=8ded86eab591242fb7a4e81c13e5e9c90084b477aa5fd3a727f3a622ff26a8e8", 1),
    ("a72-platform-movement-attempt-1", "a72-cpu-status-mask-attempt-1", 1),
    (".gemini-a72-platform-movement.XXXXXXXX", ".gemini-a72-cpu-status-mask.XXXXXXXX", 1),
    ("exact one-shot platform movement attribution decision", "exact one-shot CPU-status-mask platform decision", 1),
    ("unsafe platform-movement collector derivation", "unsafe CPU-status-mask collector derivation", 1),
    (".derived-collect-platform-movement-inner.XXXXXXXX", ".derived-collect-cpu-status-mask-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-status-mask collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
export GEMINI_REAL_NC="$real_nc"
export GEMINI_MATERIALIZED_PROBE="$materialized_probe"
export PATH="$shim_dir:$PATH"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
