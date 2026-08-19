#!/usr/bin/env bash

# Source-pin and derive the exact I2C6 firmware-writer attestation candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d009349c0d8446af61e0733e9752bcce88cfed648f8c94ef0e8ed40ff9672b55

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/scripts/build-candidate.sh"
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
    ("read-only preflight/ledger candidate",
     "I2C6 firmware-writer attestation candidate", 1),
    ("experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/build-provider-dtb.sh",
     "experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/scripts/build-attestation-dtb.sh", 1),
    ("b40340ee88a0346959da9a145530971fdfaad781611a6603154a98f8536c5cd5",
     "d64c7f6dcf05693f89411c61e6fed5bb2a129e802ffe8051cd27d719975c9735", 1),
    ("f2837f05083bf2ee5e3caa28b3415d529ecd104b",
     "9ed564adac77042d9d0dff9dabc98b6caa646aca", 2),
    ("da921x-readonly-preflight-ledger",
     "da921x-i2c6-firmware-writer-attestation", 3),
    ("7.1.3-gemini-da921x-preflight", "7.1.3-gemini-i2c6-fwatt", 2),
    ("2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04",
     "72d019e54409238a201d69941fd2b3829d99e8beeeea1c1c2124a27fbc0c8ebb", 1),
    ("c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34",
     "6fc835e4ee3fac426c13993bb9b409a678197679115d4f33160f1eaa326730e9", 1),
    ("d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48",
     "80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683", 2),
    ("28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27",
     "bfd4fcbda62ed8e335e4343fbc3942bd5e22da290b39be78cd1c007163548a6f", 1),
    ("4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a",
     "e34ce1c507e110cefa8c7964a893ed22720d170a38b3f74ff0f9e55654f50452", 1),
    ("939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb",
     "94ef393cd97d0046f762fa438596df83bbd85bab9b82a8b46491ad43f08213fd", 1),
    ("a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578",
     "791ddea68da68b8b6342ff030e1c8061148ff300ab553ec2bb82bf187df54d1d", 1),
    ("4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7",
     "7d8efed2f932e0a61e9417ae062fbb8b72b0baddc21c3857fb15093e0446c22b", 2),
    ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
     "4bdaef917acd477839cdc3129b2fa4a63591e29c6fa912afd214bc9a1f5d0972", 2),
    ("readonly RAW_SIZE=6891520", "readonly RAW_SIZE=6893568", 1),
    ("gemini-preflt", "gemini-fwatt", 1),
    ("gemini-mt6797-da921x-preflight.boot.img",
     "gemini-mt6797-i2c6-fwatt.boot.img", 1),
    ("candidate-mainline-da921x-preflight",
     "candidate-mainline-i2c6-fwatt", 2),
    ("mt6797-gemini-pda-da921x-preflight.dtb",
     "mt6797-gemini-pda-i2c6-fwatt.dtb", 1),
    (".da921x-preflight", ".i2c6-fwatt", 2),
    ("provider DTB", "attestation DTB", 2),
    ("read-only preflight DTB", "read-only firmware-writer attestation DTB", 1),
    ("portable-fetched-kernel-package-with-read-only-DA921x-preflight",
     "portable-fetched-kernel-package-with-I2C6-firmware-writer-attestation", 1),
    ("control_dtb_source=package-LK-clocks-plus-exact-serviceability-group",
     "control_dtb_source=proven-provider-plus-read-only-SCP-DEVAPC-windows", 1),
    ("2026-08-17-mainline-da921x-i2c6-firmware-writer-attestation",
     "2026-08-18-mainline-i2c6-firmware-writer-attestation", 1),
    ("runtime_hypothesis=exact-I2C6-ledger-plus-stable-read-only-DA921x-preflight",
     "runtime_hypothesis=two-sample-SCP-reset-PC-and-DEVAPC-attestation", 1),
    ("kernel_delta_from-proven-provider=read-only-I2C6-ledger-plus-preflight",
     "kernel_delta_from-proven-provider=fail-closed-read-only-firmware-writer-attestation", 1),
    ("dtb_delta_from-package=exact-proven-serviceability-group-only",
     "dtb_delta_from-package=serviceability-plus-named-SCP-DEVAPC-read-windows", 1),
    ("mainline-da921x-readonly-preflight-candidate-build",
     "mainline-i2c6-firmware-writer-attestation-candidate-build", 1),
    ("mainline-da921x-readonly-preflight-wrapper",
     "mainline-i2c6-firmware-writer-attestation-wrapper", 1),
    ("\t'CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y' \\\n"
     "\t'CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y' \\\n"
     "\t'CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y' \\\n",
     "\t'# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set' \\\n"
     "\t'# CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT is not set' \\\n"
     "\t'CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y' \\\n"
     "\t'# CONFIG_REMOTEPROC is not set' \\\n", 1),
    ("DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads",
     "DA921x_runtime_operations=identity-reads,provider-reads-only", 1),
    ("I2C6_ledger_expected_entries=30",
     "firmware_writer_attestation_register_writes=0", 2),
    ("I2C6_ledger_capacity=32",
     "firmware_writer_attestation_i2c6_transfers=0", 1),
    ("printf 'firmware_writer_attestation_register_writes=0\\nDA921x_register_data_writes_expected=0\\n'",
     "printf 'firmware_writer_attestation_register_writes=0\\nfirmware_writer_attestation_i2c6_transfers=0\\nDA921x_register_data_writes_expected=0\\n'", 1),
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
cleanup
trap - EXIT HUP INT TERM
exit "$status"
