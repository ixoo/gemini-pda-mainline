#!/usr/bin/env bash

# Source-pin the guarded provider-ready installer and retarget it to the exact
# platform/provider/protected-clock candidate. Accept only empty retained
# records or the exact completed provider pair from the successful predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=8eb5539777dd36ac4b499e8c647f20983e1cc63a7af70c401ae56d17d52847fc
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_PREDECESSOR_SHA256=f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/scripts/install-boot2.sh"
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

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-provider-clock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "# provider-ready candidate. Accept only empty retained records or the exact\n"
        "# before-provider/empty pair recovered from the predecessor attempt.",
        "# platform/provider/protected-clock candidate. Accept only empty retained\n"
        "# records or the exact completed provider pair from the predecessor.",
        1,
    ),
    (
        "provider-ready candidate. Accept only an empty retained pair or the",
        "platform/provider/protected-clock candidate. Accept only an empty pair or the",
        1,
    ),
    (
        "exact before-provider/empty pair recovered from its predecessor.",
        "exact completed provider pair recovered from its predecessor.",
        1,
    ),
    (
        "readonly VALID_HEADER_2=444247430000000000000000",
        "readonly VALID_HEADER_2=444247437e0000007e000000",
        1,
    ),
    (
        "readonly CONTROL_2_SHA256=d58e2f4ee9541fa1f2a2d07247ffb6a1fa6a31fefaa83c3715fcfe4fd3ec9998",
        "readonly CONTROL_2_SHA256=2f0ad139001347459344b031abd8376f63ff455f1742d24569823f33d23918e0",
        1,
    ),
    ("state=exact-before-provider-only-pair", "state=exact-completed-provider-pair", 1),
    (
        "retained records are neither exact empty nor the exact predecessor before-provider-only pair",
        "retained records are neither exact empty nor the exact completed predecessor provider pair",
        1,
    ),
    (
        "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e",
        "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
        1,
    ),
    (
        "ffee91da5291546ce95c807cf22a659976fa10ef61546b4cb8084e80b8627458",
        "2a600e48125d45b6281bb8c056ebbc1f107e2b3039791184b5e334f4414606d0",
        1,
    ),
    (
        "candidate-a72-platform-provider-ready-041896e2",
        "candidate-a72-platform-provider-clock-d2f4d2bd",
        1,
    ),
    (
        "a72-platform-provider-ready-deployment-",
        "a72-platform-provider-clock-deployment-",
        1,
    ),
    (
        r"\.gemini-a72-platform-provider-ready\.",
        r"\.gemini-a72-platform-provider-clock\.",
        1,
    ),
    (
        "/home/gemini/.gemini-a72-platform-provider-ready.XXXXXXXX",
        "/home/gemini/.gemini-a72-platform-provider-clock.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-25-mainline-a72-platform-provider-deferred-bind-repair",
        "experiment=2026-08-25-mainline-a72-platform-provider-protected-clock-third-read",
        1,
    ),
    ("unsafe provider-ready installer derivation", "unsafe platform/provider/clock installer derivation", 1),
    (
        ".derived-install-boot2-a72-platform-provider-ready-nested.XXXXXXXX",
        ".derived-install-boot2-a72-platform-provider-clock-nested.XXXXXXXX",
        1,
    ),
    (
        ".derived-install-boot2-a72-platform-provider-ready.XXXXXXXX",
        ".derived-install-boot2-a72-platform-provider-clock-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider/clock installer wrapper: expected {count}, "
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
	fail 'boot2 is not the exact successful provider-ready predecessor'
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
