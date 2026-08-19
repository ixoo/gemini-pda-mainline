#!/usr/bin/env bash

# Source-pin and pre-arm one bounded USB/netcat transaction-window capture,
# then use the proven native return only after the immutable capture passes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b264285548c9d3dc375c85896e623a1d0e34ce52b28d48e66f298023a8145028

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/scripts/collect-runtime.sh"
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
    ("4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972",
     "fd6680d6e0ab3fbd61cc4f46b517a4672dd115eed92f2bbc0ae788b6e263c760", 1),
    ("1062f4f4a193f8f34b9e905a4ca856ee6275a3e2b16abfe4f17224ceeead04f1",
     "df605b3941ee1dffdf6d5afa33bd3c48169c9ea974a9cc0bacb8e1cceb29f459", 1),
    ("7172ab947ca60d14a968427b2700e3fbb66e35af4e1584f1434b5e74ea9b7a9c",
     "a80aa71544263f9a74634e45791aea32fd2b3879e74c83b68dbb3cc3cdb59908", 1),
    ("mainline-i2c6-fwatt-attempt-1", "mainline-i2c6-fwtxn-attempt-1", 1),
    ("remote-attestation-probe.sh", "remote-transaction-window-probe.sh", 1),
    ("__I2C6_FWATT_BEGIN__", "__I2C6_FWTXN_BEGIN__", 1),
    ("__I2C6_FWATT_END__", "__I2C6_FWTXN_END__", 1),
    ("runtime_classification=success-firmware-writer-attestation",
     "runtime_classification=success-firmware-writer-transaction-window", 1),
    (".gemini-i2c6-fwatt.", ".gemini-i2c6-fwtxn.", 1),
    ("firmware_writer_attestation_register_writes=0",
     "DA921x_register_data_writes=0", 1),
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
