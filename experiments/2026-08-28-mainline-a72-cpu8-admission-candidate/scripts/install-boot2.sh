#!/usr/bin/env bash

# Source-pin the live-GPT/TEE installer, retarget it to the exact CPU8
# admission candidate, add a read-only transition-ledger preflight, and require
# TCP/22 closure after its verified write and clean shutdown.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7f5bddb91bf38fb5de9cce5bde5c1aa7bac4a114a7619d25f49621fb715b912d
readonly LEDGER_VALIDATOR_SHA256=cefe3d19ad05c4facbdff7725667c33105d5d714c9d6b32d5ba993d5fccd9e85
readonly SHUTDOWN_HELPER_SHA256=35317e3533cb0c9b757e198b519fac8be0f88fa1f9e423c4e717fcabb276b833
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly DEVICE_ADDRESS=192.168.1.50

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod mktemp python3 rm sha256sum ssh stat tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/install-boot2.sh"
ledger_validator="$script_dir/validate-transition-ledger.py"
shutdown_helper="$repo_root/experiments/2026-08-26-mainline-a72-cpu-status-mask-repair/scripts/confirm-shutdown-port.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
for input in "$source_installer" "$ledger_validator" "$shutdown_helper" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "required input is missing or unsafe: $input"
done
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'
[[ "$(sha256sum "$ledger_validator" | awk '{print $1}')" == "$LEDGER_VALIDATOR_SHA256" ]] ||
	die 'transition-ledger validator changed'
[[ "$(sha256sum "$shutdown_helper" | awk '{print $1}')" == "$SHUTDOWN_HELPER_SHA256" ]] ||
	die 'shutdown TCP helper changed'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'

target=
evidence_dir=
help_only=no
record_preflight_only=no
arguments=()
while (($#)); do
	case "$1" in
	--target)
		(($# >= 2)) || die '--target requires a value'
		target=$2
		arguments+=("$1" "$2")
		shift 2
		;;
	--evidence-dir)
		(($# >= 2)) || die '--evidence-dir requires a value'
		evidence_dir=$2
		arguments+=("$1" "$2")
		shift 2
		;;
	--candidate-dir)
		(($# >= 2)) || die '--candidate-dir requires a value'
		arguments+=("$1" "$2")
		shift 2
		;;
	--record-preflight-only)
		record_preflight_only=yes
		shift
		;;
	-h|--help)
		help_only=yes
		arguments+=("$1")
		shift
		;;
	*)
		arguments+=("$1")
		shift
		;;
	esac
done

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-admission.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("protected-readback observer", "CPU8 admission", 1),
    ("30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
     "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0", 1),
    ("f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a",
     "8dc9f0d50e7939fc359572206bd4604d2c5043e5a8cbc9a319e930be243189b6", 1),
    ("candidate-protected-readback-ro-a3cb0e1c", "candidate-a72-admission-d52d3c4e", 3),
    ("protected-readback-deployment-", "a72-admission-deployment-", 1),
    (r"\.gemini-protected-readback\.", r"\.gemini-a72-admission\.", 1),
    ("/home/gemini/.gemini-protected-readback.XXXXXXXX",
     "/home/gemini/.gemini-a72-admission.XXXXXXXX", 1),
    ("experiment=2026-08-21-mainline-protected-readback-runtime-observer",
     "experiment=2026-08-28-mainline-a72-cpu8-admission-candidate", 1),
    (".derived-install-boot2.XXXXXXXX",
     ".derived-install-boot2-a72-admission-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU8 admission installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

if [[ "$help_only" == yes ]]; then
	/bin/bash "$derived" "${arguments[@]}"
	exit $?
fi
[[ "$target" == "$EXPECTED_TARGET" ]] || die 'exact Gemini target is required'
if [[ "$record_preflight_only" == no && -z "$evidence_dir" ]]; then
	die 'exact evidence directory is required'
fi

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
ledger_hex="$("${ssh_command[@]}" "$target" 'sudo -n /bin/bash -s' <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in cat dd id od tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || fail 'malformed boot ID'
printf 'ledger_boot_id=%s\n' "$boot_id" >&2
dd if=/dev/mem bs=1 skip=$((0x44410000)) count=84 status=none |
	od -An -v -tx1 | tr -d ' \n'
REMOTE
)" || die 'read-only transition-ledger preflight capture failed'
[[ "$ledger_hex" =~ ^[0-9a-f]{168}$ ]] || die 'malformed transition-ledger bytes'
ledger_output=$(python3 "$ledger_validator" --hex "$ledger_hex") ||
	die 'transition-ledger preflight rejected current retained bytes'
printf '%s\n' "$ledger_output"
if [[ "$record_preflight_only" == yes ]]; then
	cleanup
	trap - EXIT HUP INT TERM
	exit 0
fi

set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
if [[ "$status" == 0 ]]; then
	shutdown_output=$(python3 "$shutdown_helper" --address "$DEVICE_ADDRESS" \
		--port 22 --attempts 20 --required-consecutive 3 --interval 2 --timeout 1) ||
		die 'write/readback passed but TCP/22 closure is not confirmed'
	printf '%s\n' "$shutdown_output"
	case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
	summary="$evidence_dir/deployment-summary.txt"
	[[ -f "$summary" && ! -L "$summary" ]] || die 'deployment summary missing after success'
	{
		printf '%s\n' "$ledger_output"
		printf '%s\nshutdown_confirmation=ssh-failure-plus-three-tcp-closures\n' "$shutdown_output"
	} >>"$summary"
	(
		cd "$evidence_dir"
		sha256sum deployment-summary.txt >SHA256SUMS
	)
	chmod 0600 "$evidence_dir/SHA256SUMS"
fi
cleanup
trap - EXIT HUP INT TERM
exit "$status"
