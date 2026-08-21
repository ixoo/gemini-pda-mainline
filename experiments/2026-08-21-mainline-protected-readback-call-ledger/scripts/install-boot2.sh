#!/usr/bin/env bash

# Source-pin the guarded protected-readback installer for the exact call-ledger
# candidate and require a bounded live empty-slot preflight before delegation.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7f5bddb91bf38fb5de9cce5bde5c1aa7bac4a114a7619d25f49621fb715b912d
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_HEADER=434742440000000000000000

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/install-boot2.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini SSH identity is missing'
identity_mode="$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")"
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'

target=
evidence_dir=
help_only=no
arguments=("$@")
while (($#)); do
	case "$1" in
	--target|--candidate-dir|--evidence-dir)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--target) target=$2 ;;
		--evidence-dir) evidence_dir=$2 ;;
		esac
		shift 2
		;;
	-h|--help) help_only=yes; shift ;;
	*) shift ;;
	esac
done

derived="$(mktemp "$script_dir/.derived-install-boot2-call-ledger.XXXXXXXX")"
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
        "# Source-pin and derive the guarded installer for the exact protected-readback\n"
        "# observer candidate, adding the mandatory live tee1/tee2 identity gate.",
        "# Source-pin and derive the guarded installer for the exact protected-readback\n"
        "# call-ledger candidate, retaining the mandatory live tee1/tee2 identity gate.",
        1,
    ),
    (
        "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        1,
    ),
    (
        "f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a",
        "a4c5f0f463071aa46613230d1d9d1fb364664bb6722f701f218099402860c545",
        1,
    ),
    (
        "candidate-protected-readback-ro-a3cb0e1c",
        "candidate-protected-readback-ledger-199e618a",
        3,
    ),
    ("protected-readback-deployment-", "protected-readback-call-ledger-deployment-", 1),
    (r"\.gemini-protected-readback\.", r"\.gemini-protected-readback-ledger\.", 1),
    (
        "/home/gemini/.gemini-protected-readback.XXXXXXXX",
        "/home/gemini/.gemini-protected-readback-ledger.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-runtime-observer",
        "experiment=2026-08-21-mainline-protected-readback-call-ledger",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe call-ledger installer derivation: expected {count} occurrences, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

if [[ "$help_only" == yes ]]; then
	/bin/bash "$derived" "${arguments[@]}"
	status=$?
	cleanup
	trap - EXIT HUP INT TERM
	exit "$status"
fi
[[ "$target" == "$EXPECTED_TARGET" && -n "$evidence_dir" ]] ||
	die 'exact target and evidence directory are required before the slot preflight'

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
slot_output="$("${ssh_command[@]}" "$target" \
	"sudo -n env EXPECTED_HEADER='$EXPECTED_HEADER' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in cat dd id od tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
[[ -c /dev/mem ]] || fail '/dev/mem is unavailable'
boot_id="$(cat /proc/sys/kernel/random/boot_id)"
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || fail 'malformed boot ID'
for spec in 171:0x444bb000 172:0x444bc000 173:0x444bd000 174:0x444be000; do
	slot=${spec%%:*}
	address=${spec#*:}
	header="$(dd if=/dev/mem bs=1 skip=$((address)) count=12 status=none |
		od -An -tx1 | tr -d ' \n')"
	[[ "$header" == "$EXPECTED_HEADER" ]] || fail "retained slot $slot is not exactly empty"
	printf 'retained_slot_%s_header=%s\n' "$slot" "$header"
done
printf 'retained_slot_preflight_boot_id=%s\nretained_slots_prewrite=exact-empty\n' "$boot_id"
printf 'retained_ram_write=none\n'
REMOTE
)" || die 'live retained-slot preflight failed'
printf '%s\n' "$slot_output"

set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
if [[ "$status" == 0 ]]; then
	case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
	summary="$evidence_dir/deployment-summary.txt"
	[[ -f "$summary" && ! -L "$summary" ]] || die 'deployment summary missing after success'
	printf '%s\n' "$slot_output" >>"$summary"
	(
		cd "$evidence_dir"
		sha256sum deployment-summary.txt >SHA256SUMS
	)
	chmod 0600 "$evidence_dir/SHA256SUMS"
fi
cleanup
trap - EXIT HUP INT TERM
exit "$status"
