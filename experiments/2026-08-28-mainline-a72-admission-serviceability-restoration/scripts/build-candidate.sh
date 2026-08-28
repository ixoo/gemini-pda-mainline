#!/usr/bin/env bash

# Source-pin the current-Image control assembler and retarget its DT semantics
# to the full admission tree plus the exact proven serviceability transform.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4b8535bec6397a92d374f6c9e68ab5d99ed860c589273a07ec614237ebe0382a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'
derived=$(mktemp "$script_dir/.derived-build-a72-admission-serviceable.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_semantics = '''[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-state' "$workdir/control.dts")" == 1 ]] || die 'platform-state node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' "$workdir/control.dts")" == 1 ]] || die 'composed observer node changed'
[[ "$(grep -Ec 'mt6797-a72-admission-controller|mt6797-a72-admission-binder' "$workdir/control.dts")" == 0 ]] || die 'admission node leaked into control DT' '''.rstrip()
new_semantics = '''[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-state' "$workdir/control.dts")" == 1 ]] || die 'platform-state node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-admission-controller' "$workdir/control.dts")" == 1 ]] || die 'admission-controller node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-binder' "$workdir/control.dts")" == 1 ]] || die 'binder node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' "$workdir/control.dts")" == 0 ]] || die 'standalone observer leaked into admission DT'
for node_path in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 /i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix; do
	[[ "$(fdtget -ts "$control_dtb" "$node_path" status)" == okay ]] || die "serviceability node is not enabled: $node_path"
done'''
replacements = (
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "b1ff92e8c21aff6b850ed5ac68854b06e0f2059719cb0d50f0924b22345c3e68", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1),
    ("gemini-a72dtctl", "gemini-a72svc", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-admission-serviceable.boot.img", 1),
    ("dd dtc find", "dd dtc fdtget find", 1),
    ("runtime-proven-DTB", "admission-serviceability-DTB", 1),
    (".a72-live-image-runtime-dt-control.XXXXXXXX", ".a72-admission-serviceability.XXXXXXXX", 1),
    (old_semantics, new_semantics, 1),
    ("experiment=2026-08-28-mainline-a72-live-image-runtime-dt-control", "experiment=2026-08-28-mainline-a72-admission-serviceability-restoration", 1),
    ("control_dtb_runtime_candidate=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", "control_dtb_base=1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509", 1),
    ("controller_nodes=0\\nbinder_nodes=0", "controller_nodes=1\\nbinder_nodes=1", 1),
    ("validation=current-image-runtime-dt-package", "validation=admission-serviceability-restoration-package", 1),
    ("dt_semantics=platform-provider-protected-clock-prefix-without-admission-nodes", "dt_semantics=current-full-admission-tree-plus-proven-serviceability-transform", 1),
    ('output_name="candidate-a72-live-image-runtime-dt-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-admission-serviceable-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-live-image-runtime-dt-control-build", "validation=a72-admission-serviceability-restoration-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe serviceable-candidate derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
