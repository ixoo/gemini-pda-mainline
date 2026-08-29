#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the exact pmsg-witness
# candidate from the target-register capsule installer.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
parent_dir="$repo_root/experiments/2026-08-28-a72-target-register-capsule/scripts"
parent_installer="$parent_dir/install-boot2.sh"
readonly PARENT_INSTALLER_SHA256=d32d5aed962954a122f361ad589d0ebfa8e10372a450c92fb73afddee38c9b39
parent_sha256="$(sha256sum "$parent_installer" | awk '{print $1}')"
[[ -f "$parent_installer" && ! -L "$parent_installer" &&
	"$parent_sha256" == "$PARENT_INSTALLER_SHA256" ]] ||
	die 'target-register installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-pmsg-installer.XXXXXXXX")"
# Invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317,SC2329
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_A72_PMSG_PARENT_SCRIPT_DIR:?missing}"#g;
	s#f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f#0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78#g;
	s#df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60#f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f#g;
	s#d3a2d9f30d36e9227abf327af27e52c418461236e00a41a705f4514bdfbfe562#38112dbb0a783c8fac0234f3856ed85488560bb16a4196ad9ec7248cb2b0e8dc#g;
	s#gemian-a72-target-register-capsule-d4ae9ee1b2f7#gemian-a72-pmsg-witness-f2be7936996e#g;
	s#Gemian A72 target-register capsule candidate#Gemian A72 pmsg-witness candidate#g;
	s#2026-08-28-a72-target-register-capsule#2026-08-28-a72-pmsg-witness#g;
	s#\.gemian-a72-register-capsule#\.gemian-a72-pmsg-witness#g;
' "$parent_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f' \
	'CANDIDATE_SHA256=0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78' \
	'ARTIFACT_MANIFEST_SHA256=38112dbb0a783c8fac0234f3856ed85488560bb16a4196ad9ec7248cb2b0e8dc' \
	'ARTIFACT_NAME=gemian-a72-pmsg-witness-f2be7936996e' \
	'2026-08-28-a72-pmsg-witness'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done

export GEMINI_A72_PMSG_PARENT_SCRIPT_DIR="$parent_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
