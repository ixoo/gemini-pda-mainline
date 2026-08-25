#!/usr/bin/env bash

# Source-pin the preceding platform/provider assembler and retarget every exact
# package, DT, configuration, readiness marker, and candidate identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=087879839334c2f0a6221958f96d559b612c83683773807833b5061361467043
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-platform-provider-ready.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("2a936080d28cba12df241eb19a694fa1d559ee53", "db62ca343b1e0a1a0f6ead4a042d826a2554a6f2", 1),
    ("readonly PROFILE=a72-platform-provider-snapshot-candidate", "readonly PROFILE=a72-platform-provider-ready-candidate", 1),
    ("7.1.3-gemini-a72-provider-read", "7.1.3-gemini-a72-provider-ready", 1),
    ("661c6221e2e175781e7d6fccd280dc8154648a8d524c3019dfcdc398d9f4e4d4", "fcb64615beb07caa2aa871ead4e3ce09954626ebd696cc5ee5d47ce6ef168d39", 1),
    ("55007fac97d1f3075a3f66cb1410d03a56ff944463c82b251530946a9f705456", "83e807d0edd5315eb85eebd96b90df7b7a5388c57c3cc6aaf6fb185d46c81978", 1),
    ("ee8baf009bd3c94e59c91a4d4b6090e6280e4045b5a0ff8abdcd0c0ef2f6d1ac", "923575e4e25498f2749bb440af78372e36bb318bf5717d05ced18be600ebd6c8", 1),
    ("2838806a9b3004c9b7840adfe34ec2bb819be22f10af0c0d51f93b2725983faa", "529612b5f8978ba1b46ed75e326331d661a9b80e1121c149e93385aacb02e65e", 1),
    ("5071bd36c9cac884e123df20d87bda7087d8439fb7983bbcc1c233a14b56b486", "5f323a1631f2d10d9e021d1439b5dfe46bcb6421ec0b88bdc7c8b0e2225d0006", 1),
    ("ab3cdf901630b955e9b469b336c6741a4829daaf2f5160bce3ef42cd95364b5a", "8b12cb21e0b2514baa5b33b7f6be1ad40a91705b1072d616e9c8c5c84feb0fea", 1),
    ("9a63872070f145304de2ab79b64b47b1c1e5f3b2432fe9787a6df282722909de", "c0adf9a5c18e3870c83eb6c20571157f40b9fd7bf309502d2113a2f3c15f8ae9", 1),
    ("32059676f453e84e4c060294646224dfa988ed8ee2941c979578b10880c7e728", "041896e2ddd37b4fc42756a71d3e3a200fde73315f6425e6623f928c2c76bd0e", 1),
    ("ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e", 1),
    ("readonly RAW_SIZE=6912000", "readonly RAW_SIZE=6909952", 1),
    ("readonly BOOT_NAME=gemini-a72prov", "readonly BOOT_NAME=gemini-a72ready", 1),
    ("gemini-mt6797-a72-platform-provider-snapshot-second-read.boot.img", "gemini-mt6797-a72-platform-provider-ready.boot.img", 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-provider-read"', 'CONFIG_LOCALVERSION="-gemini-a72-provider-ready"', 1),
    (
        "GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 state=complete platform_calls=1 platform_samples=2",
        "GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1 state=complete provider_ready_gate=passed platform_calls=1 platform_samples=2",
        1,
    ),
    (".a72-platform-provider-snapshot-candidate.XXXXXXXX", ".a72-platform-provider-ready-candidate.XXXXXXXX", 1),
    ("portable-fetched-a72-platform-provider-snapshot-candidate", "portable-fetched-a72-platform-provider-ready-candidate", 1),
    ("experiment=2026-08-25-mainline-a72-platform-provider-snapshot-second-read", "experiment=2026-08-25-mainline-a72-platform-provider-deferred-bind-repair", 1),
    ("one-stable-provider-snapshot-after-passed-platform-snapshot", "one-stable-provider-snapshot-after-explicit-provider-ready-gate", 1),
    ("dtb_delta_from_passed_platform=replace-platform-observer-with-composed-observer", "dtb_delta_from_failed_provider_snapshot=provider-phandle-plus-observer-reference", 1),
    ("candidate-a72-platform-provider-snapshot-${RAW_SHA256:0:8}", "candidate-a72-platform-provider-ready-${RAW_SHA256:0:8}", 1),
    ("validation=a72-platform-provider-snapshot-candidate-build", "validation=a72-platform-provider-ready-candidate-build", 1),
    ("unsafe platform/provider builder derivation", "unsafe provider-ready builder derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe provider-ready wrapper: expected {count}, found {actual}: {old}"
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
