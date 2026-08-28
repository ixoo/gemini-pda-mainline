#!/usr/bin/env bash

# Source-pin the proven USB/netcat collector and retarget it to the exact CPU8
# admission probe and its three decision-changing serviceable classifications.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0a4cf2cf6f21e588a8b393247f2dae3876e071ab471fe4892095f30c68284305
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-early-live-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-admission.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("Pre-arm one bounded USB/netcat observation of the exact live DT control.",
     "Pre-arm one bounded USB/netcat observation of exact CPU8 admission.", 1),
    ("070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef",
     "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0", 1),
    ("29aabf7219a476e352fa43b7988258d17aa941b87cbcac797a3963e3da28909f",
     "7b99beca6b9228efa632065de93d9fd8337867733584ae697e9bcccac8432cfc", 1),
    ("6fb2c2f7773c49d44d1cc9aa20402823d7f30c9bfd240bb204eb93f909f353fb",
     "0f8c174ef9b20cb56325eebf1e2cd8c6309cdab52aedcdce5add9de156bd0906", 1),
    ("a72-early-live-control-attempt-1", "a72-admission-attempt-1", 2),
    (".gemini-a72-early-live.", ".gemini-a72-admission-live.", 1),
    ("__A72_EARLY_LIVE_CONTROL_BEGIN__", "__A72_ADMISSION_RUNTIME_BEGIN__", 1),
    ("__A72_EARLY_LIVE_CONTROL_END__", "__A72_ADMISSION_RUNTIME_END__", 1),
    (
        "grep -Fqx 'runtime_classification=serviceable-stage27-control-pass' \"$classification\" ||\n"
        "\tdie 'runtime did not classify as the exact Stage-27 control pass'",
        "grep -Eq '^runtime_classification=serviceable-(cpu8-online-proof|pre-request-rejection|cpu8-transition-failure)$' \"$classification\" ||\n"
        "\tdie 'runtime did not classify as an exact CPU8 admission decision'",
        1,
    ),
    (
        "printf 'runtime_classification=serviceable-stage27-control-pass\\n'\n",
        "awk -F= '$1 == \"runtime_classification\" {print; count++} END {exit count != 1}' \"$classification\"\n",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU8 admission collector derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
