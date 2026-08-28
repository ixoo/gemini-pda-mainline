#!/usr/bin/env bash

# Source-pin the already hardware-free-proven live collector, bind it to the
# exact serviceable boot, and execute its one trigger session without retry.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=69e3290661820a4555a3b43c2451d63e6bf05f81013bae864704cfa0a458580e
readonly DERIVED_SHA256=f7b77371de128839b04adb874c6b81d14c3bc494f31dbf5a5faf5224a96a1ec8
readonly PRETRIGGER_SHA256=999d7a55f0fdb4992061588b17ebcd46ed945210dd1ba8006a286febfee94a9f
readonly TRIGGER_SHA256=93e6ee4b0dd84d6415a84a8bac400308b7fa7483aabab0b414b33016d1ae690b
readonly VALIDATOR_SHA256=3f4cb51ad1405df620f447b6210aac795a0664171711f8ca38ddaf05e9113531
readonly CLASSIFIER_SHA256=a35a19cd1a4a5617bbab0bb3d4a7108f205dcddde92f95b41b47d9583b55ff6d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod install mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/collect-live-trigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
while read -r path expected; do
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || die "support source changed: $path"
done <<EOF
$script_dir/remote-pretrigger.sh $PRETRIGGER_SHA256
$script_dir/remote-trigger.sh $TRIGGER_SHA256
$script_dir/validate-pretrigger.py $VALIDATOR_SHA256
$script_dir/classify-attempt.py $CLASSIFIER_SHA256
EOF

derived=$(mktemp "$script_dir/.derived-serviceable-one-shot.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_route = '''route_interface() {
	route -n get "$DEVICE_ADDRESS" 2>/dev/null | \\
		awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }'
}'''
new_route = '''route_interface() {
	local resolved
	resolved="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')" || true
	if [[ -z "$resolved" ]]; then
		resolved="$(netstat -rn -f inet 2>/dev/null | awk '$1 == "10.15.19/24" { print $4; count++ } END { exit count != 1 }')" || true
	fi
	printf '%s\\n' "$resolved"
}'''
replacements = (
    ("4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1),
    ("008a8e33cd67654dc4d3632277b6d1600ef9b565ef7e5b763bb481c424229b60", "999d7a55f0fdb4992061588b17ebcd46ed945210dd1ba8006a286febfee94a9f", 1),
    ("906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715", "3f4cb51ad1405df620f447b6210aac795a0664171711f8ca38ddaf05e9113531", 1),
    ("274b950c8c0dbd2ca3eb6fa7933fe692251de70bf7aadf735bc98d5c12d2886e", "a35a19cd1a4a5617bbab0bb3d4a7108f205dcddde92f95b41b47d9583b55ff6d", 1),
    ("2026-08-28-mainline-a72-admission-live-trigger", "2026-08-28-mainline-a72-admission-serviceable-one-shot", 2),
    ("nc ping python3 route sed", "nc netstat ping python3 route sed", 1),
    (old_route, new_route, 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe collector derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
[[ "$(sha256sum "$derived" | awk '{print $1}')" == "$DERIVED_SHA256" ]] || die 'derived collector changed'

if (($#)); then
	[[ $# == 2 && "$1" == --materialize ]] || die 'usage: run-one-shot.sh [--materialize NEW_FILE]'
	[[ ! -e "$2" && ! -L "$2" ]] || die 'refusing to overwrite materialized collector'
	install -m 0600 "$derived" "$2"
	cleanup
	trap - EXIT HUP INT TERM
	exit 0
fi

set +e
/bin/bash "$derived" \
	--output artifacts/runtime-captures/a72-admission-serviceable-one-shot-attempt-1 \
	--deployment-boot-id 9c462f2c-84a5-490a-a26d-ce863a5ab50a \
	--wait-seconds 180 --recovery-seconds 300
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
