#!/usr/bin/env bash

# Source-pin and derive the validated assembler for the one-node SCP repair.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0397e351c933c665903c82e4c1e3de01d5e86980b055064a08279658749957f6

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-current-dtb-usb-observation/scripts/build-candidate.sh"
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
    ("# Reuse the exact validated GAEL assembler with a three-property USB DT.",
     "# Reuse the exact GAEL assembler with the disabled SCP LK handoff node.", 1),
    ("dbf8a99fc99f2f7cbd256495bb3d295b2c5bed9b627a9c60a338cfa518303efb",
     "932f0b987275539dcc0b9ea8126e3787ab2d4347d8d322221c83f9e3de41e0b8", 1),
    ("e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331",
     "53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b", 2),
    ("a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be",
     "d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4", 2),
    ("fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87",
     "73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7", 1),
    ("build-usb-observation-dtb.sh", "build-scp-handoff-dtb.sh", 1),
    ("candidate-current-dtb-usb-observation-${RAW_SHA256:0:8}",
     "candidate-mainline-scp-handoff-node-${RAW_SHA256:0:8}", 1),
    ("mt6797-gemini-pda-usb-observation.dtb",
     "mt6797-gemini-pda-scp-handoff.dtb", 1),
    (".current-dtb-usb-observation-wrapper.XXXXXXXX",
     ".mainline-scp-handoff-node-wrapper.XXXXXXXX", 1),
    ("# Assemble the exact GAEL kernel with the minimal current-DT USB observation path.",
     "# Assemble the exact GAEL kernel with the disabled SCP LK handoff node.", 1),
    ("readonly BOOT_NAME=gemini-usbobs", "readonly BOOT_NAME=gemini-scpnode", 1),
    ("gemini-mt6797-arm64-entry-ledger-usb-observation.boot.img",
     "gemini-mt6797-arm64-entry-ledger-scp-handoff.boot.img", 1),
    ("USB-observation DTB", "SCP-handoff DTB", 1),
    (".current-dtb-usb-observation.XXXXXXXX",
     ".mainline-scp-handoff-node.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-current-dtb-usb-observation",
     "portable-fetched-kernel-package-with-mainline-scp-handoff-node", 1),
    ("usb_observation_dtb_sha256", "scp_handoff_dtb_sha256", 1),
    ("usb_observation_dtb_source=current-package-plus-three-status-properties",
     "scp_handoff_dtb_source=current-package-plus-three-status-properties-plus-disabled-SCP-node", 1),
    ("experiment=2026-08-16-mainline-current-dtb-usb-observation",
     "experiment=2026-08-16-mainline-scp-handoff-node", 1),
    ("runtime_hypothesis=three_status_properties_restore_live_usb_oracle_to_current_dtb",
     "runtime_hypothesis=disabled_SCP_node_satisfies_strict_LK_platform_atag_append", 1),
    ("dtb_delta_from_stopped_gael=three-usb-status-properties-only",
     "dtb_delta_from_stopped_usb_observation=one-disabled-SCP-node", 1),
    ("candidate-current-dtb-usb-observation-",
     "candidate-mainline-scp-handoff-node-", 1),
    ("validation=current-dtb-usb-observation-candidate-build",
     "validation=mainline-scp-handoff-node-candidate-build", 1),
    ("validation=current-dtb-usb-observation-wrapper",
     "validation=mainline-scp-handoff-node-wrapper", 1),
    ("semantic_delta_count=3",
     "semantic_delta=three-USB-status-properties-plus-one-disabled-SCP-node", 1),
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
