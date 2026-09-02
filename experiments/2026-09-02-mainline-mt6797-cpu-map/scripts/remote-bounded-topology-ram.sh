#!/usr/bin/env bash

# Materialize the proven volatile-RAM probe with exact topology collection for
# all ten CPUs, bound to one fresh boot ID.
set -euo pipefail
export LC_ALL=C

readonly SOURCE_SHA256=d1b5f4d9046639e61785d6bebcd598f67ab07feb6dcb82d2a49f8ab41eee5738
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-09-02-mainline-dual-a72-ram-coherency/scripts/device-bounded-ram-coherency.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source RAM probe is absent or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source RAM probe changed'

python3 - "$source_probe" "$boot_id" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("# Run one finite, bidirectional RAM-backed integrity observation on CPUs 8/9.",
     "# Run one finite 4+4+2 topology and bidirectional RAM-integrity observation.", 1),
    ("EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__", f"EXPECTED_BOOT_ID={sys.argv[2]}", 1),
    ("for cpu in 8 9; do", "for cpu in 0 1 2 3 4 5 6 7 8 9; do", 1),
    ("\t$BB printf 'cpu%s_core_siblings=' \"$cpu\"; $BB cat \"$topology/core_siblings_list\"\n"
     "\t$BB printf 'cpu%s_thread_siblings=' \"$cpu\"; $BB cat \"$topology/thread_siblings_list\"",
     "\t$BB printf 'cpu%s_core_siblings=' \"$cpu\"; $BB cat \"$topology/core_siblings_list\"\n"
     "\t$BB printf 'cpu%s_cluster_cpus=' \"$cpu\"; $BB cat \"$topology/cluster_cpus_list\"\n"
     "\t$BB printf 'cpu%s_thread_siblings=' \"$cpu\"; $BB cat \"$topology/thread_siblings_list\"", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology/RAM probe derivation: expected {count}, "
            f"found {actual}: {old!r}"
        )
    text = text.replace(old, new)
sys.stdout.write(text)
PY
