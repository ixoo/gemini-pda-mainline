#!/usr/bin/env bash

# Source-pin the live-GPT/TEE installer, retarget it to the exact P30E
# READY-identity candidate, and require its exact immediate boot2 predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7f5bddb91bf38fb5de9cce5bde5c1aa7bac4a114a7619d25f49621fb715b912d
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_PREDECESSOR_SHA256=a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453
readonly CANDIDATE_SHA256=459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/install-boot2.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'Gemini SSH identity is absent or unsafe'

derived=$(mktemp "$script_dir/.derived-install-a72-p30e-ready-identity-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a", "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a", "c98b9e676236d59339ff7939f8cd723310c04474ffda924296f07879177f90e2", 1),
    ("candidate-protected-readback-ro-a3cb0e1c", "candidate-a72-p30e-ready-identity-repair-417d911f", 3),
    ("protected-readback-deployment-", "a72-p30e-ready-identity-repair-deployment-", 1),
    ("gemini-protected-readback", "gemini-a72-p30e-ready-identity-repair", 2),
    ("experiment=2026-08-21-mainline-protected-readback-runtime-observer", "experiment=2026-08-31-mainline-a72-p30e-ready-identity-repair", 1),
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

help_only=no
target=
arguments=("$@")
while (($#)); do
	case "$1" in
	-h|--help) help_only=yes; shift ;;
	--target) (($# >= 2)) || die '--target requires a value'; target=$2; shift 2 ;;
	*) shift ;;
	esac
done
if [[ "$help_only" == yes ]]; then
	/bin/bash "$derived" "${arguments[@]}"
	exit $?
fi
[[ "$target" == "$EXPECTED_TARGET" ]] || die 'exact Gemini target is required'

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity"
)
predecessor=$("${ssh_command[@]}" "$target" 'sudo -n /bin/bash -s' <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] || fail 'live GPT boot2 count changed'
read -r boot2 label type size ro mountpoint extra <<<"$rows"
[[ "$boot2" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && "$label" == boot2 &&
	"$type" == part && "$size" == 16777216 && "$ro" == 0 &&
	-z "${mountpoint:-}" && -z "${extra:-}" && -b "$boot2" ]] ||
	fail 'boot2 live GPT identity changed or is mounted'
root=$(readlink -f "$(findmnt -n -o SOURCE /)")
[[ "$root" == /dev/mmcblk0p29 && "$root" != "$boot2" ]] || fail 'active root changed or equals boot2'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$boot2" ]] || fail 'boot2 by-partlabel disagrees with GPT'
sha256sum "$boot2" | awk '{print $1}'
REMOTE
) || die 'exact predecessor preflight failed'
case "$predecessor" in
"$EXPECTED_PREDECESSOR_SHA256"|"$CANDIDATE_SHA256") ;;
*) die 'boot2 is neither the exact predecessor nor the already-installed candidate' ;;
esac
printf 'boot2_preflight_sha256=%s\n' "$predecessor"

set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
