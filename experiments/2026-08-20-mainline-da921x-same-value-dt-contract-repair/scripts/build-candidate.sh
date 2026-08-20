#!/usr/bin/env bash

# Derive the same-value-write candidate with the matching three-window handoff DT.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d009349c0d8446af61e0733e9752bcce88cfed648f8c94ef0e8ed40ff9672b55

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname find mktemp python3 rm sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-preflight-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

output_parent=
previous=
for argument in "$@"; do
	[[ "$previous" != --output-parent ]] || output_parent=$argument
	previous=$argument
done
[[ -n "$output_parent" ]] || die '--output-parent is required'

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
    ("DA921x read-only preflight/ledger candidate",
     "DA921x same-value-write DT-contract-repaired candidate", 1),
    ("experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/build-provider-dtb.sh",
     "experiments/2026-08-18-mainline-i2c6-firmware-writer-attestation/scripts/build-attestation-dtb.sh", 1),
    ("b40340ee88a0346959da9a145530971fdfaad781611a6603154a98f8536c5cd5",
     "d64c7f6dcf05693f89411c61e6fed5bb2a129e802ffe8051cd27d719975c9735", 1),
    ("f2837f05083bf2ee5e3caa28b3415d529ecd104b",
     "7c012d736f78898be08bfd8430a25c8708a62e1d", 2),
    ("da921x-readonly-preflight-ledger", "da921x-same-value-write", 3),
    ("7.1.3-gemini-da921x-preflight", "7.1.3-gemini-da921x-same-write", 2),
    ("d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48",
     "80972fc24406d5be8818c891d06fb8ed4d40f2332bd1eda2d8263597029ea683", 2),
    ("4a0c440604ac4ebd82a1fa139020f02ae4d758cc9b89bc6509a782434d8e62e7",
     "87b38fc41969f3bfcc33ef814f10b5987e32fdfd3d25b2a35fc703fe40fd5f83", 2),
    ("41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3",
     "85dbd8d020cc6d3527743f05d4a1071a8f573407a5519ae1584127e55e33bae9", 2),
    ("readonly RAW_SIZE=6891520", "readonly RAW_SIZE=6895616", 1),
    ("candidate-mainline-da921x-preflight", "candidate-mainline-da921x-same-value-dt-repair", 2),
    ("mt6797-gemini-pda-da921x-preflight.dtb", "mt6797-gemini-pda-da921x-same-value-dt-repair.dtb", 1),
    ("2ecc140cd87f151107b6ad5b21491232962d4a33b39d5770e77bf08f13b7bc04",
     "595056ac4cee9ff0a5b79287dca18bdc24f48374ffa7a3ef2647a0255cf1773c", 1),
    ("c8225bc2355083d02171b9113d89ea931ece4be0edec9ee1e5c04002fab59a34",
     "9327bd97af0ef8b2470c6eb769b0f96b562b855d4049289d3e0890c2739a5b29", 1),
    ("28c1bccede0210991a42b31e4a342d8f543222605e4096c02b718b4b503c7c27",
     "61590965540ad27624b64c8906a58f87d36ed15821e769f5ec93871f39695614", 1),
    ("4087c7671b46c57b0e9221511db6e8918d8eef6402d8e102148fd9d060580b0a",
     "321606b03dbeff1facfe8c9fa1404550457458eb862320054d0e1d823b8a91b2", 1),
    ("939b7c3a575dea3e1bcd06d8d8c0fb622b4c7b5b7af7c6435a30f0bb2dcb76cb",
     "4c39328d8a75d173ac262ba07159064d1069a0d1097964a23a48aaef40e19bd2", 1),
    ("a2a185aed8291f4f9f578bbbe6b65b9d4b3d3d3749347f675baa189fda886578",
     "e6932a0803b69071b64fc7c4a4ec8fa98c08112eec1e06f2c48a039c54ec5e20", 1),
    ("gemini-preflt", "gemini-da921x-w", 1),
    ("gemini-mt6797-da921x-preflight.boot.img",
     "gemini-mt6797-da921x-same-value-dt-repair.boot.img", 1),
    ("'CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y' \\\n",
     "'# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set' \\\n"
     "\t'CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y' \\\n"
     "\t'CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y' \\\n"
     "\t'CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y' \\\n"
     "\t'CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y' \\\n", 1),
    ("experiment=2026-08-17-mainline-da921x-same-value-write",
     "experiment=2026-08-20-mainline-da921x-same-value-dt-contract-repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe candidate derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
if ((status == 0)); then
	output_parent="$(cd -- "$output_parent" && pwd -P)"
	candidate="$output_parent/candidate-mainline-da921x-same-value-dt-repair-87b38fc4"
	[[ -d "$candidate" && ! -L "$candidate" ]] || die 'derived candidate is absent or unsafe'
	python3 - "$candidate/provenance.txt" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")
replacements = (
    ("DA921x_register_data_writes_expected=0\n",
     "DA921x_register_data_writes_expected=1-exact-0xda-0x46\n", 1),
    ("DA921x_runtime_operations=identity-reads,provider-reads,preflight-reads\n",
     "DA921x_runtime_operations=identity-reads,provider-reads,one-shot-same-value-write-with-readbacks\n", 1),
    ("I2C6_ledger_expected_entries=30\n",
     "I2C6_ledger_pretrigger_entries=20\nI2C6_ledger_posttrigger_entries=32\n", 1),
    ("dtb_delta_from-package=exact-proven-serviceability-group-only\n",
     "dtb_delta_from-rejected-same-value-candidate=restore-three-named-handoff-windows\n", 1),
    ("runtime_hypothesis=exact-I2C6-ledger-plus-stable-read-only-DA921x-preflight\n",
     "runtime_hypothesis=matching-three-window-handoff-contract-restores-DA921x-client-before-one-shot-token\n", 1),
    ("kernel_delta_from-proven-provider=read-only-I2C6-ledger-plus-preflight\n",
     "kernel_delta_from-rejected-same-value-candidate=none\n", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe provenance repair: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
path.write_text(text, encoding="ascii")
PY
	(
		cd "$candidate"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
	) >"$candidate/SHA256SUMS"
	(cd "$candidate" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
		die 'repaired candidate manifest failed'
	printf 'validation=mainline-da921x-same-value-dt-contract-repair-wrapper\n'
	printf 'artifact=%s\nDT_contract=three-named-windows\n' "$candidate"
	printf 'DA921x_register_data_writes_expected=1-exact-0xda-0x46\n'
	printf 'device_access=none\nhardware_write=none\nresult=pass\n'
fi
cleanup
trap - EXIT HUP INT TERM
exit "$status"
