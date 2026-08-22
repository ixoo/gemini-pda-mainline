#!/usr/bin/env bash

# Source-pin the manual-checkpoint builder and specialize it for the exact
# live prefix-reason package, configuration, markers, and container.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=641867c5f52eb2f9427f30ede4c3c4fe942379c062ce6a4291a33669d354dc49

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.manual-checkpoint-prefix-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("manual-checkpoint control identities and closures",
     "manual-checkpoint live prefix-reason identities and closures", 1),
    (".manual-checkpoint-builder.XXXXXXXX", ".manual-checkpoint-prefix-builder-inner.XXXXXXXX", 1),
    ("c1d59f3b1783f70e92b4ab27d11c5809f9722869",
     "49f8e7f31c29cecde992a048103f2591e6a1aef1", 1),
    ("da921x-manual-checkpoint-control", "da921x-manual-checkpoint-prefix-control", 1),
    ("7.1.3-gemini-checkpoint-ctl", "7.1.3-gemini-checkpoint-prefix", 1),
    ("e796316372ed008aed2abccd4ed2acadf640105f6a641aff2dd0e48e61245959",
     "6340299f8ef5cc33bdf4828a0bbd3e453cb569cf57804cfd8526922859c757dd", 1),
    ("638a9732387c5b742905ed2b71698be9cda69cfb231ecf8400fb6c2a4ee9800a",
     "ed2f64374f0f0d5b40b012ba3c914e3c6fadd5d9e073300679e035f15c7ab0dd", 1),
    ("411692b59d20ed2ed67fd64274e4f980119ff0607df4297342594a13b4ecf321",
     "4ab905bd150c5890d7a38962aafb12c695a33ac873630623144110131cd28205", 1),
    ("100b461163bfce3e4c15b69c5e7b2effdcfb760942ce4e55b9af61ade82468fa",
     "a9547ad04f47043b5f865637d80b6fcc408e05a2334d69b01a1440871f4a6b6d", 1),
    ("39e5bb68be28a2b41fc1250a0271b38b2b9d103afe81961e14b6d6060d5a593e",
     "ff38c25b4b68832fd6bd9797c37bc43d693b2247b3779af9ff1d1248b6b99960", 1),
    ("9d5fef4e7a100813c5d53451ae2a24a5c37efc37db7e19ef34a4f90df146e69d",
     "2a5df2760ea35af83edc68bdea8aa19844dbff812cbfeb896a0bca6e186a430a", 1),
    ("4338ac1ee770ea23087694f7c166226c2297874fd595751d1a235565ecee3805",
     "1d69e03378ae880d1b4f52f6350cd27e9be322478dcec0c022d91d7d0885e6ee", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901", 1),
    ("readonly RAW_SIZE=6893568", "readonly RAW_SIZE=6895616", 1),
    ("readonly BOOT_NAME=gemini-chkctl", "readonly BOOT_NAME=gemini-chkpfx", 1),
    ("readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-control.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-prefix-control.boot.img", 1),
    ("'manual-checkpoint serviceability DTB'", "'manual-checkpoint prefix serviceability DTB'", 1),
    (".manual-checkpoint-control.XXXXXXXX", ".manual-checkpoint-prefix-control.XXXXXXXX", 1),
    ("portable-fetched-manual-checkpoint-control-package",
     "portable-fetched-manual-checkpoint-prefix-control-package", 1),
    ("experiment=2026-08-21-mainline-manual-checkpoint-control",
     "experiment=2026-08-21-mainline-manual-checkpoint-prefix-control", 1),
    ("runtime_hypothesis=shared-writer-completes-two-local-readbacks-on-serviceable-base",
     "runtime_hypothesis=one-live-prefix-reason-identifies-first-header-refusal", 1),
    ("kernel_delta_from-last-runtime-proven=manual-writer-and-late-initcall-only",
     "kernel_delta_from-last-runtime-proven=default-off-post-refusal-three-read-snapshot-only", 1),
    ("candidate-manual-checkpoint-control-${RAW_SHA256:0:8}",
     "candidate-manual-checkpoint-prefix-control-${RAW_SHA256:0:8}", 1),
    ("validation=manual-checkpoint-control-candidate-build",
     "validation=manual-checkpoint-prefix-control-candidate-build", 1),
    ("'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y' \\",
     "'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y' \\", 1),
    ('CONFIG_LOCALVERSION="-gemini-checkpoint-ctl"',
     'CONFIG_LOCALVERSION="-gemini-checkpoint-prefix"', 1),
    ("'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1'; do",
     "'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1' \\\n\t'GEMINI_MANUAL_CHECKPOINT_STAGE_V1' \\\n\t'GEMINI_MANUAL_CHECKPOINT_PREFIX_V1'; do", 2),
    ("manual_checkpoint_retained_writes_expected=2",
     "manual_checkpoint_retained_writes_expected=prefix-refusal-consistent-0", 1),
    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=prefix-refusal-consistent-0", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe prefix candidate derivation: expected {count}, found {actual}: {old}"
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
