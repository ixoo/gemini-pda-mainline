#!/usr/bin/env bash

# Source-pin the audited direct candidate assembler and retarget it to the
# production P30E entry-publication repair package and composed runtime DT.
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

derived=$(mktemp "$script_dir/.derived-build-a72-p30e-entry-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "23b21b6f4f8cbb3af0cefd610d5d0e5961f7fa51", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "c59324bcd04b358a4563bd39d1dcb9c03a47ecef087b57a6b1d5b4cf03f4a82b", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "f629b74a5dc999d2e353bd25be4710d7bf696bc7dcc9b9558bda9e2f1edded74", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "967841597ace9128fded320c85d2c8f919bc11323ac092af0c631955910bd0ec", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "135703294fb2dfdecbf200b83e6dfb5d4e49241cbe64a27712d6e055772b35bc", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "7f5bf270c09b7f603c4f449a3c0e28fd63e6145c3a053bf36119c58753e399aa", 1),
    ("0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", "d8b1c5161d0b545ac5f3873929bfed12d0a0bb50fd459c7c093af2824d7d8961", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "461e2d1c4b88a79740747d6755d2c402bab6367c240380e8c2a20c6a47055de3", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "b80dfc49dd22a7830afdadbe3138c0e5131a2da1cbca7012d6c90ad09002e463", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),
    ("readonly RAW_SIZE=6934528", "readonly RAW_SIZE=6955008", 1),
    ("readonly BOOT_NAME=gemini-a72dtctl", "readonly BOOT_NAME=gemini-a72prov", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-p30e-entry-diagnostic.boot.img", 1),
    ("dtc find grep", "dtc fdtget find grep", 1),
    (
        "grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' \"$config\" || die 'live trigger is absent from current Image'",
        "grep -qx 'CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y' \"$config\" || die 'live trigger is absent from current Image'\n"
        "grep -qx 'CONFIG_ARM64_MT6797_A72_P30E_WIRE=y' \"$config\" || die 'P30E production wire is absent from current Image'\n"
        "grep -qx '# CONFIG_KUNIT is not set' \"$config\" || die 'KUnit leaked into production Image'\n"
        "for symbol in arm64_mt6797_a72_p30e_arm arm64_mt6797_a72_p30e_readback arm64_mt6797_a72_p30e_target_claim arm64_mt6797_a72_p30e_target_publish; do\n"
        "\tgrep -Eq \" [Tt] ${symbol}$\" \"$system_map\" || die \"P30E symbol missing: $symbol\"\n"
        "done",
        1,
    ),
    (
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-platform-state' \"$workdir/control.dts\")\" == 1 ]] || die 'platform-state node changed'\n"
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' \"$workdir/control.dts\")\" == 1 ]] || die 'composed observer node changed'\n"
        "[[ \"$(grep -Ec 'mt6797-a72-admission-controller|mt6797-a72-admission-binder' \"$workdir/control.dts\")\" == 0 ]] || die 'admission node leaked into control DT'",
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-platform-state' \"$workdir/control.dts\")\" == 1 ]] || die 'platform-state node changed'\n"
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-admission-controller' \"$workdir/control.dts\")\" == 1 ]] || die 'admission-controller node changed'\n"
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-binder' \"$workdir/control.dts\")\" == 1 ]] || die 'binder node changed'\n"
        "[[ \"$(grep -Fc 'planet,gemini-a72-runtime-binding-v1' \"$workdir/control.dts\")\" == 1 ]] || die 'runtime provenance node changed'\n"
        "[[ \"$(grep -Fc 'mediatek,mt6797-a72-platform-provider-clock-observer' \"$workdir/control.dts\")\" == 0 ]] || die 'standalone observer leaked into admission DT'\n"
        "[[ \"$(fdtget -ts \"$control_dtb\" /chosen/gemini-late-cpu-provenance compatible)\" == planet,gemini-a72-runtime-binding-v1 ]] || die 'runtime provenance compatible changed'\n"
        "[[ \"$(fdtget -tbx \"$control_dtb\" /chosen/gemini-late-cpu-provenance record-identity)\" == '96 fe 21 66 17 bc fb 42 15 94 f4 d1 f9 60 ef f9 62 ae 8a 92 2 11 cf 41 16 9b 30 f7 ed 55 94 55' ]] || die 'runtime provenance identity changed'\n"
        "for node_path in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 /i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix /dvfsp-clock-backend@1001a000 /dvfsp-bigidvfs-backend; do\n"
        "\t[[ \"$(fdtget -ts \"$control_dtb\" \"$node_path\" status)\" == okay ]] || die \"serviceability/admission node is not enabled: $node_path\"\n"
        "done",
        1,
    ),
    ("die 'raw candidate changed'", "die \"raw candidate changed: sha=$raw_sha\"", 1),
    ("die 'padded candidate changed'", "die \"padded candidate changed: sha=$padded_sha\"", 1),
    ("experiment=2026-08-28-mainline-a72-live-image-runtime-dt-control", "experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic", 1),
    ("control_dtb_runtime_candidate=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", "control_dtb_serviceability_base=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ("controller_nodes=0\\nbinder_nodes=0\\ncpu8_requests=0", "controller_nodes=1\\nbinder_nodes=1\\ncandidate_cpu8_request_paths=1\\ncpu8_requests=0", 1),
    ("validation=current-image-runtime-dt-package", "validation=p30e-entry-diagnostic-package", 1),
    ("dt_semantics=platform-provider-protected-clock-prefix-without-admission-nodes", "dt_semantics=serviceability-admission-tree-plus-package-exact-provenance-leaf", 1),
    ('output_name="candidate-a72-live-image-runtime-dt-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-p30e-entry-diagnostic-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-live-image-runtime-dt-control-build", "validation=a72-p30e-entry-diagnostic-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E candidate derivation: expected {count}, found {actual}: {old}"
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
