#!/usr/bin/env bash

# Source-pin the generic live-GPT/TEE installer and retarget it to the exact
# failure-stage candidate. Accept only logically empty retained headers or the
# exact completed provider pair already accepted by the retired predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7f5bddb91bf38fb5de9cce5bde5c1aa7bac4a114a7619d25f49621fb715b912d
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_PREDECESSOR_SHA256=1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2
readonly EMPTY_HEADER=444247430000000000000000
readonly VALID_HEADER_1=444247437f0000007f000000
readonly VALID_HEADER_2=444247437e0000007e000000
readonly CONTROL_1_SHA256=047e5c5c6f3bfa3b8f86ba174c3e1ceb65926a190dbec7099f915ee5b7e371b2
readonly CONTROL_2_SHA256=2f0ad139001347459344b031abd8376f63ff455f1742d24569823f33d23918e0

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/install-boot2.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
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
	--target)
		(($# >= 2)) || die '--target requires a value'
		target=$2
		shift 2
		;;
	--evidence-dir)
		(($# >= 2)) || die '--evidence-dir requires a value'
		evidence_dir=$2
		shift 2
		;;
	--candidate-dir)
		(($# >= 2)) || die '--candidate-dir requires a value'
		shift 2
		;;
	--record-preflight-only)
		record_preflight_only=yes
		shift
		;;
	-h|--help)
		help_only=yes
		shift
		;;
	*)
		shift
		;;
	esac
done

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-provider-clock-stage-generic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "# Source-pin and derive the guarded installer for the exact protected-readback\n"
        "# observer candidate, adding the mandatory live tee1/tee2 identity gate.",
        "# Source-pin and derive the guarded installer for the exact failure-stage\n"
        "# candidate, retaining the mandatory live tee1/tee2 identity gate.",
        1,
    ),
    (
        "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",
        1,
    ),
    (
        "f1ceff04a7631af3ee2c3b3614d9fd025f956a2453a75b0cc6d3fd6cde24580a",
        "1a73373660e3b07d8ee830f940ab7fb31e0f791406e877b6c9824f133ce363ea",
        1,
    ),
    (
        "candidate-protected-readback-ro-a3cb0e1c",
        "candidate-a72-platform-provider-clock-stage-8ca14ec2",
        3,
    ),
    (
        "protected-readback-deployment-",
        "a72-platform-provider-clock-stage-deployment-",
        1,
    ),
    (
        r"\.gemini-protected-readback\.",
        r"\.gemini-a72-platform-provider-clock-stage\.",
        1,
    ),
    (
        "/home/gemini/.gemini-protected-readback.XXXXXXXX",
        "/home/gemini/.gemini-a72-platform-provider-clock-stage.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-runtime-observer",
        "experiment=2026-08-25-mainline-a72-platform-provider-failure-stage-attribution",
        1,
    ),
    (
        ".derived-install-boot2.XXXXXXXX",
        ".derived-install-boot2-a72-platform-provider-clock-stage-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe failure-stage installer wrapper: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

if [[ "$help_only" == yes ]]; then
	set +e
	/bin/bash "$derived" "${arguments[@]}"
	status=$?
	set -e
	cleanup
	trap - EXIT HUP INT TERM
	exit "$status"
fi

[[ "$target" == "$EXPECTED_TARGET" ]] || die 'exact Gemini target is required'
[[ -n "$evidence_dir" ]] || die 'exact evidence directory is required'
ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
predecessor_output="$("${ssh_command[@]}" "$target" \
	"sudo -n env EXPECTED_PREDECESSOR_SHA256='$EXPECTED_PREDECESSOR_SHA256' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk cat id lsblk readlink sha256sum uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')"
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2 row'
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && "$label" == boot2 &&
	"$type" == part && "$size" == 16777216 && "$ro" == 0 ]] ||
	fail 'boot2 identity, type, size, or writable state changed'
[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]] ||
	fail 'boot2 is mounted or invalid'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] ||
	fail 'boot2 by-partlabel disagrees with GPT'
actual="$(sha256sum "$target" | awk '{print $1}')"
[[ "$actual" == "$EXPECTED_PREDECESSOR_SHA256" ]] ||
	fail 'boot2 is not the exact retired third-reader predecessor'
printf 'boot2_predecessor_target=%s\nboot2_predecessor_sha256=%s\n' "$target" "$actual"
printf 'boot2_predecessor_read=full-partition\ndevice_partition_write=none\n'
REMOTE
)" || die 'exact boot2 predecessor preflight failed'
printf '%s\n' "$predecessor_output"

record_output="$("${ssh_command[@]}" "$target" \
	"sudo -n env EMPTY_HEADER='$EMPTY_HEADER' VALID_HEADER_1='$VALID_HEADER_1' VALID_HEADER_2='$VALID_HEADER_2' CONTROL_1_SHA256='$CONTROL_1_SHA256' CONTROL_2_SHA256='$CONTROL_2_SHA256' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in cat cut dd id od sha256sum tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
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
if [[ "$header_1" == "$EMPTY_HEADER" && "$header_2" == "$EMPTY_HEADER" ]]; then
	state=exact-logically-empty-headers
elif [[ "$header_1" == "$VALID_HEADER_1" && "$header_2" == "$VALID_HEADER_2" &&
	"$digest_1" == "$CONTROL_1_SHA256" && "$digest_2" == "$CONTROL_2_SHA256" ]]; then
	state=exact-completed-provider-pair
else
	fail 'retained headers are neither exact logical-empty nor the exact completed provider pair'
fi
printf 'record_preflight_boot_id=%s\n' "$boot_id"
printf 'dmesg_record_1_header=%s\ndmesg_record_1_sha256=%s\n' "$header_1" "$digest_1"
printf 'dmesg_record_2_header=%s\ndmesg_record_2_sha256=%s\n' "$header_2" "$digest_2"
printf 'dmesg_records_1_2_prewrite=%s\nretained_ram_write=none\n' "$state"
REMOTE
)" || die 'live retained-header preflight failed'
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
