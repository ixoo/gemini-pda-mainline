#!/usr/bin/env bash

# Source-pin the movement-attribution validator and retarget its exact package,
# layout, status-mask result, and candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3235254e03d3eff1e27b125c8e3f6a73a67fab848669669be96bad572d9fbf64
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-26-mainline-a72-platform-movement-attribution/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-cpu-status-mask.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1ad025c40cb6716cb5a110319b715cc03f812551", "8b087b98fcc4e2a03d82d89bee26c99818a81836", 1),
    ("a72-platform-movement-candidate", "a72-cpu-status-mask-candidate", 1),
    ("7.1.3-gemini-a72-movement", "7.1.3-gemini-a72-cpumask", 1),
    ("d1e244b4b3d757b6ee20d3ef0c2719a8f6cfc8f627b6381993ed7b702b26fb27", "84096d9dc21e3393ee427c7550ecd19d104000fc6ba982bd4ab23bdd97a8bfd5", 1),
    ("5413eace14655c31ef3355a769ec36986e7e458309d4fe5d374c4923b66b6814", "c3549526dd77bd150770fcf4f1ba415c4c55ba353aeeec369c5536bb4f6df000", 1),
    ("f0c86eeea98b478930745c5957cdff81cab05deec9710262b677936ec452736c", "e2deb1f5495f71dbb8afd2e7ad5bee1f2af7c2a17a517aff19a9547305e6dc77", 1),
    ("6c7d9359b3a262ebcd928f2bd76543713102e37fcb55df9c590e60598ecc29ee", "668531f77d7580a24148afa58192adf839fef42fec6df1a26c84e49c9437894f", 1),
    ("e96a221ec55b032f5fd8442b8b3bc6ee7669040f56b5016d14bddac691502e73", "97026023b245a2f5e7071a329c5b1a95ca393ba6ffbf46ad3f98e945f25fa67d", 1),
    ("fd070a56d1f247108935298ab1be61938987cab912b84fd64624e8a26a7a6d99", "ebaddc69660a824de4ff0f2f59eafb9073a7b100ae3f737caf0f9b50f59cf98a", 1),
    ("9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", 1),
    ("4_834_030", "4_834_045", 1),
    ("-gemini-a72-movement", "-gemini-a72-cpumask", 1),
    ("gemini-mt6797-a72-platform-movement.boot.img", "gemini-mt6797-a72-cpu-status-mask.boot.img", 1),
    ("control_dtb=byte-identical-retired-failure-stage-dtb", "control_dtb=byte-identical-movement-attribution-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-status-mask validator derivation: expected {count}, found {actual}: {old}"
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
