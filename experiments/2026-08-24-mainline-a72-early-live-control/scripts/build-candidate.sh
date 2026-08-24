#!/usr/bin/env bash

# Source-pin the reviewed Stage-27 DTB control builder and retarget only its
# exact kernel package, early-initcall policy, names, and candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=cb653690a9ab76d52fc40ea808d2df1bce107b19987616857f81b4f20abf3771

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived=$(mktemp "$script_dir/.derived-build-a72-early-live.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old_config = """\
grep -qx 'CONFIG_MODULES=y' "$config" || die 'module policy changed'
grep -qx '# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set' "$config" ||
	die 'old ledger leaked into control'
grep -qx 'CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y' "$config" ||
	die 'arm64 entry ledger is absent'
grep -qx '# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set' "$config" ||
	die 'post-ramoops checkpoint leaked into control'
for marker in 'GAEL-20260816-A E0' 'GAEL-20260816-A E1' \\
	'GAEL-20260816-A E2' 'GAEL-20260816-A E3'; do"""
new_config = """\
grep -qx 'CONFIG_MODULES=y' "$config" || die 'module policy changed'
grep -qx 'CONFIG_LOCALVERSION="-gemini-a72-early"' "$config" ||
	die 'local version changed'
grep -qx '# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set' "$config" ||
	die 'physical-source mode leaked into control'
grep -qx '# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set' "$config" ||
	die 'precapture mode leaked into control'
grep -qx '# CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER is not set' "$config" ||
	die 'global-initcall mode leaked into control'
grep -qx 'CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER=y' "$config" ||
	die 'early-initcall ledger is absent'
for marker in \\
	'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f' \\
	'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5' \\
	'GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init outcome=primary-refused slot=2 crc32=5767e326'; do"""
replacements = (
    ("exact GAEL kernel", "exact A72 early-initcall kernel", 1),
    ("98996fdfbf09f8de2a6b86e488defef22fcc7968", "26274db63316bbb24eeb9bfa8de21759da666b9e", 1),
    ("readonly PROFILE=da921x-modules-arm64-entry-ledger", "readonly PROFILE=a72-early-initcall-ledger", 1),
    ("readonly RELEASE=7.1.3-gemini-entryled-a", "readonly RELEASE=7.1.3-gemini-a72-early", 1),
    ("37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84", "6a990065ed3be26bb1ec113a578baba68600733d00f46bff45783569a22bfce0", 1),
    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe", "00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293", 1),
    ("e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323", "d951032cfaee8e05c5ff0c69e689a1384375d2ddce657481722451261ba332dd", 1),
    ("dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec", "16807a1bfadb4175156f162ae0656326afc93ed636dec48b829a0d67224b23c8", 1),
    ("88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee", "738759ca844d9da96db082c30e31670e2e59b4a858c9a6bf12b4c98ed0ad5e8b", 1),
    ("a9d2f7d81b61eab7dd3afbaba715778ea2785088bf4d7b098043a803c8e86ce5", "4753b29adba9e4cc340d7768c44a04a40d31c7e403a287ccf363cbfc5bb5f890", 1),
    ("e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086", "32ff42b3e8ba07e5b0267b521118f906aa27bd737613ae76a119961d3acc9e0d", 1),
    ("68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67", "070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", 1),
    ("readonly RAW_SIZE=6879232", "readonly RAW_SIZE=6909952", 1),
    ("readonly BOOT_NAME=gemini-dtbctl", "readonly BOOT_NAME=gemini-a72live", 1),
    ("readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img", "readonly BOOT_FILE=gemini-mt6797-a72-early-live-control.boot.img", 1),
    (old_config, new_config, 1),
    (".lk-handoff-dtb-control.XXXXXXXX", ".a72-early-live-control.XXXXXXXX", 1),
    ("validation=portable-fetched-kernel-package-with-runtime-proven-dtb-control", "validation=portable-fetched-a72-early-package-with-runtime-proven-dtb-control", 1),
    ("experiment=2026-08-16-mainline-lk-handoff-dtb-control", "experiment=2026-08-24-mainline-a72-early-live-control", 1),
    ("runtime_hypothesis=stage27_dtb_distinguishes_lk_dtb_processing_from_image_entry", "runtime_hypothesis=exact-current-kernel-reaches-live-usb-with-runtime-proven-stage27-dtb", 1),
    ("kernel_delta_from_stopped_gael=none", "kernel_delta_from_retired_early_initcall=none", 1),
    ("dtb_delta_from_stopped_gael=exact-runtime-proven-stage27-dtb", "dtb_delta_from_retired_early_initcall=exact-runtime-proven-stage27-dtb", 1),
    ('output_name="candidate-lk-handoff-dtb-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-early-live-control-${RAW_SHA256:0:8}"', 1),
    ("validation=lk-handoff-dtb-control-candidate-build", "validation=a72-early-live-control-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-control builder derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
