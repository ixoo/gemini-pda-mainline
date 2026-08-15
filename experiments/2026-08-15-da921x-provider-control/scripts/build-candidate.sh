#!/usr/bin/env bash

# Source-pin and mechanically derive the exact matched provider-only control
# candidate builder from the independently reviewed observer builder.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=8ec4f32f444b3d8fdf2670408bedea5e69c1b148aaa44eb2ce21eda289a177a8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-15-da921x-readonly-observer/scripts/build-candidate.sh"
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
    ("# Assemble the exact read-only observer Android-v0/LK candidate offline.",
     "# Assemble the exact matched provider-only Android-v0/LK control offline.", 1),
    ("readonly REPOSITORY_COMMIT=d0d511e60af343bdcc880b41b50acd2be877fa2b",
     "readonly REPOSITORY_COMMIT=1ab09cd9ef39a9c99c82e639dcbc15cb6040c74c", 1),
    ("readonly PROFILE=da921x-readonly-observer",
     "readonly PROFILE=da921x-resource-only-provider", 1),
    ("readonly RELEASE=7.1.3-gemini-da921x-observer",
     "readonly RELEASE=7.1.3-gemini-da921x-resource", 1),
    ("readonly IMAGE_SHA256=3483fb980c8c59ea0a10bf356737391aaa6b49969e39b4a3cee3831774f5fbf9",
     "readonly IMAGE_SHA256=7c32d659dd9eabef33800e2e5aa16e3f609d3cddf0c7efb8e7dc22159ad8cab5", 1),
    ("readonly IMAGE_GZIP_SHA256=5609a9a30b2959fd93144900461e4a07ba274adda04454ef534a2961d6a8c1b1",
     "readonly IMAGE_GZIP_SHA256=e9ad785fc00d96584ad7c29abc671864c8f03d1c7272610f8b64768b171b27c7", 1),
    ("readonly CONFIG_SHA256=0d707f8483ce7a5599625bb2a09889c642b3ee945d2ad3fa6cf6f7289363581a",
     "readonly CONFIG_SHA256=56a08dd0f2f4400044f15c2b597e23bbaeb1bd806658670c2d5facf3152d6ac6", 1),
    ("readonly SYSTEM_MAP_SHA256=665d70c58f771abc43d39b2b9b7244a28df9ae7ad4eb8856e4fbf678dd7e88dc",
     "readonly SYSTEM_MAP_SHA256=4dedb128f7a7e25d627b0f7191486e67b4cbde6f1df2e3692e9b971991e8a298", 1),
    ("readonly BUILD_JSON_SHA256=1643441936f8f88d8a7dc221007c4d5fc0616a9c697cda8fcb0b4eb380e61b4e",
     "readonly BUILD_JSON_SHA256=a614f5f8368758e6c24c9a497c5feb3c9243f362aa574aaf4cdd0135660c5e7d", 1),
    ("readonly PACKAGE_MANIFEST_SHA256=dcebb9929993b8e8affb86f37470d4b33ace97f7ef17eaee0247b3ad5e9439bf",
     "readonly PACKAGE_MANIFEST_SHA256=5a2665fc4f478a4e9699fa7f6271908bf1ca453afd50eb08ff02281d3153e56f", 1),
    ("readonly RAW_SHA256=1a55a25b7d6bff448802db3259ba65371c34657b341f0e621dc134bd700e7b14",
     "readonly RAW_SHA256=76d32c74a8ffb714bd10ee7b2e6d1483e4c87e5fa62f0f1ec47d121ea8b95fa9", 1),
    ("readonly PADDED_SHA256=7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564",
     "readonly PADDED_SHA256=3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2", 1),
    ("readonly BOOT_NAME=gemini-daobs", "readonly BOOT_NAME=gemini-dactl", 1),
    ("readonly BOOT_FILE=gemini-mt6797-da921x-readonly-observer.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-da921x-resource-control.boot.img", 1),
    ("grep -qx 'CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y' \"$config\" ||\n\tdie 'observer is not built in'\ngrep -qx '# CONFIG_KUNIT is not set' \"$config\" || die 'KUnit leaked into runtime image'\ngrep -q ' da9213_legacy_observer_collect$' \"$system_map\" || die 'observer symbol missing'\n! grep -q 'da9213_legacy_observer_test_suite' \"$system_map\" ||\n\tdie 'observer test symbol leaked into runtime image'",
     "grep -qx 'CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y' \"$config\" ||\n\tdie 'read-only provider is not built in'\ngrep -qx '# CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER is not set' \"$config\" ||\n\tdie 'observer unexpectedly enabled'\ngrep -qx '# CONFIG_KUNIT is not set' \"$config\" || die 'KUnit leaked into runtime image'\ngrep -q ' da9213_legacy_probe$' \"$system_map\" || die 'provider probe symbol missing'\n! grep -q ' da9213_legacy_observer_collect$' \"$system_map\" ||\n\tdie 'observer symbol leaked into control image'", 1),
    (".da921x-observer-candidate.XXXXXXXX", ".da921x-provider-control.XXXXXXXX", 1),
    ("experiment=2026-08-15-da921x-readonly-observer",
     "experiment=2026-08-15-da921x-provider-control", 1),
    ("runtime_hypothesis=one-attributable-read-only-provider-observation",
     "runtime_hypothesis=matched-provider-only-control-reaches-usb-without-observer", 1),
    ("output_name=\"candidate-da921x-readonly-observer-${RAW_SHA256:0:8}\"",
     "output_name=\"candidate-da921x-provider-control-${RAW_SHA256:0:8}\"", 1),
    ("validation=da921x-readonly-observer-candidate-build",
     "validation=da921x-provider-control-candidate-build", 1),
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
