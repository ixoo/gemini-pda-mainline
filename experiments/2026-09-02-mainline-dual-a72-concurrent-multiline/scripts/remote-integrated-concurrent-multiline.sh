#!/usr/bin/env bash

# Materialize admission, topology/RAM, and finite concurrent multiline work as
# one boot-bound device shell and one nc session.
set -euo pipefail
export LC_ALL=C
umask 077

readonly PARENT_SHA256=989e94e2d8dfd89dff8e5df3cc9bf512ad7b88ceee49f972e6101249c9425a85
readonly WORKLOAD_SHA256=c6bc8a26f2f79487d1bbfd9c8a294e589afd02ba17acf31647736dff7f100316
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
for command in mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
parent="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/remote-integrated-topology-ram.sh"
workload="$script_dir/device-concurrent-multiline.sh"
[[ -f "$parent" && ! -L "$parent" ]] || die 'integrated parent is absent or unsafe'
[[ -f "$workload" && ! -L "$workload" ]] || die 'concurrent workload is absent or unsafe'
[[ "$(sha256sum "$parent" | awk '{print $1}')" == "$PARENT_SHA256" ]] || die 'integrated parent changed'
[[ "$(sha256sum "$workload" | awk '{print $1}')" == "$WORKLOAD_SHA256" ]] || die 'concurrent workload changed'

parent_script=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-concurrent-parent.XXXXXXXX")
workload_script=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-concurrent-workload.XXXXXXXX")
cleanup() { rm -f -- "${parent_script:-}" "${workload_script:-}"; }
trap cleanup EXIT HUP INT TERM
"$parent" --boot-id "$boot_id" >"$parent_script"
python3 - "$workload" "$workload_script" "$boot_id" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
marker = "EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__"
replacement = f"EXPECTED_BOOT_ID={sys.argv[3]}"
if text.count(marker) != 1:
    raise SystemExit("concurrent workload boot-ID marker changed")
Path(sys.argv[2]).write_text(text.replace(marker, replacement), encoding="utf-8")
PY
python3 - "$parent_script" "$workload_script" <<'PY'
from pathlib import Path
import sys

parent = Path(sys.argv[1]).read_text(encoding="utf-8")
workload = Path(sys.argv[2]).read_text(encoding="utf-8")
old = "trap - EXIT HUP INT TERM\nexit 0\n"
new = "trap - EXIT HUP INT TERM\n"
if parent.count(old) != 1:
    raise SystemExit("unsafe concurrent continuation after topology/RAM parent")
if parent.count("__GEMINI_A72_RAM_COHERENCY_BEGIN__") != 1:
    raise SystemExit("parent topology/RAM begin boundary changed")
if workload.count("__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__") != 1:
    raise SystemExit("concurrent begin boundary changed")
if workload.count("__GEMINI_A72_CONCURRENT_MULTILINE_END__") != 2:
    raise SystemExit("concurrent end boundary changed")
sys.stdout.write(parent.replace(old, new, 1))
sys.stdout.write("\n")
sys.stdout.write(workload)
PY
