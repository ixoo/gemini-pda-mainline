#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Replay the exact current-tree serviceability transform with new-package pins.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
base='' output='' expected=''
while (($#)); do
  case "$1" in
    --base-dtb) base=${2:-}; shift 2;;
    --output) output=${2:-}; shift 2;;
    --expected-sha256) expected=${2:-}; shift 2;;
    *) die "unknown argument: $1";;
  esac
done
readonly EXPECTED_DTB_SHA256=58629ff9f48ffa3840b04a336d45a52da7f2c1483a4400d2a0f1637fe9638037
[[ -n "$base" && -n "$output" && "$expected" == "$EXPECTED_DTB_SHA256" ]] || die 'base, output and exact expected sha256 are required'
[[ -f "$base" && ! -L "$base" ]] || die 'unsafe base DTB'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite DTB'
[[ "$(sha256sum "$base" | awk '{print $1}')" == d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc ]] || die 'base DTB identity changed'

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh"
[[ -f "$source" && ! -L "$source" ]] || die 'pinned transformer missing'
[[ "$(sha256sum "$source" | awk '{print $1}')" == 550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d ]] || die 'pinned transformer changed'

managed_root="$repo_root/artifacts/toprgu/.tmp"
mkdir -p -- "$managed_root"
chmod 0700 "$managed_root"
[[ "$(stat -f '%Lp:%u' "$managed_root" 2>/dev/null || stat -c '%a:%u' "$managed_root")" == "700:$(id -u)" ]] || die 'temporary root is not private'
git -C "$repo_root" check-ignore -q -- "$managed_root" || die 'temporary root is not Git-ignored'
derived=''
cleanup() {
    [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"
    rmdir -- "$managed_root" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
derived=$(mktemp "$managed_root/.serviceability-transform.XXXXXXXX")
python3 - "$source" "$derived" "$expected" <<'PY'
from pathlib import Path
import sys
source, output, expected = map(Path, sys.argv[1:])
text = source.read_text(encoding="utf-8")
text = text.replace("dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e", "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc", 1)
text = text.replace("b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd", expected.name, 1)
if "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc" not in text:
    raise SystemExit("transformer derivation lost base pin")
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" --base-dtb "$base" --output "$output"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
[[ "$status" == 0 ]] || exit "$status"
[[ "$(sha256sum "$output" | awk '{print $1}')" == "$EXPECTED_DTB_SHA256" ]] || die 'derived DTB identity changed'
