#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# read-only event-envelope state candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-dual-modalias-pre-dispatch-suppression/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=a44b8f336d69b642cee844f48d3065557d5c01f130a2a18333f21b6eb69ad0ce
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
	s#79c3bcb9afde686659be552cfb906f142f392b72c662db2dc9f623b52b3f3141#c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736#g;
	s#ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072#4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9#g;
	s#81cdca19d56faba451804d358d631c9fe3b50624522768d9bb19fa0e0b1da648#ad82cab56687ee3b8cccda7bb8010b6bb82363f23c77153f59d3ac0a73b46275#g;
	s#candidate-Gate3-da921x-dualpre-8be48f43#candidate-Gate3-da921x-envstate-b6d6b25d#g;
	s#DA921x dual-modalias pre-dispatch-suppression#DA921x dual-modalias event-envelope state#g;
	s#2026-07-31-da921x-dual-modalias-pre-dispatch-suppression#2026-07-31-da921x-dual-modalias-envelope-state#g;
	s#gemini-da921x-dualpre#gemini-da921x-envstate#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	79c3bcb9afde686659be552cfb906f142f392b72c662db2dc9f623b52b3f3141 \
	ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072 \
	81cdca19d56faba451804d358d631c9fe3b50624522768d9bb19fa0e0b1da648 \
	b7edda8e0fd9c084ac3e98820f51122b6d943904ec1fc377b4d5ff6e3edf3e91 \
	candidate-Gate3-da921x-dualpre-8be48f43 \
	2026-07-31-da921x-dual-modalias-pre-dispatch-suppression \
	gemini-da921x-dualpre; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=c755109e73f2148516942b2a31a3a06952abdf72c0154c5b70259836b8fcb736' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
