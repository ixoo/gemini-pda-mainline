#!/usr/bin/env bash

# Source-pin the proven CPU0-9 container assembler and retarget only the exact
# Buildbox provenance, topology DT, and deterministic container identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f494b860897923a6173a501d6492ed6693e74ddcdf6f77d17c9ee3abd804a83b
readonly OUTPUT_NAME=candidate-a72-cpu9-topology-7753563c
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod find mktemp python3 rm sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/build-completion-lock-repair-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source completion-lock builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source completion-lock builder changed'

output_parent=
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [[ "${args[$i]}" == --output-parent ]]; then
		((i + 1 < ${#args[@]})) || die '--output-parent requires a value'
		output_parent=${args[$((i + 1))]}
	fi
done
[[ -n "$output_parent" ]] || die '--output-parent is required'
output_parent=$(cd -- "$output_parent" && pwd -P)
output="$output_parent/$OUTPUT_NAME"
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'

derived=$(mktemp "$script_dir/.derived-build-mt6797-cpu-map.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f554c691007e26e2b8fb234320f291f10a33fdf0",
     "2e661e90a6b4d158400b4e5fe832d39f48abd10b", 1),
    ("29d47ed5d027d0787b583c196aff63e96d5a822b5137395dfc6607afefa33a2c",
     "1a393163e822c330ac9eefa00e873723b5d496fd7c48a10a16e5047df7aedfa1", 1),
    ("6b5b5b9d48cd5d7d5a03b5c7099390b870c5b73e46165aade7e6eeae7540aa64",
     "4a39f1eb9fc64f8c11879eab25e241050fb98edd9fb1070701f087fe323a02f4", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "01c60771e1fc21c47a5a094482a555b286f8f5d046c009ba3e06d7e0212c6ac7", 1),
    ("eba0aa21a2a650a64c0a3ba2b3d416932294eae2d257eb0e9b83b50df2335872",
     "7753563c80356b7b4822249a96c4baccf7d247bb9e9cf8747239e9292872d55c", 1),
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("38 61 52 0 ff 5c b4 b2 cb 41 f4 25 78 e3 e a1 aa ce 2f b0 2c d2 39 f0 e0 b9 fd 66 b7 e1 17 ad",
     "e3 9 96 b2 60 4d f0 7b 99 bf 6d 48 29 40 fa a ff 65 85 c8 6c e2 fd 7e d6 c4 2b 13 68 2c 58 65", 1),
    ("variant=cpu9-completion-lock-repair", "variant=cpu-map-topology", 1),
    ("dt_semantics=unchanged-serviceability-admission-tree-plus-completion-lock-repair-package-provenance-leaf",
     "dt_semantics=serviceability-admission-tree-plus-mt6797-4-4-2-cpu-map-plus-package-provenance-leaf", 1),
    ('output_name="candidate-a72-cpu9-completion-lock-${RAW_SHA256:0:8}"',
     'output_name="candidate-a72-cpu9-topology-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-cpu9-completion-lock-repair-build",
     "validation=a72-cpu9-topology-build-derived", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology candidate derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"
cleanup
trap - EXIT HUP INT TERM

python3 - "$output/provenance.txt" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")
replacements = (
    ("experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor\n",
     "experiment=2026-09-02-mainline-mt6797-cpu-map\n", 1),
    ("control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c\n",
     "control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c\n"
     "topology_serviceability_dtb_sha256=4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923\n", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate provenance normalization: expected {count}, "
            f"found {actual}: {old!r}"
        )
    text = text.replace(old, new)
path.write_text(text, encoding="ascii")
PY
(cd "$output" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum) >"$output/SHA256SUMS"
(cd "$output" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'normalized artifact manifest failed'
chmod 0600 "$output"/*
printf 'validation=a72-cpu9-topology-build\nartifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\ndevice_access=none\nhardware_write=none\n' \
	"$output" \
	7753563c80356b7b4822249a96c4baccf7d247bb9e9cf8747239e9292872d55c \
	68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393
