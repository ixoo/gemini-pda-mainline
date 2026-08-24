#!/usr/bin/env bash

# Source-pin the guarded live-GPT/TEE installer and retarget only its exact
# platform-state-only candidate. Accept only an empty retained pair or the
# exact Stage-27 control pair that this live-network experiment supersedes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7f5bddb91bf38fb5de9cce5bde5c1aa7bac4a114a7619d25f49621fb715b912d
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EMPTY_HEADER=444247430000000000000000
readonly VALID_HEADER=444247437800000078000000
readonly EMPTY_SHA256=d58e2f4ee9541fa1f2a2d07247ffb6a1fa6a31fefaa83c3715fcfe4fd3ec9998
readonly CONTROL_1_SHA256=dd39c08c5de7d9cde7ccf9f62707521475ce1ff35b3833f06443939bcff79e06
readonly CONTROL_2_SHA256=ad7909f9294e69f1efc13354c997b864a40c89a5c9f1cef9a445aa4f9f58b239

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/install-boot2.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini SSH identity is missing'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'

target=
evidence_dir=
help_only=no
record_preflight_only=no
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
	--record-preflight-only) record_preflight_only=yes; shift ;;
	-h|--help) help_only=yes; shift ;;
	*) shift ;;
	esac
done

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (".derived-install-boot2.XXXXXXXX", ".derived-install-boot2-a72-platform-only.XXXXXXXX", 1),
    ("30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a", "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", 1),
    ("f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a", "07f89b083539be006efe1e8407694153daa00b581b95394e40844bd71d54c7da", 1),
    ("candidate-protected-readback-ro-a3cb0e1c", "candidate-a72-platform-state-only-f3210fb3", 3),
    ("protected-readback-deployment-", "a72-platform-state-only-deployment-", 1),
    (r"\.gemini-protected-readback\.", r"\.gemini-a72-platform-state-only\.", 1),
    ("/home/gemini/.gemini-protected-readback.XXXXXXXX", "/home/gemini/.gemini-a72-platform-state-only.XXXXXXXX", 1),
    ("experiment=2026-08-21-mainline-protected-readback-runtime-observer", "experiment=2026-08-24-mainline-a72-platform-state-only", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform-state-only installer derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
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
	die 'exact target and evidence directory are required before retained-record preflight'

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
record_output="$("${ssh_command[@]}" "$target" \
	"sudo -n env EMPTY_HEADER='$EMPTY_HEADER' VALID_HEADER='$VALID_HEADER' EMPTY_SHA256='$EMPTY_SHA256' CONTROL_1_SHA256='$CONTROL_1_SHA256' CONTROL_2_SHA256='$CONTROL_2_SHA256' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in cat cut dd id od sha256sum tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
[[ -c /dev/mem ]] || fail '/dev/mem is unavailable'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || fail 'malformed boot ID'

for spec in 1:0x44410000 2:0x44411000; do
	record=${spec%%:*}
	address=${spec#*:}
	header=$(dd if=/dev/mem bs=1 skip=$((address)) count=12 status=none |
		od -An -tx1 | tr -d ' \n')
	digest=$(dd if=/dev/mem bs=4096 skip=$((address / 4096)) count=1 status=none |
		sha256sum | cut -d ' ' -f 1)
	printf -v "header_$record" '%s' "$header"
	printf -v "digest_$record" '%s' "$digest"
done

if [[ "$header_1" == "$EMPTY_HEADER" && "$header_2" == "$EMPTY_HEADER" &&
	"$digest_1" == "$EMPTY_SHA256" && "$digest_2" == "$EMPTY_SHA256" ]]; then
	state=exact-empty
elif [[ "$header_1" == "$VALID_HEADER" && "$header_2" == "$VALID_HEADER" &&
	"$digest_1" == "$CONTROL_1_SHA256" && "$digest_2" == "$CONTROL_2_SHA256" ]]; then
	state=exact-stage27-control-pair
else
	fail 'retained records are neither exact empty nor the exact Stage-27 control pair'
fi
printf 'record_preflight_boot_id=%s\n' "$boot_id"
printf 'dmesg_record_1_header=%s\ndmesg_record_1_sha256=%s\n' "$header_1" "$digest_1"
printf 'dmesg_record_2_header=%s\ndmesg_record_2_sha256=%s\n' "$header_2" "$digest_2"
printf 'dmesg_records_1_2_prewrite=%s\nretained_ram_write=none\n' "$state"
REMOTE
)" || die 'live platform-state-only retained-record preflight failed'
printf '%s\n' "$record_output"
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
	case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
	summary="$evidence_dir/deployment-summary.txt"
	[[ -f "$summary" && ! -L "$summary" ]] || die 'deployment summary missing after success'
	printf '%s\n' "$record_output" >>"$summary"
	(
		cd "$evidence_dir"
		sha256sum deployment-summary.txt >SHA256SUMS
	)
	chmod 0600 "$evidence_dir/SHA256SUMS"
fi
cleanup
trap - EXIT HUP INT TERM
exit "$status"
