#!/usr/bin/env bash

# Source-pin the proven Android-v0/LK assembler and retarget its exact inputs
# to the unchanged READY-admission package plus the composed provenance DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4b8535bec6397a92d374f6c9e68ab5d99ed860c589273a07ec614237ebe0382a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-provenance-serviceability.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
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
[[ "$(grep -Fc 'planet,gemini-a72-runtime-binding-v1' "$workdir/control.dts")" == 1 ]] || die 'runtime provenance node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' "$workdir/control.dts")" == 0 ]] || die 'standalone observer leaked into admission DT'
[[ "$(fdtget -ts "$control_dtb" /chosen/gemini-late-cpu-provenance compatible)" == planet,gemini-a72-runtime-binding-v1 ]] || die 'runtime provenance compatible changed'
[[ "$(fdtget -tbx "$control_dtb" /chosen/gemini-late-cpu-provenance record-identity)" == '68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a' ]] || die 'runtime provenance identity changed'
for node_path in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 /i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix /dvfsp-clock-backend@1001a000 /dvfsp-bigidvfs-backend; do
    [[ "$(fdtget -ts "$control_dtb" "$node_path" status)" == okay ]] || die "serviceability/admission node is not enabled: $node_path"
done'''
replacements = (
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", 1),
    ("0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", "b17e485aa14119a7c56bea6ccc657b7d583ee1069642035b1201ae8848172634", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    ("readonly RAW_SIZE=6934528", "readonly RAW_SIZE=6948864", 1),
    ("gemini-a72dtctl", "gemini-a72prov", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-provenance-serviceability.boot.img", 1),
    ("dd dtc find", "dd dtc fdtget find", 1),
    (old_semantics, new_semantics, 1),
    ("die 'raw candidate changed'", "die \"raw candidate changed: sha=$raw_sha\"", 1),
    ("die 'padded candidate changed'", "die \"padded candidate changed: sha=$padded_sha\"", 1),
    ("experiment=2026-08-28-mainline-a72-live-image-runtime-dt-control", "experiment=2026-08-30-mainline-a72-provenance-serviceability-composition", 1),
    ("control_dtb_runtime_candidate=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", "control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ("controller_nodes=0\\nbinder_nodes=0", "controller_nodes=1\\nbinder_nodes=1", 1),
    ("cpu8_requests=0\\ncpu9_requests=0", "candidate_cpu8_request_paths=1\\ncpu8_requests=0\\ncpu9_requests=0", 1),
    ("validation=current-image-runtime-dt-package", "validation=provenance-serviceability-package", 1),
    ("dt_semantics=platform-provider-protected-clock-prefix-without-admission-nodes", "dt_semantics=serviceability-admission-tree-plus-package-exact-provenance-leaf", 1),
    ('output_name="candidate-a72-live-image-runtime-dt-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-provenance-serviceability-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-live-image-runtime-dt-control-build", "validation=a72-provenance-serviceability-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe candidate derivation: expected {count}, found {actual}: {old}")
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
