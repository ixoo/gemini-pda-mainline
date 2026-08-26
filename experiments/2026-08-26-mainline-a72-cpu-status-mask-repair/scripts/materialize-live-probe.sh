#!/usr/bin/env bash

# Materialize the exact source-pinned wrapper chain into the concrete device
# probe without executing that probe on the host.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=124f15e09c9c2812b35e91a3a30d347458729a7b2333b216d730ff6824e2dc86
readonly MATERIALIZED_SHA256=de72e6cf61aec14c2deb56ee67a133ad323612d87812914e96a2644bca91d1c9
readonly MAX_LEVELS=10
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --output FILE\n' "$0" >&2; }

output=
while (($#)); do
	case "$1" in
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage; exit 2; }
for command in chmod cp grep mkdir mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-live-probe.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source probe changed'
case "$output" in /*) ;; *) output="$PWD/${output#./}" ;; esac
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
output_parent=$(cd -- "$(dirname -- "$output")" && pwd -P)
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is unsafe'

workdir=$(mktemp -d "${TMPDIR:-/tmp}/.gemini-materialize-probe.XXXXXXXX")
runner=$(mktemp "$script_dir/.materialize-probe-runner.XXXXXXXX")
cleanup() {
	[[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"
	[[ ! -e "${runner:-}" ]] || rm -f -- "$runner"
}
trap cleanup EXIT HUP INT TERM
cp "$source_probe" "$workdir/level-0.sh"
level=0
# shellcheck disable=SC2016 # Match literal wrapper variables, not host values.
while grep -Eq '/bin/(ba)?sh "\$derived" "\$@"' "$workdir/level-$level.sh"; do
	next=$((level + 1))
	((next <= MAX_LEVELS)) || die 'probe derivation chain exceeds ceiling'
	cp "$workdir/level-$level.sh" "$runner"
	python3 - "$runner" <<'PY'
from pathlib import Path
import re
import sys


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
pattern = re.compile(r'/bin/(?:ba)?sh "\$derived" "\$@"')
if len(pattern.findall(text)) != 1:
    raise SystemExit("unsafe probe materialization execution anchor")
path.write_text(
    pattern.sub('cp "$derived" "$DERIVED_OUTPUT"', text),
    encoding="utf-8",
)
PY
	chmod 0700 "$runner"
	DERIVED_OUTPUT="$workdir/level-$next.sh" "$runner"
	[[ -f "$workdir/level-$next.sh" && ! -L "$workdir/level-$next.sh" ]] ||
		die 'derived probe level is missing or unsafe'
	level=$next
done
[[ "$level" == 2 ]] || die 'unexpected probe derivation depth'
final="$workdir/level-$level.sh"
[[ "$(sha256sum "$final" | awk '{print $1}')" == "$MATERIALIZED_SHA256" ]] ||
	die 'materialized probe identity changed'
/bin/sh -n "$final"
grep -Fq '__A72_EARLY_LIVE_CONTROL_BEGIN__' "$final" || die 'begin frame missing'
grep -Fq '__A72_EARLY_LIVE_CONTROL_END__' "$final" || die 'end frame missing'
grep -Fq 'readonly INSTALLED_FULL_SHA256=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7' "$final" ||
	die 'candidate identity missing'
mv "$final" "$output"
chmod 0600 "$output"
cleanup
trap - EXIT HUP INT TERM
printf 'materialized_probe_sha256=%s\nderivation_levels=%s\ndevice_action=none\n' \
	"$MATERIALIZED_SHA256" "$level"
