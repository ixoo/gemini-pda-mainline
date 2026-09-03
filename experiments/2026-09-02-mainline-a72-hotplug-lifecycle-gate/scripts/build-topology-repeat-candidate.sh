#!/usr/bin/env bash

# Source-pin the successful stage-binding candidate builder and replace only
# its composed DT with the proven topology-preserving composition.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0c23fe89f0d26ce4030b221675605ccd5c76a3a447077c674b5880112b19ed08
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/build-stage-binding-fix-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source stage-binding-fix builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-topology-repeat.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
output_parent=
previous=
for argument in "$@"; do
	if [[ "$previous" == --output-parent ]]; then
		output_parent=$argument
		break
	fi
	previous=$argument
done
[[ -n "$output_parent" ]] || die 'missing --output-parent argument'
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ecf278518608e4fa17c05b933a75c55ec4a31fdb4ceff10bce784754822e834c",
     "1f34ddb965a1f14ef1e4cd3f68589b7a93d8186c8045c2804bd16beed9bc92c7", 1),
    ("09c4f0b7ebc733286446b586ce397f7f93ded832c4ccd96e48077e363bb995ae",
     "e02bfd85b503f0ee8116d7ac60942105ec329e6453e3cd3204a3b1beaa6e3c54", 1),
    ("c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271",
     "6ba8c9538dcff6559066088da943d96aaa8ad32d10a93b34c8bbeddc97464f75", 1),
    ("gemini-a72sym", "gemini-a72top", 1),
    ("gemini-mt6797-a72-stage-binding-fix.boot.img",
     "gemini-mt6797-a72-topology-repeat.boot.img", 1),
    ("candidate-a72-stage-binding-fix-", "candidate-a72-topology-repeat-", 1),
    ("validation=a72-stage-binding-fix-package",
     "validation=a72-topology-repeat-package", 1),
    ("validation=a72-stage-binding-fix-build",
     "validation=a72-topology-repeat-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology-repeat candidate derivation: expected {count}, "
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
if [[ "$rc" == 0 ]]; then
	artifact="$output_parent/candidate-a72-topology-repeat-e02bfd85"
	python3 - "$artifact" <<'PY'
from pathlib import Path
import hashlib
import os
import sys
import tempfile

artifact = Path(sys.argv[1])
if not artifact.is_dir() or artifact.is_symlink():
    raise SystemExit("topology-repeat artifact directory is missing or unsafe")
provenance = artifact / "provenance.txt"
old = "control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c"
new = "control_dtb_serviceability_base=4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
text = provenance.read_text(encoding="ascii")
if text.count(old) != 1 or new in text:
    raise SystemExit("candidate provenance base identity changed")
with tempfile.NamedTemporaryFile(
    mode="w", encoding="ascii", dir=artifact, prefix=".provenance.",
    delete=False
) as stream:
    stream.write(text.replace(old, new))
    temporary = Path(stream.name)
os.chmod(temporary, 0o600)
os.replace(temporary, provenance)

lines = []
for path in sorted(artifact.iterdir(), key=lambda item: item.name):
    if path.name == "SHA256SUMS":
        continue
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"unexpected artifact member: {path.name}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  ./{path.name}\n")
manifest = artifact / "SHA256SUMS"
with tempfile.NamedTemporaryFile(
    mode="w", encoding="ascii", dir=artifact, prefix=".manifest.",
    delete=False
) as stream:
    stream.writelines(lines)
    temporary = Path(stream.name)
os.chmod(temporary, 0o600)
os.replace(temporary, manifest)
PY
	printf '%s\n' 'validation=a72-topology-repeat-provenance' \
		'control_dtb_serviceability_base=4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923' \
		'result=pass'
fi
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
