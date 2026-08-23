#!/usr/bin/env bash

# Source-pin the manual-checkpoint builder and specialize it for the exact
# one-record raw-write qualification package, configuration, and container.
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

derived="$(mktemp "$script_dir/.manual-checkpoint-raw-write-builder.XXXXXXXX")"
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
     "manual-checkpoint one-record raw-write identities and closures", 1),
    (".manual-checkpoint-builder.XXXXXXXX",
     ".manual-checkpoint-raw-write-builder-inner.XXXXXXXX", 1),
    ("c1d59f3b1783f70e92b4ab27d11c5809f9722869",
     "24f0a696e1cedbf80f382ca04e9d812254c7e18f", 1),
    ("da921x-manual-checkpoint-control",
     "da921x-manual-checkpoint-raw-write", 1),
    ("7.1.3-gemini-checkpoint-ctl",
     "7.1.3-gemini-checkpoint-raw-write", 1),
    ("e796316372ed008aed2abccd4ed2acadf640105f6a641aff2dd0e48e61245959",
     "bf1b3fb57605fb207d2bf2cd9a8cc98c7127327195dc4d14a78169e6f58db715", 1),
    ("638a9732387c5b742905ed2b71698be9cda69cfb231ecf8400fb6c2a4ee9800a",
     "0c9b5db9fdadeb0c32d93a23bc6f8cbab0b50bf095a86ed05c19283e13e951f6", 1),
    ("411692b59d20ed2ed67fd64274e4f980119ff0607df4297342594a13b4ecf321",
     "ce61fec47cba4ab06f176aa68956aad81951b9f7b208e80a4f85a3b38f379341", 1),
    ("100b461163bfce3e4c15b69c5e7b2effdcfb760942ce4e55b9af61ade82468fa",
     "85805de3dab0fa0a9e4595cb4e4123f3a4cc17c145271e663bb6359711d53613", 1),
    ("39e5bb68be28a2b41fc1250a0271b38b2b9d103afe81961e14b6d6060d5a593e",
     "1bd62a99576b8746b68caf2ba71e4cefbc7c2b156d439475a173ab199907f4f3", 1),
    ("9d5fef4e7a100813c5d53451ae2a24a5c37efc37db7e19ef34a4f90df146e69d",
     "579cedd1396c4b86b9e9c9600ca9feab3590c59852db19fcec059cf2ff8435cd", 1),
    ("4338ac1ee770ea23087694f7c166226c2297874fd595751d1a235565ecee3805",
     "6a2f698fe05a67a96ccb8ff282ac62668170e229125fe3ddeae3257ac135adf3", 1),
    ("53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
     "c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631", 1),
    ("readonly RAW_SIZE=6893568", "readonly RAW_SIZE=6895616", 1),
    ("readonly BOOT_NAME=gemini-chkctl", "readonly BOOT_NAME=gemini-chkraw", 1),
    ("readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-control.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-manual-checkpoint-raw-write.boot.img", 1),
    ("'manual-checkpoint serviceability DTB'",
     "'manual-checkpoint raw-write serviceability DTB'", 1),
    (".manual-checkpoint-control.XXXXXXXX",
     ".manual-checkpoint-raw-write.XXXXXXXX", 1),
    ("portable-fetched-manual-checkpoint-control-package",
     "portable-fetched-manual-checkpoint-raw-write-package", 1),
    ("experiment=2026-08-21-mainline-manual-checkpoint-control",
     "experiment=2026-08-22-mainline-manual-checkpoint-raw-write-qualification", 1),
    ("runtime_hypothesis=shared-writer-completes-two-local-readbacks-on-serviceable-base",
     "runtime_hypothesis=one-raw-record-commits-and-recovers-before-protected-backend", 1),
    ("kernel_delta_from-last-runtime-proven=manual-writer-and-late-initcall-only",
     "kernel_delta_from-last-runtime-proven=default-off-one-record-raw-write-qualification", 1),
    ("candidate-manual-checkpoint-control-${RAW_SHA256:0:8}",
     "candidate-manual-checkpoint-raw-write-${RAW_SHA256:0:8}", 1),
    ("validation=manual-checkpoint-control-candidate-build",
     "validation=manual-checkpoint-raw-write-candidate-build", 1),
    ("'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y' \\",
     "'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y' \\\n\t'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION=y' \\", 1),
    ('CONFIG_LOCALVERSION="-gemini-checkpoint-ctl"',
     'CONFIG_LOCALVERSION="-gemini-checkpoint-raw-write"', 1),
    ("'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1'; do",
     "'GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1' \\\n\t'GEMINI_MANUAL_CHECKPOINT_STAGE_V1' \\\n\t'GEMINI_MANUAL_RAW_WRITE_QUALIFICATION_LIVE_V1'; do", 2),
    ("manual_checkpoint_retained_writes_expected=2",
     "manual_checkpoint_retained_writes_expected=exactly-1", 1),
    ("manual_checkpoint_local_full_readbacks_expected=2",
     "manual_checkpoint_local_full_readbacks_expected=exactly-1", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe raw-write candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

second_marker = (
    "\t'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A "
    "checkpoint=manual-second slot=174 crc32=c90b9e18' \\\n"
)
escaped_second_marker = (
    "\\t'GEMINI_MANUAL_CHECKPOINT_CONTROL_V1 token=GMCP-20260821-A "
    "checkpoint=manual-second slot=174 crc32=c90b9e18' \\\\\n"
)
if text.count(second_marker) != 1 or text.count(escaped_second_marker) != 1:
    raise SystemExit("unsafe unused second-record marker removal")
text = text.replace(second_marker, "")
text = text.replace(escaped_second_marker, "")
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
