#!/usr/bin/env bash

# Source-pin and mechanically derive the exact post-ramoops checkpoint
# candidate builder from the reviewed module-policy control builder.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1159b305a37fce60e94e8fdcb1080198e3db3b8ea9262013d4e48198d4a0cb89

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-15-mainline-module-policy-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

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
    ("# Source-pin and mechanically derive the exact module-policy serviceability\n# control builder",
     "# Source-pin and mechanically derive the exact post-ramoops checkpoint\n# candidate builder", 1),
    ("09ba93dbe1aa462795f1a1f4f0e82e31f5392989",
     "cac458c1cbd228390b94f2ae7154db34160adac2", 1),
    ("da921x-resource-only-provider-modules-control",
     "da921x-modules-post-ramoops-checkpoint", 1),
    ("7.1.3-gemini-da921x-modctl", "7.1.3-gemini-postram-a", 1),
    ("ca9d18d721916efa994a8e5623adc52f08a105b3676ada960077236f78e101df",
     "3fa0d577fc953544b8dcd3a76720c18973ec6942120bdaf441d238d486ae4d6c", 1),
    ("86cdcb5bec92aa8cd6d292e27f44df06e3cca78305862bbb5026b6c094174b7e",
     "89ebdafc9c7360900d341787dc9f63884b51ecfc2919563b7f058f471723ccd6", 1),
    ("f65d2cf39070e8ba0427e8745bd8aa615869abf048698a18251c6c07a69d26b2",
     "be742f54afc6a3ac3f1622589c98d68f3904cd8f0b8191236d1da1017413b112", 1),
    ("7093fe54510224c1c4cbf83562a8d6650f6ac0b03fa71a2da19c81f7b3846b34",
     "bbb63ccfd6486483dedfd5190a4db666eb1202bd22fa1a0ef2da8b4f383a5ad9", 1),
    ("bdd3bd798f2edc5f0936d3a05bf21c58a24b1fa6f424e62c47c34a1decf4cacf",
     "ccbc30998640777f99f296cb5ee57ca9e391b566e04cdec3a98e3b19d7d64a3c", 1),
    ("706aa2b12941d2b65fee3a8f34955e001bffc4917a95572bd93540172f87fe4a",
     "8861f3930f1c406c6f9e1444f7a0e438c489ffcf500e8f32a0cf42176ea2897e", 1),
    ("782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040",
     "e16405f0a9061e98898f7fac5312033d56b1ab2aec162673fbebac564672e788", 1),
    ("044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff",
     "ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348", 1),
    ("gemini-modctl", "gemini-postram", 1),
    ("gemini-mt6797-da921x-module-policy-control.boot.img",
     "gemini-mt6797-post-ramoops-checkpoint.boot.img", 1),
    (".da921x-module-policy-control.XXXXXXXX", ".post-ramoops-checkpoint.XXXXXXXX", 1),
    ("experiment=2026-08-15-mainline-module-policy-control",
     "experiment=2026-08-15-mainline-post-ramoops-checkpoint", 1),
    ("runtime_hypothesis=module-policy-restoration-recovers-serviceability",
     "runtime_hypothesis=retain-marker-after-successful-ramoops-registration", 1),
    ("candidate-da921x-module-policy-control-${RAW_SHA256:0:8}",
     "candidate-post-ramoops-checkpoint-${RAW_SHA256:0:8}", 1),
    ("validation=da921x-module-policy-control-candidate-build",
     "validation=post-ramoops-checkpoint-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe builder derivation: expected {count} occurrences, found {actual}: {old}"
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
