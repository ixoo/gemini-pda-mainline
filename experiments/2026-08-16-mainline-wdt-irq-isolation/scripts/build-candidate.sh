#!/usr/bin/env bash

# Source-pin and derive the validated assembler for watchdog IRQ isolation.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9ff4e2b0bc36af97bc5aa10f499fcdbf124849c67a3811484c44c03dbfd9202a

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-scp-handoff-node/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source candidate builder changed'

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
    ("one-node SCP repair", "one-property watchdog IRQ isolation", 1),
    ("932f0b987275539dcc0b9ea8126e3787ab2d4347d8d322221c83f9e3de41e0b8",
     "90de973cd5fa0d5f7625dd5eae8e3fd6a71817f568ae3775983869620b9775ea", 1),
    ("53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b",
     "49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa", 1),
    ("d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4",
     "21cd418951922852c0628d451e52d3a8df032c304e03037195738c41232676d2", 1),
    ("73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7",
     "b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d", 1),
    ("build-scp-handoff-dtb.sh", "build-wdt-noirq-dtb.sh", 1),
    ("candidate-mainline-scp-handoff-node-${RAW_SHA256:0:8}",
     "candidate-mainline-wdt-irq-isolation-${RAW_SHA256:0:8}", 1),
    ("mt6797-gemini-pda-scp-handoff.dtb",
     "mt6797-gemini-pda-wdt-noirq.dtb", 1),
    (".mainline-scp-handoff-node-wrapper.XXXXXXXX",
     ".mainline-wdt-irq-isolation-wrapper.XXXXXXXX", 1),
    ("# Assemble the exact GAEL kernel with the disabled SCP LK handoff node.",
     "# Assemble the exact GAEL kernel without the optional watchdog IRQ.", 1),
    ("readonly BOOT_NAME=gemini-scpnode", "readonly BOOT_NAME=gemini-wdtnoirq", 1),
    ("gemini-mt6797-arm64-entry-ledger-scp-handoff.boot.img",
     "gemini-mt6797-arm64-entry-ledger-wdt-noirq.boot.img", 1),
    ("SCP-handoff DTB", "watchdog-no-IRQ DTB", 1),
    (".mainline-scp-handoff-node.XXXXXXXX",
     ".mainline-wdt-irq-isolation.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-mainline-scp-handoff-node",
     "portable-fetched-kernel-package-with-watchdog-IRQ-isolation", 1),
    ("scp_handoff_dtb_sha256", "wdt_noirq_dtb_sha256", 1),
    ("scp_handoff_dtb_source=current-package-plus-three-status-properties-plus-disabled-SCP-node",
     "wdt_noirq_dtb_source=stopped-predecessor-minus-watchdog-interrupts", 1),
    ("experiment=2026-08-16-mainline-scp-handoff-node",
     "experiment=2026-08-16-mainline-wdt-irq-isolation", 1),
    ("runtime_hypothesis=disabled_SCP_node_satisfies_strict_LK_platform_atag_append",
     "runtime_hypothesis=no_watchdog_IRQ_reproduces_runtime_proven_early_takeover_path", 1),
    ("dtb_delta_from_stopped_usb_observation=one-disabled-SCP-node",
     "dtb_delta_from_stopped_scp_candidate=delete-watchdog-interrupts-only", 1),
    ("candidate-mainline-scp-handoff-node-",
     "candidate-mainline-wdt-irq-isolation-", 1),
    ("validation=mainline-scp-handoff-node-candidate-build",
     "validation=mainline-wdt-irq-isolation-candidate-build", 1),
    ("validation=mainline-scp-handoff-node-wrapper",
     "validation=mainline-wdt-irq-isolation-wrapper", 1),
    ("semantic_delta=three-USB-status-properties-plus-one-disabled-SCP-node",
     "semantic_delta=predecessor-minus-watchdog-interrupts-only", 1),
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
