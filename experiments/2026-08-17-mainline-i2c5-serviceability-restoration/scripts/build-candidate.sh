#!/usr/bin/env bash

# Source-pin and derive the validated assembler for the coherent I2C5 serviceability group.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1fd082009841fb10115c21c34df821b4a188c949c576db11b9a145f850a2c50f
readonly RAW_SHA256=e115127db5b4e2bbcf8e5fa12ebf5f8da88f8e87c76712605181160fa7b6917c

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --package DIR --ramdisk FILE --base-dtb FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
base_dtb=
output_parent=
while (($#)); do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$base_dtb" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk chmod dirname find mktemp python3 rm sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-wdt-irq-isolation/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source candidate builder changed'

output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

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
    ("one-property watchdog IRQ isolation",
     "coherent I2C5/AW9523 polling-keyboard serviceability restoration", 1),
    ("90de973cd5fa0d5f7625dd5eae8e3fd6a71817f568ae3775983869620b9775ea",
     "b63913108ab329915e505c6fbee54b6c85338dcb80252dbee9b9731142ee9503", 1),
    ("49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa",
     "a6b76ffc352e818d90709712a372c583ee275baf5f06ebf2cd11f593022b429c", 1),
    ("21cd418951922852c0628d451e52d3a8df032c304e03037195738c41232676d2",
     "e115127db5b4e2bbcf8e5fa12ebf5f8da88f8e87c76712605181160fa7b6917c", 1),
    ("b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d",
     "8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5", 1),
    ("build-wdt-noirq-dtb.sh", "build-serviceability-dtb.sh", 1),
    ("candidate-mainline-wdt-irq-isolation-${RAW_SHA256:0:8}",
     "candidate-mainline-i2c5-serviceability-${RAW_SHA256:0:8}", 1),
    ("mt6797-gemini-pda-wdt-noirq.dtb",
     "mt6797-gemini-pda-i2c5-serviceability.dtb", 1),
    (".mainline-wdt-irq-isolation-wrapper.XXXXXXXX",
     ".mainline-i2c5-serviceability-wrapper.XXXXXXXX", 1),
    ("# Assemble the exact GAEL kernel without the optional watchdog IRQ.",
     "# Assemble the exact GAEL kernel with the I2C5/AW9523 polling-keyboard group.", 1),
    ("readonly BOOT_NAME=gemini-wdtnoirq", "readonly BOOT_NAME=gemini-i2c5svc", 1),
    ("gemini-mt6797-arm64-entry-ledger-wdt-noirq.boot.img",
     "gemini-mt6797-arm64-entry-ledger-i2c5-serviceability.boot.img", 1),
    ("watchdog-no-IRQ DTB", "I2C5 serviceability DTB", 1),
    (".mainline-wdt-irq-isolation.XXXXXXXX",
     ".mainline-i2c5-serviceability.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-watchdog-IRQ-isolation",
     "portable-fetched-kernel-package-with-I2C5-serviceability-restoration", 1),
    ("wdt_noirq_dtb_sha256", "i2c5_serviceability_dtb_sha256", 1),
    ("wdt_noirq_dtb_source=stopped-predecessor-minus-watchdog-interrupts",
     "i2c5_serviceability_dtb_source=stopped-predecessor-plus-positive-control-serviceability-group", 1),
    ("experiment=2026-08-16-mainline-wdt-irq-isolation",
     "experiment=2026-08-17-mainline-i2c5-serviceability-restoration", 1),
    ("runtime_hypothesis=no_watchdog_IRQ_reproduces_runtime_proven_early_takeover_path",
     "runtime_hypothesis=exact_I2C5_AW9523_polling_keyboard_group_restores_serviceability", 1),
    ("dtb_delta_from_stopped_scp_candidate=delete-watchdog-interrupts-only",
     "dtb_delta_from_stopped_wdt_candidate=exact-positive-control-I2C5-serviceability-group", 1),
    ("candidate-mainline-wdt-irq-isolation-",
     "candidate-mainline-i2c5-serviceability-", 1),
    ("validation=mainline-wdt-irq-isolation-candidate-build",
     "validation=mainline-i2c5-serviceability-candidate-build", 1),
    ("validation=mainline-wdt-irq-isolation-wrapper",
     "validation=mainline-i2c5-serviceability-wrapper", 1),
    ("semantic_delta=predecessor-minus-watchdog-interrupts-only",
     "semantic_delta=exact-I2C5-AW9523-polling-keyboard-positive-control-group", 1),
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
/bin/bash "$derived" --package "$package" --ramdisk "$ramdisk" \
	--base-dtb "$base_dtb" --output-parent "$output_parent"
status=$?
set -e
((status == 0)) || exit "$status"

candidate="$output_parent/candidate-mainline-i2c5-serviceability-${RAW_SHA256:0:8}"
[[ -d "$candidate" && ! -L "$candidate" ]] || die 'derived candidate is absent or unsafe'
python3 - "$candidate/provenance.txt" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")
replacements = (
    ("register_data_writes_expected=0",
     "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only", 1),
    ("hardware_write=none",
     "hardware_write=AW9523-serviceability-probe-and-keyboard-only", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe provenance correction: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
path.write_text(text, encoding="ascii")
PY
(
	cd "$candidate"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$candidate/SHA256SUMS"
(cd "$candidate" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'corrected candidate manifest failed'

cleanup
trap - EXIT HUP INT TERM
printf 'validation=mainline-i2c5-serviceability-provenance-wrapper\n'
printf 'artifact=%s\ncandidate_sha256=%s\n' "$candidate" "$RAW_SHA256"
printf 'runtime_hardware_write=AW9523-serviceability-probe-and-keyboard-only\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
