#!/usr/bin/env bash

# Source-pin the guarded provenance/serviceability installer and retarget only
# the exact predecessor, repaired candidate, artifact manifest, and evidence.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=819c208ceab37a3a445a1a4518e8118602646ba7b9edc96e51bb5c4f57c279b0
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-live-a34-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7",\n     "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1)',
     '("8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7",\n     "7c96288818d6d3e0eb5547c675057bbe7789b0b62388b0a171681720da29f2a9", 1)', 1),
    ('("0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78",\n     "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1)',
     '("0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78",\n     "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1)', 1),
    ("388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", "0085efd39fd5c62ad56dfe18108ba7e4f70221a1e6a26d785f66b2cf7fb3680d", 1),
    ("candidate-a72-provenance-serviceability-1921c30e", "candidate-a72-live-a34-predicate-repair-8fb8194b", 1),
    ('("a72-admission-trace", "a72-provenance-serviceability", 5)', '("a72-admission-trace", "a72-live-a34-predicate-repair", 5)', 1),
    ("2026-08-30-mainline-a72-provenance-serviceability-composition", "2026-08-30-mainline-a72-live-a34-predicate-repair", 1),
    (".derived-install-a72-provenance-serviceability.XXXXXXXX", ".derived-install-a72-live-a34-repair-inner.XXXXXXXX", 1),
    ("unsafe composed-candidate installer derivation", "unsafe live-A34-repair installer derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-A34-repair installer derivation: expected {count}, found {actual}: {old}"
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
