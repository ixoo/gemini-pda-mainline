#!/usr/bin/env bash

# Source-pin and derive the pre-armed observer for the one SCP handoff-node
# attempt. It adds a sanitized exact USB topology journal so a short device
# transition is not represented only by a topology hash.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=94f77f6b4f10eb695593f95bd7b1dd3b95595b14287ca5e1f0ceaa107103a798

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-16-mainline-current-dtb-usb-observation/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
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
    ("one current-DT repair attempt", "one SCP handoff-node repair attempt", 1),
    ("39c18b20-1b73-474a-835e-c99e1e6adc45",
     "2df0e486-4d13-44f9-a1ec-94f90726a612", 1),
    ("fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87",
     "73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7", 1),
    ("current-dtb-usb-observation-attempt-1",
     "mainline-scp-handoff-node-attempt-1", 2),
    (".gemini-usb-observation.XXXXXXXX",
     ".gemini-scp-handoff-observation.XXXXXXXX", 1),
    ("no-mainline-network-before-changed-Gemian-return",
     "no-mainline-network-after-SCP-node-before-changed-Gemian-return", 2),
    ("exact-current-kernel-serviceable-with-three-property-DT",
     "exact-current-kernel-serviceable-with-disabled-SCP-node", 2),
    (
        'service="$output/service.txt"\n'
        'printf \'observer=armed\\ncandidate_sha256=%s\\n\' "$CANDIDATE_SHA256" >"$events"',
        'service="$output/service.txt"\n'
        'usb_topology="$output/usb-topology.txt"\n'
        'printf \'observer=armed\\ncandidate_sha256=%s\\n\' "$CANDIDATE_SHA256" >"$events"',
        1,
    ),
    (
        'baseline_usb="$(ioreg -p IOUSB -l -w 0 |\n'
        '\tawk \'/"idVendor"|"idProduct"|"USB Product Name"/\' |\n'
        '\tsha256sum | awk \'{print $1}\')"\n'
        'printf \'baseline_usb_topology_sha256=%s\\n\' "$baseline_usb" >>"$events"',
        'baseline_snapshot="$(ioreg -p IOUSB -l -w 0 |\n'
        '\tawk \'/"idVendor"|"idProduct"|"USB Product Name"/\')"\n'
        'baseline_usb="$(printf \'%s\\n\' "$baseline_snapshot" | sha256sum | awk \'{print $1}\')"\n'
        '{\n'
        '\tprintf \'snapshot=baseline utc=%s sha256=%s\\n\' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$baseline_usb"\n'
        '\tprintf \'%s\\n\' "$baseline_snapshot"\n'
        '} >"$usb_topology"\n'
        'printf \'baseline_usb_topology_sha256=%s\\n\' "$baseline_usb" >>"$events"',
        1,
    ),
    (
        '\tcurrent_usb="$(ioreg -p IOUSB -l -w 0 |\n'
        '\t\tawk \'/"idVendor"|"idProduct"|"USB Product Name"/\' |\n'
        '\t\tsha256sum | awk \'{print $1}\')"\n'
        '\tif [[ "$current_usb" != "$last_usb" ]]; then\n'
        '\t\tprintf \'usb_topology_change_utc=%s sha256=%s\\n\' \\\n'
        '\t\t\t"$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$current_usb" >>"$events"\n'
        '\t\tlast_usb=$current_usb\n'
        '\tfi',
        '\tcurrent_snapshot="$(ioreg -p IOUSB -l -w 0 |\n'
        '\t\tawk \'/"idVendor"|"idProduct"|"USB Product Name"/\')"\n'
        '\tcurrent_usb="$(printf \'%s\\n\' "$current_snapshot" | sha256sum | awk \'{print $1}\')"\n'
        '\tif [[ "$current_usb" != "$last_usb" ]]; then\n'
        '\t\tchange_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"\n'
        '\t\tprintf \'usb_topology_change_utc=%s sha256=%s\\n\' \\\n'
        '\t\t\t"$change_utc" "$current_usb" >>"$events"\n'
        '\t\t{\n'
        '\t\t\tprintf \'snapshot=change utc=%s sha256=%s\\n\' "$change_utc" "$current_usb"\n'
        '\t\t\tprintf \'%s\\n\' "$current_snapshot"\n'
        '\t\t} >>"$usb_topology"\n'
        '\t\tlast_usb=$current_usb\n'
        '\tfi',
        1,
    ),
    ("sha256sum observer-events.txt >SHA256SUMS",
     "sha256sum observer-events.txt usb-topology.txt >SHA256SUMS", 2),
    ("sha256sum observer-events.txt runtime.txt service.txt >SHA256SUMS",
     "sha256sum observer-events.txt usb-topology.txt runtime.txt service.txt >SHA256SUMS", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe collector derivation: expected {count} occurrences, found {actual}: {old}"
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
