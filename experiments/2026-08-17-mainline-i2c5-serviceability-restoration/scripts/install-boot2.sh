#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# coherent I2C5/AW9523 polling-keyboard serviceability candidate. The inherited
# policy resolves live GPT boot2, records but does not back up the predecessor,
# verifies a full readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=eeff61412d1096644adb69a53ddff293dd8bc69cd096f8f2423f81a55a7552f0

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-16-mainline-wdt-irq-isolation/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("one-property watchdog IRQ isolation candidate",
     "coherent I2C5/AW9523 polling-keyboard serviceability candidate", 2),
    ("b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d",
     "8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5", 1),
    ("5437f1cddf2407e9b38f4ddc4ef55f2bf17ba66ad4f1d3d36ba74f33e52ed212",
     "9a05fd5ea6266d04595307575425e296b476dc2cfdf478a87ca402b4108ed143", 1),
    ("candidate-mainline-wdt-irq-isolation-21cd4189",
     "candidate-mainline-i2c5-serviceability-e115127d", 1),
    ("mainline-wdt-irq-isolation-deployment-",
     "mainline-i2c5-serviceability-deployment-", 1),
    (r"\.gemini-mainline-wdt-irq-isolation\.",
     r"\.gemini-mainline-i2c5-serviceability\.", 1),
    ("/home/gemini/.gemini-mainline-wdt-irq-isolation.XXXXXXXX",
     "/home/gemini/.gemini-mainline-i2c5-serviceability.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-wdt-irq-isolation",
     "experiment=2026-08-17-mainline-i2c5-serviceability-restoration", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
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
