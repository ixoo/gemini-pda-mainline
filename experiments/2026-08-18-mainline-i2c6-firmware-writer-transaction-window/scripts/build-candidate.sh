#!/usr/bin/env bash

# Source-pin and derive the exact I2C6 firmware-writer transaction-window
# candidate from the preceding attestation candidate builder.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=edbd550ba0ee3e4b7af868d5a8d6596e18c8a68ed09029e39e210f9921a0dc5a
readonly RAW_SHA256=db828e1a6295167f8b370f04e87e675dba9bc08b6c0908283c3b11fe2cca7549
readonly PADDED_SHA256=fd6680d6e0ab3fbd61cc4f46b517a4672dd115eed92f2bbc0ae788b6e263c760

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname grep mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

package=
output_parent=
previous=
for argument in "$@"; do
	if [[ "$previous" == --package ]]; then package=$argument; fi
	if [[ "$previous" == --output-parent ]]; then output_parent=$argument; fi
	previous=$argument
done
[[ -n "$package" && -n "$output_parent" ]] || die 'package or output parent is absent'
config="$package/kernel.config"
[[ -f "$config" && ! -L "$config" ]] || die 'package configuration is unsafe'
for gate in \
	'CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y' \
	'CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y' \
	'CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y' \
	'CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y' \
	'# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set' \
	'# CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT is not set' \
	'# CONFIG_REMOTEPROC is not set'; do
	grep -Fqx "$gate" "$config" || die "configuration gate missing: $gate"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source builder is missing or unsafe'
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
    ("9ed564adac77042d9d0dff9dabc98b6caa646aca",
     "21728a382e771d7e11b4b9bf0392037002ffd572", 1),
    ("da921x-i2c6-firmware-writer-attestation",
     "da921x-i2c6-firmware-writer-transaction-window", 2),
    ("7.1.3-gemini-i2c6-fwatt", "7.1.3-gemini-i2c6-fwtxn", 1),
    ("72d019e54409238a201d69941fd2b3829d99e8beeeea1c1c2124a27fbc0c8ebb",
     "ac943b89424976e081f9456a5875d4590b5d58f97d1b67bb72587a4407901b33", 1),
    ("6fc835e4ee3fac426c13993bb9b409a678197679115d4f33160f1eaa326730e9",
     "9fa80052966f62822ad010784c374bed65714502410e89915d47ec4f0eca2ff9", 1),
    ("bfd4fcbda62ed8e335e4343fbc3942bd5e22da290b39be78cd1c007163548a6f",
     "a6ebe65225cea56cb176545fab2620affabd0ec8062a9e3a1ef1160f3f4e32d0", 1),
    ("e34ce1c507e110cefa8c7964a893ed22720d170a38b3f74ff0f9e55654f50452",
     "a8bc482a268c8223f3205d77fa220eebd8a6ca585c47a0ac5ab528297181431c", 1),
    ("94ef393cd97d0046f762fa438596df83bbd85bab9b82a8b46491ad43f08213fd",
     "44afe75ba245bc9575995df34f4292ca23fb193b094aa5ed07581fdbf38d17b6", 1),
    ("791ddea68da68b8b6342ff030e1c8061148ff300ab553ec2bb82bf187df54d1d",
     "d7d4d1842ac2b07e29b25d025fd1ba6e922008ae7815a98822860182604ff4d7", 1),
    ("7d8efed2f932e0a61e9417ae062fbb8b72b0baddc21c3857fb15093e0446c22b",
     "db828e1a6295167f8b370f04e87e675dba9bc08b6c0908283c3b11fe2cca7549", 1),
    ("4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972",
     "fd6680d6e0ab3fbd61cc4f46b517a4672dd115eed92f2bbc0ae788b6e263c760", 1),
    ('("gemini-preflt", "gemini-fwatt", 1)',
     '("gemini-preflt", "gemini-fwtxn", 1)', 1),
    ("gemini-mt6797-i2c6-fwatt.boot.img",
     "gemini-mt6797-i2c6-fwtxn.boot.img", 1),
    ("candidate-mainline-i2c6-fwatt", "candidate-mainline-i2c6-fwtxn", 1),
    ("mt6797-gemini-pda-i2c6-fwatt.dtb",
     "mt6797-gemini-pda-i2c6-fwtxn.dtb", 1),
    (".i2c6-fwatt", ".i2c6-fwtxn", 1),
    ("mainline-i2c6-firmware-writer-attestation-candidate-build",
     "mainline-i2c6-firmware-writer-transaction-window-candidate-build", 1),
    ("mainline-i2c6-firmware-writer-attestation-wrapper",
     "mainline-i2c6-firmware-writer-transaction-window-wrapper", 1),
    ('"2026-08-18-mainline-i2c6-firmware-writer-attestation", 1)',
     '"2026-08-18-mainline-i2c6-firmware-writer-transaction-window", 1)', 1),
    ("runtime_hypothesis=two-sample-SCP-reset-PC-and-DEVAPC-attestation",
     "runtime_hypothesis=SCP-reset-zero-at-both-edges-of-exact-20-read-only-I2C6-transactions", 1),
    ("kernel_delta_from-proven-provider=fail-closed-read-only-firmware-writer-attestation",
     "kernel_delta_from-proven-provider=read-only-SCP-reset-guarded-I2C6-transaction-window", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
(( status == 0 )) || exit "$status"

output_parent="$(cd -- "$output_parent" && pwd -P)"
candidate="$output_parent/candidate-mainline-i2c6-fwtxn-${RAW_SHA256:0:8}"
[[ -d "$candidate" && ! -L "$candidate" ]] || die 'derived candidate is absent or unsafe'
python3 - "$candidate/provenance.txt" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")
old = "firmware_writer_attestation_i2c6_transfers=0\n"
new = (
    "firmware_writer_attestation_i2c6_transfers=0\n"
    "transaction_window_expected_entries=20\n"
    "transaction_entry_reset_checks_expected=20\n"
    "transaction_exit_reset_checks_expected=20\n"
    "transaction_reset_failures_expected=0\n"
    "I2C6_entry_ledger_expected_entries=20\n"
    "I2C6_entry_ledger_capacity=32\n"
)
if text.count(old) != 1:
    raise SystemExit("unsafe transaction-window provenance extension")
path.write_text(text.replace(old, new), encoding="ascii")
PY
(
	cd "$candidate"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$candidate/SHA256SUMS"
(cd "$candidate" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'transaction-window candidate manifest failed'

cleanup
trap - EXIT HUP INT TERM
printf 'validation=mainline-i2c6-firmware-writer-transaction-window-wrapper\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$candidate" "$RAW_SHA256" "$PADDED_SHA256"
printf 'transaction_entry_reset_checks_expected=20\n'
printf 'transaction_exit_reset_checks_expected=20\n'
printf 'I2C6_entry_ledger_expected_entries=20\n'
printf 'CPU8_CPU9_admission=closed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
