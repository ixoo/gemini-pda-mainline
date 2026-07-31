#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# read-only event-entry classification candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-dual-modalias-envelope-state/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=88df2829ac2afdb6331f9570261dcac21aa5aac0b1bce26bfcbb0d646b39e9c4
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
	s#4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#g;
	s#c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736#4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9#g;
	s#ad82cab56687ee3b8cccda7bb8010b6bb82363f23c77153f59d3ac0a73b46275#594a34e303e6f8150806829e564748706327c985d852e0e65dc7cf29dd78e281#g;
	s#candidate-Gate3-da921x-envstate-b6d6b25d#candidate-Gate3-da921x-entryclass-5933dc9f#g;
	s#DA921x dual-modalias event-envelope state#DA921x dual-modalias event-entry classification#g;
	s#2026-07-31-da921x-dual-modalias-envelope-state#2026-07-31-da921x-dual-modalias-entry-classification#g;
	s#gemini-da921x-envstate#gemini-da921x-entryclass#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736 \
	ad82cab56687ee3b8cccda7bb8010b6bb82363f23c77153f59d3ac0a73b46275 \
	candidate-Gate3-da921x-envstate-b6d6b25d \
	2026-07-31-da921x-dual-modalias-envelope-state \
	gemini-da921x-envstate; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
