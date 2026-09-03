#!/usr/bin/env bash

# Source-pin the proven Android-v0/LK assembler and retarget its exact inputs
# to the physical CPU9-off/same-boot-restore package and composed DT.
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

derived=$(mktemp "$script_dir/.derived-build-a72-physical-hotplug.XXXXXXXX")
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
[[ "$(grep -Fc 'mediatek,mt6797-a72-binder' "$workdir/control.dts")" == 1 ]] || die 'admission binder node changed'
[[ "$(grep -Fc 'planet,gemini-a72-runtime-binding-v1' "$workdir/control.dts")" == 1 ]] || die 'runtime provenance node changed'
[[ "$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' "$workdir/control.dts")" == 0 ]] || die 'standalone observer leaked into admission DT'
[[ "$(fdtget -ts "$control_dtb" /chosen/gemini-late-cpu-provenance compatible)" == planet,gemini-a72-runtime-binding-v1 ]] || die 'runtime provenance compatible changed'
[[ "$(fdtget -tbx "$control_dtb" /chosen/gemini-late-cpu-provenance record-identity)" == '86 fb c5 7b 39 76 60 94 65 f3 13 6f 69 43 7f 6f 4 b7 df 1c d4 af d3 b1 c0 d9 6 17 16 96 49 c9' ]] || die 'runtime provenance identity changed'
for node_path in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 /i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix /dvfsp-clock-backend@1001a000 /dvfsp-bigidvfs-backend; do
    [[ "$(fdtget -ts "$control_dtb" "$node_path" status)" == okay ]] || die "serviceability/admission node is not enabled: $node_path"
done'''
old_config = '''grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-admission-live"' "$config" || die 'local version changed'
grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' "$config" || die 'live trigger is absent from current Image' '''.rstrip()
new_config = '''grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-hotplug-physical"' "$config" || die 'local version changed'
for symbol in ARM64_MT6797_A72_CPU9_MEMBERSHIP PSTORE_GEMINI_CPU9_TRANSITION_LEDGER MTK_MT6797_A72_CPU9_EXECUTOR MTK_MT6797_A72_CPU9_BINDER MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER PSTORE_GEMINI_A72_HOTPLUG_LEDGER MTK_MT6797_A72_HOTPLUG_EXECUTOR MTK_MT6797_A72_HOTPLUG_SNAPSHOT MTK_MT6797_A72_CPU8_OBSERVER MTK_MT6797_A72_RESTORE_EXECUTOR MTK_MT6797_A72_HOTPLUG_BINDER_CORE MTK_MT6797_A72_HOTPLUG_BINDING; do
    grep -qx "CONFIG_${symbol}=y" "$config" || die "production hotplug symbol is absent: $symbol"
done
grep -q '^CONFIG_KUNIT=y$' "$config" && die 'KUnit leaked into production Image'
grep -q '^CONFIG_HOTPLUG_SPLIT_STARTUP=y$' "$config" && die 'split-startup policy changed' '''.rstrip()
replacements = (
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "46539642f0ce3587bb2dea9903b2bcdc9e9f1e8f", 1),
    ("readonly PROFILE=a72-admission-live-trigger-candidate", "readonly PROFILE=gemini-a72-hotplug-physical-candidate", 1),
    ("readonly RELEASE=7.1.3-gemini-a72-admission-live", "readonly RELEASE=7.1.3-gemini-a72-hotplug-physical", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "52c950f12df382e92a3f26c0719e2072428c966b3a39797d7d7723c666e3e4d6", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "9c9b46e94df6fb3ff531ba62d74b7817765cebbe8bd877f11d8117bba0fcebf9", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "a76237ab140491d0c11dd9560cf3eb11176476c910f0a5c889c70d1cf324e70a", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "ea298dbe3ac4296c455c6364329a03cdf244762c7165a98fcb865328acbd8a98", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "507827df6b27a5431d906a18ad78f827b7f086e3e392435e66b4911db06c7bd3", 1),
    ("0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", "590f47bb3e7a0df6d261c3cedb3c0ac3dc4b9d965566149cdd30675acb19767c", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "99415ca8c13fd6f30b34b805214ebbbbc1230951fae0c943c7cbaf6c1603439d", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "6e133cee640f141bb5b81790aea58fc58504b32871b3ff70e688997dab7eccdf", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "9b60b576efe1e1c7496953c098748205a8ec2ca4eaa322d9d6466fa8285a2136", 1),
    ("readonly RAW_SIZE=6934528", "readonly RAW_SIZE=6981632", 1),
    ("gemini-a72dtctl", "gemini-a72prov", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-hotplug-physical.boot.img", 1),
    ("dd dtc find", "dd dtc fdtget find", 1),
    (old_semantics, new_semantics, 1),
    (old_config, new_config, 1),
    ("die 'raw candidate changed'", "die \"raw candidate changed: expected-size=$RAW_SIZE sha=$raw_sha\"", 1),
    ("die 'padded candidate changed'", "die \"padded candidate changed: sha=$padded_sha\"", 1),
    ("experiment=2026-08-28-mainline-a72-live-image-runtime-dt-control", "experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate", 1),
    ("control_dtb_runtime_candidate=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", "control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ("controller_nodes=0\\nbinder_nodes=0\\ncpu8_requests=0\\ncpu9_requests=0\\ncpu_off_requests=0\\nretries=0", "controller_nodes=1\\nbinder_nodes=1\\ncandidate_cpu8_request_paths=1\\ncandidate_cpu9_request_paths=1\\nphysical_transaction_paths=1\\ncpu9_off_paths=1\\ncpu9_restore_paths=1\\nphysical_requests_during_validation=0\\nretries=0", 1),
    ("validation=current-image-runtime-dt-package", "validation=a72-physical-hotplug-package", 1),
    ("dt_semantics=platform-provider-protected-clock-prefix-without-admission-nodes", "dt_semantics=unchanged-serviceability-admission-tree-plus-physical-hotplug-package-provenance-leaf", 1),
    ('output_name="candidate-a72-live-image-runtime-dt-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-hotplug-physical-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-live-image-runtime-dt-control-build", "validation=a72-physical-hotplug-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug candidate derivation: expected {count}, "
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
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
