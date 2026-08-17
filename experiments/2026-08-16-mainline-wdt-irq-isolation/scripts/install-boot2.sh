#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded installer for the exact
# one-property watchdog IRQ isolation candidate. The inherited policy resolves
# live GPT boot2, records but does not back up the predecessor, verifies a full
# readback, and powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2119cbbbf94ebc1b6cf9ecb24273c8240897b4494ace3c5f89f9087cbcb530eb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-16-mainline-scp-handoff-node/scripts/install-boot2.sh"
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
    ("disabled-SCP-node LK handoff candidate",
     "one-property watchdog IRQ isolation candidate", 2),
    ("73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7",
     "b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d", 1),
    ("2bc9c53da18bb0e0276d7d86eb617d8e96a6259f01a556ed47d1883ee72f657a",
     "5437f1cddf2407e9b38f4ddc4ef55f2bf17ba66ad4f1d3d36ba74f33e52ed212", 1),
    ("candidate-mainline-scp-handoff-node-d13f110a",
     "candidate-mainline-wdt-irq-isolation-21cd4189", 1),
    ("mainline-scp-handoff-node-deployment-",
     "mainline-wdt-irq-isolation-deployment-", 1),
    (r"\.gemini-mainline-scp-handoff-node\.",
     r"\.gemini-mainline-wdt-irq-isolation\.", 1),
    ("/home/gemini/.gemini-mainline-scp-handoff-node.XXXXXXXX",
     "/home/gemini/.gemini-mainline-wdt-irq-isolation.XXXXXXXX", 1),
    ("experiment=2026-08-16-mainline-scp-handoff-node",
     "experiment=2026-08-16-mainline-wdt-irq-isolation", 1),
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
