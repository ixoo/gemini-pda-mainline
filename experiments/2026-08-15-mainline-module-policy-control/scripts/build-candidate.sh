#!/usr/bin/env bash

# Source-pin and mechanically derive the exact module-policy serviceability
# control builder from the reviewed provider-only control builder.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c2e626280474b99b28b95866aeccca6b67f048a187f4b15c098c046fa1787692

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-15-da921x-provider-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.derived-build-candidate.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Source-pin and mechanically derive the exact matched provider-only control",
     "# Source-pin and mechanically derive the exact module-policy serviceability control", 1),
    ("\"readonly REPOSITORY_COMMIT=1ab09cd9ef39a9c99c82e639dcbc15cb6040c74c\"",
     "\"readonly REPOSITORY_COMMIT=09ba93dbe1aa462795f1a1f4f0e82e31f5392989\"", 1),
    ("\"readonly PROFILE=da921x-resource-only-provider\"",
     "\"readonly PROFILE=da921x-resource-only-provider-modules-control\"", 1),
    ("\"readonly RELEASE=7.1.3-gemini-da921x-resource\"",
     "\"readonly RELEASE=7.1.3-gemini-da921x-modctl\"", 1),
    ("\"readonly IMAGE_SHA256=7c32d659dd9eabef33800e2e5aa16e3f609d3cddf0c7efb8e7dc22159ad8cab5\"",
     "\"readonly IMAGE_SHA256=ca9d18d721916efa994a8e5623adc52f08a105b3676ada960077236f78e101df\"", 1),
    ("\"readonly IMAGE_GZIP_SHA256=e9ad785fc00d96584ad7c29abc671864c8f03d1c7272610f8b64768b171b27c7\"",
     "\"readonly IMAGE_GZIP_SHA256=86cdcb5bec92aa8cd6d292e27f44df06e3cca78305862bbb5026b6c094174b7e\"", 1),
    ("\"readonly CONFIG_SHA256=56a08dd0f2f4400044f15c2b597e23bbaeb1bd806658670c2d5facf3152d6ac6\"",
     "\"readonly CONFIG_SHA256=f65d2cf39070e8ba0427e8745bd8aa615869abf048698a18251c6c07a69d26b2\"", 1),
    ("\"readonly SYSTEM_MAP_SHA256=4dedb128f7a7e25d627b0f7191486e67b4cbde6f1df2e3692e9b971991e8a298\"",
     "\"readonly SYSTEM_MAP_SHA256=7093fe54510224c1c4cbf83562a8d6650f6ac0b03fa71a2da19c81f7b3846b34\"", 1),
    ("\"readonly BUILD_JSON_SHA256=a614f5f8368758e6c24c9a497c5feb3c9243f362aa574aaf4cdd0135660c5e7d\"",
     "\"readonly BUILD_JSON_SHA256=bdd3bd798f2edc5f0936d3a05bf21c58a24b1fa6f424e62c47c34a1decf4cacf\"", 1),
    ("\"readonly PACKAGE_MANIFEST_SHA256=5a2665fc4f478a4e9699fa7f6271908bf1ca453afd50eb08ff02281d3153e56f\"",
     "\"readonly PACKAGE_MANIFEST_SHA256=706aa2b12941d2b65fee3a8f34955e001bffc4917a95572bd93540172f87fe4a\"", 1),
    ("\"readonly RAW_SHA256=76d32c74a8ffb714bd10ee7b2e6d1483e4c87e5fa62f0f1ec47d121ea8b95fa9\"",
     "\"readonly RAW_SHA256=782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040\"", 1),
    ("\"readonly PADDED_SHA256=3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2\"",
     "\"readonly PADDED_SHA256=044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff\"", 1),
    ("    (\"readonly BOOT_NAME=gemini-daobs\", \"readonly BOOT_NAME=gemini-dactl\", 1),",
     "    (\"readonly RAW_SIZE=7761920\", \"readonly RAW_SIZE=6881280\", 1),\n"
     "    (\"readonly BOOT_NAME=gemini-daobs\", \"readonly BOOT_NAME=gemini-modctl\", 1),", 1),
    ("\"readonly BOOT_FILE=gemini-mt6797-da921x-resource-control.boot.img\"",
     "\"readonly BOOT_FILE=gemini-mt6797-da921x-module-policy-control.boot.img\"", 1),
    (".da921x-provider-control.XXXXXXXX", ".da921x-module-policy-control.XXXXXXXX", 1),
    ("experiment=2026-08-15-da921x-provider-control",
     "experiment=2026-08-15-mainline-module-policy-control", 1),
    ("runtime_hypothesis=matched-provider-only-control-reaches-usb-without-observer",
     "runtime_hypothesis=module-policy-restoration-recovers-serviceability", 1),
    ("candidate-da921x-provider-control-${RAW_SHA256:0:8}",
     "candidate-da921x-module-policy-control-${RAW_SHA256:0:8}", 1),
    ("validation=da921x-provider-control-candidate-build",
     "validation=da921x-module-policy-control-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
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
