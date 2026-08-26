#!/usr/bin/env bash

# Source-pin the guarded third-reader installer and retarget it to the exact
# failure-stage candidate. Accept only empty retained records or the exact
# completed provider pair already accepted by the retired predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=80b3609bc7e190f4c9b215fa22307db23cfcf5e5eec912408919c3e9e4bef819
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_PREDECESSOR_SHA256=1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/scripts/install-boot2.sh"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini SSH identity is missing'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'

target=
help_only=no
arguments=("$@")
while (($#)); do
	case "$1" in
	--target)
		(($# >= 2)) || die '--target requires a value'
		target=$2
		shift 2
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

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-provider-clock-stage.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "# platform/provider/protected-clock candidate. Accept only empty retained\n"
        "# records or the exact completed provider pair from the successful predecessor.",
        "# failure-stage candidate. Accept only empty retained records or the exact\n"
        "# completed provider pair already accepted by the retired predecessor.",
        1,
    ),
    (
        "readonly EXPECTED_PREDECESSOR_SHA256=f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e",
        "readonly EXPECTED_PREDECESSOR_SHA256=1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
        1,
    ),
    (
        '        "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",',
        '        "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",',
        1,
    ),
    (
        "2a600e48125d45b6281bb8c056ebbc1f107e2b3039791184b5e334f4414606d0",
        "1a73373660e3b07d8ee830f940ab7fb31e0f791406e877b6c9824f133ce363ea",
        1,
    ),
    (
        "candidate-a72-platform-provider-clock-d2f4d2bd",
        "candidate-a72-platform-provider-clock-stage-8ca14ec2",
        1,
    ),
    (
        "a72-platform-provider-clock-deployment-",
        "a72-platform-provider-clock-stage-deployment-",
        1,
    ),
    (
        r"\.gemini-a72-platform-provider-clock\.",
        r"\.gemini-a72-platform-provider-clock-stage\.",
        1,
    ),
    (
        "/home/gemini/.gemini-a72-platform-provider-clock.XXXXXXXX",
        "/home/gemini/.gemini-a72-platform-provider-clock-stage.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-25-mainline-a72-platform-provider-protected-clock-third-read",
        "experiment=2026-08-25-mainline-a72-platform-provider-failure-stage-attribution",
        1,
    ),
    (
        "unsafe platform/provider/clock installer derivation",
        "unsafe platform/provider/clock-stage installer derivation",
        1,
    ),
    (
        ".derived-install-boot2-a72-platform-provider-clock-nested.XXXXXXXX",
        ".derived-install-boot2-a72-platform-provider-clock-stage-nested.XXXXXXXX",
        1,
    ),
    (
        ".derived-install-boot2-a72-platform-provider-clock.XXXXXXXX",
        ".derived-install-boot2-a72-platform-provider-clock-stage-inner.XXXXXXXX",
        1,
    ),
    (
        "boot2 is not the exact successful provider-ready predecessor",
        "boot2 is not the exact retired third-reader predecessor",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider/clock-stage installer wrapper: expected {count}, "
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

set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
