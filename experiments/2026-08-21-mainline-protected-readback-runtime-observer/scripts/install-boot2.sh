#!/usr/bin/env bash

# Source-pin and derive the guarded installer for the exact protected-readback
# observer candidate, adding the mandatory live tee1/tee2 identity gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
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
    (
        "# Install the exact validated provenance-observer container to inactive boot2.",
        "# Install the exact validated protected-readback observer container to inactive boot2.",
        1,
    ),
    (
        "ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02",
        "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        1,
    ),
    (
        "ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a",
        "f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a",
        1,
    ),
    (
        "gemian-runtime-provenance-observer-rndis-1d303dda10b4",
        "candidate-protected-readback-ro-a3cb0e1c",
        1,
    ),
    ("provenance-observer-deployment-", "protected-readback-deployment-", 3),
    (r"\.gemini-provenance-observer\.", r"\.gemini-protected-readback\.", 2),
    (
        "/home/gemini/.gemini-provenance-observer.XXXXXXXX",
        "/home/gemini/.gemini-protected-readback.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-14-mt6797-runtime-provenance-observer",
        "experiment=2026-08-21-mainline-protected-readback-runtime-observer",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)

insertions = (
    (
        "readonly ARTIFACT_NAME=candidate-protected-readback-ro-a3cb0e1c\n",
        "readonly ARTIFACT_NAME=candidate-protected-readback-ro-a3cb0e1c\n"
        "readonly EXPECTED_TEE_SHA256=2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3\n",
        1,
    ),
    (
        "EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_STAGE='$expected_stage' /bin/bash -s",
        "EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_STAGE='$expected_stage' "
        "EXPECTED_TEE_SHA256='$EXPECTED_TEE_SHA256' /bin/bash -s",
        1,
    ),
    (
        "[[ \"$(cat /proc/sys/kernel/random/boot_id)\" == \"$EXPECTED_BOOT_ID\" ]] || fail 'boot ID changed'\n\n"
        "rows=\"$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == \"boot2\" {print}')\"",
        "[[ \"$(cat /proc/sys/kernel/random/boot_id)\" == \"$EXPECTED_BOOT_ID\" ]] || fail 'boot ID changed'\n\n"
        "resolve_tee() {\n"
        "\tlocal wanted=$1 rows target label type size ro mountpoint extra\n"
        "\trows=\"$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | "
        "awk -v wanted=\"$wanted\" '$2 == wanted {print}')\"\n"
        "\t[[ \"$(printf '%s\\n' \"$rows\" | awk 'NF {n++} END {print n+0}')\" == 1 ]] ||\n"
        "\t\tfail \"live GPT does not have exactly one $wanted row\"\n"
        "\tread -r target label type size ro mountpoint extra <<<\"$rows\"\n"
        "\t[[ \"$target\" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && \"$label\" == \"$wanted\" &&\n"
        "\t\t\"$type\" == part && \"$size\" =~ ^[1-9][0-9]*$ && \"$ro\" =~ ^[01]$ ]] ||\n"
        "\t\tfail \"$wanted identity changed\"\n"
        "\t[[ -z \"${mountpoint:-}\" && -z \"${extra:-}\" && -b \"$target\" ]] ||\n"
        "\t\tfail \"$wanted is mounted or invalid\"\n"
        "\t[[ \"$(readlink -f \"/dev/disk/by-partlabel/$wanted\")\" == \"$target\" ]] ||\n"
        "\t\tfail \"$wanted by-partlabel disagrees with GPT\"\n"
        "\t[[ \"$(lsblk -dnro PKNAME \"$target\")\" == mmcblk0 ]] ||\n"
        "\t\tfail \"$wanted parent changed\"\n"
        "\tprintf '%s\\n' \"$target\"\n"
        "}\n"
        "tee1_target=\"$(resolve_tee tee1)\"\n"
        "tee2_target=\"$(resolve_tee tee2)\"\n"
        "[[ \"$tee1_target\" != \"$tee2_target\" ]] || fail 'TEE targets alias'\n"
        "tee1_sha256=\"$(sha256sum \"$tee1_target\" | awk '{print $1}')\"\n"
        "tee2_sha256=\"$(sha256sum \"$tee2_target\" | awk '{print $1}')\"\n"
        "[[ \"$tee1_sha256\" == \"$EXPECTED_TEE_SHA256\" &&\n"
        "\t\"$tee2_sha256\" == \"$EXPECTED_TEE_SHA256\" ]] ||\n"
        "\tfail 'live tee1/tee2 identities do not match the audited payload'\n\n"
        "rows=\"$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == \"boot2\" {print}')\"",
        1,
    ),
    (
        "printf 'gate=passed\\nmode=%s\\ntarget=%s\\nroot=%s\\n' \"$GATE_MODE\" \"$target\" \"$root\"\n",
        "printf 'gate=passed\\nmode=%s\\ntarget=%s\\nroot=%s\\n' \"$GATE_MODE\" \"$target\" \"$root\"\n"
        "printf 'tee1_target=%s\\ntee1_sha256=%s\\ntee2_target=%s\\ntee2_sha256=%s\\n' "
        "\"$tee1_target\" \"$tee1_sha256\" \"$tee2_target\" \"$tee2_sha256\"\n",
        1,
    ),
    (
        "power=\"$(single_value power \"$probe_output\")\" || die 'invalid power evidence'\n",
        "power=\"$(single_value power \"$probe_output\")\" || die 'invalid power evidence'\n"
        "tee1_sha256=\"$(single_value tee1_sha256 \"$probe_output\")\" || die 'invalid tee1 evidence'\n"
        "tee2_sha256=\"$(single_value tee2_sha256 \"$probe_output\")\" || die 'invalid tee2 evidence'\n"
        "[[ \"$tee1_sha256\" == \"$EXPECTED_TEE_SHA256\" &&\n"
        "\t\"$tee2_sha256\" == \"$EXPECTED_TEE_SHA256\" ]] || die 'TEE evidence changed'\n",
        1,
    ),
    (
        "printf 'candidate_sha256=%s\\nreadback_sha256=%s\\n' \"$CANDIDATE_SHA256\" \"$readback_sha256\"\n",
        "printf 'candidate_sha256=%s\\nreadback_sha256=%s\\n' \"$CANDIDATE_SHA256\" \"$readback_sha256\"\n"
        "\tprintf 'tee1_sha256=%s\\ntee2_sha256=%s\\n' \"$tee1_sha256\" \"$tee2_sha256\"\n",
        1,
    ),
)
for old, new, count in insertions:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer insertion: expected {count} occurrences, found {actual}: {old}"
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
