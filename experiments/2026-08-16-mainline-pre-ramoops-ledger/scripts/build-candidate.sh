#!/usr/bin/env bash

# Source-pin and mechanically derive the exact pre-ramoops ledger candidate
# builder from the reviewed module-policy control builder.
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
     "# Source-pin and mechanically derive the exact pre-ramoops ledger\n# candidate builder", 1),
    ("09ba93dbe1aa462795f1a1f4f0e82e31f5392989",
     "ca56f0161f6d67900d0fc58719e9190e7d1bb4a3", 1),
    ("da921x-resource-only-provider-modules-control",
     "da921x-modules-pre-ramoops-ledger", 1),
    ("7.1.3-gemini-da921x-modctl", "7.1.3-gemini-preledger-a", 1),
    ("ca9d18d721916efa994a8e5623adc52f08a105b3676ada960077236f78e101df",
     "8fbd12d6494c72882daa6b4d49fe2596e38796561b83a6252133c8587c89db5c", 1),
    ("86cdcb5bec92aa8cd6d292e27f44df06e3cca78305862bbb5026b6c094174b7e",
     "c68da1d645c750f9d60c4ab067e70bf8da276273d60eca78b72b06e7b70741e4", 1),
    ("f65d2cf39070e8ba0427e8745bd8aa615869abf048698a18251c6c07a69d26b2",
     "9f93f48aec1e215b07d89d38d8e4a653b041a46a0df939d542cc11e7e65efbca", 1),
    ("7093fe54510224c1c4cbf83562a8d6650f6ac0b03fa71a2da19c81f7b3846b34",
     "9832806c73e8ae2b10f139bdac9bb4e11722df76bea216c2e49422ff496f4f7c", 1),
    ("bdd3bd798f2edc5f0936d3a05bf21c58a24b1fa6f424e62c47c34a1decf4cacf",
     "49b9c33a0dbb619e978b59bea22bfb89b2b884e4843d9236484a7f8520871812", 1),
    ("706aa2b12941d2b65fee3a8f34955e001bffc4917a95572bd93540172f87fe4a",
     "c3fe6adb07c6ca5e93187a00fb141391a1516e2f4673bffccd20a61958e07808", 1),
    ("782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040",
     "00455398cf1ffa3f57ad5083322e5541b0a58dbdec9ff63883b1427990cff8c3", 1),
    ("044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff",
     "ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f", 1),
    ('\\"readonly RAW_SIZE=6881280\\"', '\\"readonly RAW_SIZE=6877184\\"', 1),
    ("gemini-modctl", "gemini-preledg", 1),
    ("gemini-mt6797-da921x-module-policy-control.boot.img",
     "gemini-mt6797-pre-ramoops-ledger.boot.img", 1),
    (".da921x-module-policy-control.XXXXXXXX", ".pre-ramoops-ledger.XXXXXXXX", 1),
    ("experiment=2026-08-15-mainline-module-policy-control",
     "experiment=2026-08-16-mainline-pre-ramoops-ledger", 1),
    ("runtime_hypothesis=module-policy-restoration-recovers-serviceability",
     "runtime_hypothesis=four-stage-pre-ramoops-ledger-localization", 1),
    ("candidate-da921x-module-policy-control-${RAW_SHA256:0:8}",
     "candidate-pre-ramoops-ledger-${RAW_SHA256:0:8}", 1),
    ("validation=da921x-module-policy-control-candidate-build",
     "validation=pre-ramoops-ledger-candidate-build", 1),
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
