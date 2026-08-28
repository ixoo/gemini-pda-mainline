#!/usr/bin/env bash

# Source-pin the validated trace-softfail builder, retaining its exact kernel
# package while replacing only the raw full-admission DT with the already
# proven serviceability-restored derivative.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=246322cd6afc6d7c9fc73df5ad5c6dd53390e5a35906a1f72e7dc714d49155e4
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-softtrace-serviceable.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = "replacements = (\n"
injected = '''replacements = (
    ("readonly DTB_SHA256=1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509",
     "readonly DTB_SHA256=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ('dtb="$package/dtbs/mediatek/mt6797-gemini-pda-a72-admission.dtb"',
     'dtb="$repo_root/artifacts/a72-admission-serviceability-restoration-input/mt6797-gemini-pda-a72-admission-serviceable.dtb"', 1),
    ("experiment=2026-08-28-mainline-a72-admission-durable-candidate",
     "experiment=2026-08-28-mainline-a72-admission-softtrace-serviceable", 1),
'''
if text.count(anchor) != 1:
    raise SystemExit("unsafe serviceable-softtrace derivation: replacement anchor changed")
text = text.replace(anchor, injected, 1)
replacements = (
    ('("a72-admission-durable-candidate", "a72-admission-trace-softfail-candidate", 4)',
     '("a72-admission-durable-candidate", "a72-admission-trace-softfail-candidate", 3)', 1),
    ("9d1912aa3055d0835831a9376aec141329e5809fd833359f5baaeb6ad033fd40",
     "8dbc66427179b7468424ce6f81263132e90fb37264d46c4aeb650bad3a5678e7", 1),
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60", 1),
    ("readonly RAW_SIZE=6942720", "readonly RAW_SIZE=6944768", 1),
    ("gemini-mt6797-a72-admission-softtrace.boot.img",
     "gemini-mt6797-a72-admission-softtrace-serviceable.boot.img", 1),
    ("portable-fetched-a72-admission-trace-softfail-package",
     "portable-fetched-a72-admission-softtrace-serviceable-package", 1),
    ("candidate-a72-admission-softtrace-",
     "candidate-a72-admission-softtrace-serviceable-", 1),
    (".derived-build-a72-admission-softtrace.XXXXXXXX",
     ".derived-build-a72-admission-softtrace-serviceable-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe serviceable-softtrace wrapper derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
