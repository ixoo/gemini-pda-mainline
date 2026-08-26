#!/usr/bin/env bash

# Source-pin the passed failure-stage assembler and retarget only the exact
# package, release, movement marker, and output identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1e8156541aa3c0bfc79a7d1f387b95f3b6e67b7949c3fb2da258910744921e35
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-platform-movement.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_marker_tail = r'''\t'platform/provider/clock capture failed: stage=%s ret=%d'; do'''
new_marker_tail = r'''\t'platform/provider/clock capture failed: stage=%s ret=%d' \\
\t'platform/provider/clock capture failed: stage=platform ret=-11 movement=%03x cpu=%08x/%08x cpu2=%08x/%08x cpusys=%08x/%08x cpu0=%08x/%08x cpu1=%08x/%08x iso=%08x/%08x dcm=%08x/%08x cci-port=%08x/%08x pwrap=%u/%u'; do'''
replacements = (
    ("53398b8a4689e6a4150ec450e5c1e8a5ce37c6bc", "1ad025c40cb6716cb5a110319b715cc03f812551", 1),
    ("a72-platform-provider-clock-stage-candidate", "a72-platform-movement-candidate", 1),
    ("7.1.3-gemini-a72-clock-stage", "7.1.3-gemini-a72-movement", 1),
    ("0088c87bbf39acdbb8147ba185687e87233c4c8e3c30daad633d57311e4885f8", "d1e244b4b3d757b6ee20d3ef0c2719a8f6cfc8f627b6381993ed7b702b26fb27", 1),
    ("b158c810f117f62259c890dad517f769225e5ad7862d89ddfacd659aa68319b3", "5413eace14655c31ef3355a769ec36986e7e458309d4fe5d374c4923b66b6814", 1),
    ("d45758d0175786447635192d0ee0eff6d81f29df10482bc5828f1c3ac34b1265", "f0c86eeea98b478930745c5957cdff81cab05deec9710262b677936ec452736c", 1),
    ("3dc5719f9684a44770b23f8e8f71c2a299db06da230d3616ac756e4bc94b8057", "6c7d9359b3a262ebcd928f2bd76543713102e37fcb55df9c590e60598ecc29ee", 1),
    ("bb39b46229db4ecda930c56e29cce1dd8607baaf769f653baf853b532c307e86", "e96a221ec55b032f5fd8442b8b3bc6ee7669040f56b5016d14bddac691502e73", 1),
    ("c586b6692d20fc9c4a11f768c13492b8073d8fefd37b5c54173881b8e18efaf6", "f1e98614c54bb063343e5d3b396d2a4f5f1d3fe283efd3782a41dee1dede754f", 1),
    ("8ca14ec2960b6934a7b1062de7c6013dc4e9dd3875c42d7cc96c0d7506e42429", "fd070a56d1f247108935298ab1be61938987cab912b84fd64624e8a26a7a6d99", 1),
    ("8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", 1),
    ("-gemini-a72-clock-stage", "-gemini-a72-movement", 1),
    ("gemini-mt6797-a72-platform-provider-clock-stage.boot.img", "gemini-mt6797-a72-platform-movement.boot.img", 1),
    ("candidate-a72-platform-provider-clock-stage-", "candidate-a72-platform-movement-", 1),
    ("2026-08-25-mainline-a72-platform-provider-failure-stage-attribution", "2026-08-26-mainline-a72-platform-movement-attribution", 1),
    ("one-preclock-failure-stage-after-qualified-prefix", "one-platform-movement-mask-from-existing-two-sample-pair", 1),
    ("dtb_delta_from_retired_third_reader=none-byte-identical", "dtb_delta_from_retired_failure_stage=none-byte-identical", 1),
    (old_marker_tail, new_marker_tail, 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe movement builder derivation: expected {count}, found {actual}: {old}"
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
