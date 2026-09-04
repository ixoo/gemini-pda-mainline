#!/usr/bin/env bash

# Retarget the guarded live-GPT installer to the exact production candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c9a69f2e970a4782a070e7a5ebeb268932fe94102e3086f38c51e6b066e58d97
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer=$repository/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/install-topology-repeat-boot2.sh
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source topology installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source topology installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-frequency-thermal.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("6ba8c9538dcff6559066088da943d96aaa8ad32d10a93b34c8bbeddc97464f75",
     "ea2aae419220b3c2ea11780f9c91dbb51d509286cd76d2ba1741d9e08e837c9c", 1),
    ("650581d9884741659ab69370b41cff1d61cc8cae799cad589dd6a885f47bd722",
     "819f1c08b7843fc912fd79c812d9e82e213910ff2b93937b66db0e294458eb16", 1),
    ("candidate-a72-topology-repeat-e02bfd85",
     "candidate-mt6797-a72-frequency-zero-divider-398ca636", 1),
    ("a72-topology-repeat", "a72-frequency-thermal-zero-divider", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe production installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
evidence_dir=
arguments=("$@")
for ((index = 0; index < ${#arguments[@]}; index++)); do
	if [[ "${arguments[$index]}" == --evidence-dir ]]; then
		((index + 1 < ${#arguments[@]})) || die '--evidence-dir requires a value'
		evidence_dir=${arguments[$((index + 1))]}
	fi
done
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
if [[ "$rc" == 0 && -n "$evidence_dir" ]]; then
	case "$evidence_dir" in /*) ;; *) evidence_dir=$repository/${evidence_dir#./} ;; esac
	summary=$evidence_dir/deployment-summary.txt
	[[ -f "$summary" && ! -L "$summary" ]] || die 'successful deployment summary is absent or unsafe'
	python3 - "$summary" <<'PY'
from pathlib import Path
import os
import sys

path = Path(sys.argv[1])
old = "experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate\n"
new = "experiment=2026-09-04-mt6797-a72-frequency-observation\n"
text = path.read_text(encoding="utf-8")
if text.count(old) != 1 or text.count(new) != 0:
    raise SystemExit("successful deployment summary label changed")
temporary = path.with_name(".deployment-summary.normalized")
temporary.write_text(text.replace(old, new, 1), encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, path)
PY
	(cd "$evidence_dir" && sha256sum deployment-summary.txt >SHA256SUMS)
	chmod 0600 "$evidence_dir/SHA256SUMS"
fi
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
