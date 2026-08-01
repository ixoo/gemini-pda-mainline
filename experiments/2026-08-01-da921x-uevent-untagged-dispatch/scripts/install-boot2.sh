#!/usr/bin/env bash

# Source-pin and mechanically derive the exact boot2 installer for the
# untagged-dispatch candidate.
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
source_installer="$repo_root/experiments/2026-08-01-da921x-uevent-single-multicast/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=174dfbad4d21d6a45fca73f99b0c1b997bfedcb0da8c2dd5edcedbe7d9364a82
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == \
	"$SOURCE_INSTALLER_SHA256" ]] || die 'source boot2 installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-install-boot2.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274#__OLD_CANDIDATE__#g;
	s#e1327619295ab7d739ebd76dbf31ac91691ad91ca086acb34728dbf69a1e54e5#b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274#g;
	s#__OLD_CANDIDATE__#0c31f1c73bcd7f61d6b10010e17bd4de3bcc05ab6239130cab5d7fa2d26e139d#g;
	s#d1d8fff40a863c1427c24126dc2eef1a3fcdd75965b58266a61d3d5d8c9aa67d#de71c72f6dab69de7d3a2dee6fe7e98ca16c8e09d4d2811e64ef568eff40a53b#g;
	s#candidate-Gate3-da921x-mcast1-1183d5cb#candidate-Gate3-da921x-untag-2a6dcc2a#g;
	s#DA921x single multicast#DA921x untagged dispatch#g;
	s#2026-08-01-da921x-uevent-single-multicast#2026-08-01-da921x-uevent-untagged-dispatch#g;
	s#gemini-da921x-mcast1#gemini-da921x-untag#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	e1327619295ab7d739ebd76dbf31ac91691ad91ca086acb34728dbf69a1e54e5 \
	d1d8fff40a863c1427c24126dc2eef1a3fcdd75965b58266a61d3d5d8c9aa67d \
	candidate-Gate3-da921x-mcast1-1183d5cb \
	2026-08-01-da921x-uevent-single-multicast \
	gemini-da921x-mcast1; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=0c31f1c73bcd7f61d6b10010e17bd4de3bcc05ab6239130cab5d7fa2d26e139d' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
