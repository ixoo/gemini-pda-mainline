#!/usr/bin/env bash

# Source-pin the guarded P30E installer and retarget only its exact
# READY-identity successor, immediate predecessor, manifest, and labels.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0e24b9827bb66b2ad527fa79de2354f68a321f6840fa0644548d9aee56661466
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-p30e-ready-identity-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),',
        '("e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),',
        1,
    ),
    ("28b5e3eff190e5299da9594cd3ac5de8ad48b0787fc1c913195e74375a88c3e1", "c98b9e676236d59339ff7939f8cd723310c04474ffda924296f07879177f90e2", 1),
    (
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743", 1),',
        '("a7ce2c2d58bccce6c1f41814d0ae584b808555791397fb50088117058111a179", "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453", 1),',
        1,
    ),
    ("candidate-a72-p30e-entry-diagnostic-b80dfc49", "candidate-a72-p30e-ready-identity-repair-417d911f", 1),
    ("experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic", "experiment=2026-08-31-mainline-a72-p30e-ready-identity-repair", 1),
    ('("a72-isolation-held-result-contract-repair", "a72-p30e-entry-diagnostic", 1),', '("a72-isolation-held-result-contract-repair", "a72-p30e-ready-identity-repair", 1),', 1),
    (".derived-install-a72-p30e-entry-diagnostic-inner.XXXXXXXX", ".derived-install-a72-p30e-ready-identity-repair-inner.XXXXXXXX", 1),
    ("P30E entry-publication diagnostic candidate", "P30E READY-identity repair candidate", 1),
    ("P30E entry installer derivation", "P30E READY-identity installer derivation", 3),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
