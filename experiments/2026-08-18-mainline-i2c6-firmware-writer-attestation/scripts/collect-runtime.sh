#!/usr/bin/env bash

# Source-pin and pre-arm one bounded USB/netcat attestation capture, then use
# the proven native return only after the immutable capture classifies safely.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6d9d8d3d683b99dff3630e6e172c269d6b4c858e0ae6e018a9d41e327d23ff00

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-collect-runtime.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("read-only provider", "I2C6 firmware-writer attestation", 1),
    ("eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854",
     "4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972", 1),
    ("cf25dd25266fc4f12f91d4d6e2b91c25f79b7da6617d6a4aaf1169796cb520e8",
     "1062f4f4a193f8f34b9e905a4ca856ee6275a3e2b16abfe4f17224ceeead04f1", 1),
    ("2b00879d1bc7a025de1d642262bdabe209c096a90c15aba403d09f034b69b324",
     "7172ab947ca60d14a968427b2700e3fbb66e35af4e1584f1434b5e74ea9b7a9c", 1),
    ("mainline-da921x-lkro-provider-attempt-1",
     "mainline-i2c6-fwatt-attempt-1", 2),
    ("remote-provider-probe.sh", "remote-attestation-probe.sh", 1),
    ("__DA921X_LKRO_BEGIN__", "__I2C6_FWATT_BEGIN__", 1),
    ("__DA921X_LKRO_END__", "__I2C6_FWATT_END__", 1),
    ("runtime_classification=success-read-only-provider",
     "runtime_classification=success-firmware-writer-attestation", 2),
    (".gemini-da921x-lkro.", ".gemini-i2c6-fwatt.", 1),
    ("DA921x_register_data_writes=0",
     "firmware_writer_attestation_register_writes=0", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe collector derivation: expected {count}, found {actual}: {old}"
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
