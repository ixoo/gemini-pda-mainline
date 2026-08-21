#!/usr/bin/env bash

# Source-pin the independent clock-entry validator and add an exact semantic
# proof that this control changes only model text and clock-node enablement.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a302290ccf0509b8fa27b7b2424e648656722e710f267bb0205d9695c9e31769

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod dtc mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-clock-backend-entry-ledger/scripts/test-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] ||
	die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
	/bin/bash "$source_validator" "$@"
	exit $?
fi

package=
arguments=("$@")
while (($#)); do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	*) shift ;;
	esac
done
[[ -n "$package" ]] || die '--package is required'
package="$(cd -- "$package" && pwd -P)"

python3 - \
	"$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	"$package/dtbs/mediatek/mt6797-gemini-pda-clock-backend-entry.dtb" <<'PY'
from pathlib import Path
import subprocess
import sys


def decompile(path: Path) -> list[str]:
    result = subprocess.run(
        ["dtc", "-I", "dtb", "-O", "dts", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.splitlines()


base = decompile(Path(sys.argv[1]))
derivative = decompile(Path(sys.argv[2]))
if len(base) != len(derivative):
    raise SystemExit("DT controls differ structurally")
changes = [(index, left, right) for index, (left, right) in enumerate(zip(base, derivative)) if left != right]
expected_model = (
    '\tmodel = "Planet Computers Gemini PDA";',
    '\tmodel = "Planet Computers Gemini PDA (clock backend entry ledger)";',
)
if len(changes) != 2 or changes[0][1:] != expected_model:
    raise SystemExit(f"unexpected DT semantic delta: {changes!r}")
index, left, right = changes[1]
if (left, right) != ('\t\tstatus = "disabled";', '\t\tstatus = "okay";'):
    raise SystemExit(f"unexpected clock status delta: {(left, right)!r}")
node_start = max(i for i in range(index) if base[i] == '\tdvfsp-clock-backend@1001a000 {')
node_end = next(i for i in range(index + 1, len(base)) if base[i] == '\t};')
if not (node_start < index < node_end):
    raise SystemExit("clock status delta is outside the exact backend node")
print("control_dtb_semantic_delta=model-label,clock-node-okay-to-disabled")
print("control_dtb_delta_count=2")
PY

derived="$(mktemp "$script_dir/.clock-entry-control-validator.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("5_559_536", "5_559_508", 1),
    (
        "1c5a410b07b0fd971b2105f14cb97dea05168c5d5cf73dc67a47c2892a171768",
        "a36425f3e9cec23ff9281d9151e54ce780ff5abc8d98aa8df190a300a786eb4e",
        1,
    ),
    (
        "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        "fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf",
        1,
    ),
    (
        "d93cba886584ebf3f9b30a9341f4dbea8f90fb35745200464265449a7811c920",
        "dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e",
        1,
    ),
    (
        "gemini-mt6797-clock-backend-entry.boot.img",
        "gemini-mt6797-clock-entry-control.boot.img",
        1,
    ),
    (
        "dtbs/mediatek/mt6797-gemini-pda-clock-backend-entry.dtb",
        "dtbs/mediatek/mt6797-gemini-pda.dtb",
        1,
    ),
    (
        "validation=clock-backend-entry-ledger-candidate",
        "validation=clock-entry-observation-control-candidate",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe control validator derivation: expected {count} occurrences, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY

chmod 0700 "$derived"
set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
