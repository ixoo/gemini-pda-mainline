#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the exact target-
# register capsule candidate from the accepted scheduler-unpark installer.
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
parent_dir="$repo_root/experiments/2026-08-03-a72-scheduler-context/scripts"
parent_installer="$parent_dir/install-boot2.sh"
readonly PARENT_INSTALLER_SHA256=29236d880bf33377d77eee66183ad682016b1769ef0b541f519bdb3e90a503b3
parent_sha256="$(sha256sum "$parent_installer" | awk '{print $1}')"
[[ -f "$parent_installer" && ! -L "$parent_installer" &&
	"$parent_sha256" == "$PARENT_INSTALLER_SHA256" ]] ||
	die 'scheduler installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-regcap-installer.XXXXXXXX")"
# Invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317,SC2329
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_A72_REGCAP_PARENT_SCRIPT_DIR:?missing}"#g;
	s#5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5#f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f#g;
	s#2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8#df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60#g;
	s#9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5#d3a2d9f30d36e9227abf327af27e52c418461236e00a41a705f4514bdfbfe562#g;
	s#gemian-a72-scheduler-unpark-f3e235f3c196#gemian-a72-target-register-capsule-d4ae9ee1b2f7#g;
	s#Gemian A72 scheduler kthread-unpark candidate#Gemian A72 target-register capsule candidate#g;
	s#2026-08-03-a72-scheduler-context#2026-08-28-a72-target-register-capsule#g;
	s#\.gemian-a72-scheduler-unpark#\.gemian-a72-register-capsule#g;
' "$parent_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60' \
	'CANDIDATE_SHA256=f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f' \
	'ARTIFACT_MANIFEST_SHA256=d3a2d9f30d36e9227abf327af27e52c418461236e00a41a705f4514bdfbfe562' \
	'ARTIFACT_NAME=gemian-a72-target-register-capsule-d4ae9ee1b2f7' \
	'2026-08-28-a72-target-register-capsule'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done

export GEMINI_A72_REGCAP_PARENT_SCRIPT_DIR="$parent_dir"
status=0
"$derived" "$@" || status=$?
exit "$status"
