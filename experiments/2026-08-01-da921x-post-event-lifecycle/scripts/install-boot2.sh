#!/usr/bin/env bash

# Source-pin and mechanically derive the exact boot2 installer for the
# post-event lifecycle candidate.
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
source_installer="$repo_root/experiments/2026-08-01-da921x-uevent-untagged-dispatch/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=58f902b9be590c29cb599ccc23425e4e4a2229e0e21a0bb918c7d7cc8001b49f
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
	s#0c31f1c73bcd7f61d6b10010e17bd4de3bcc05ab6239130cab5d7fa2d26e139d#__NEW_CANDIDATE__#g;
	s!s#b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274#__OLD_CANDIDATE__#g;!s#__KEEP_OLD_CANDIDATE__#__OLD_CANDIDATE__#g;!;
	s#b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274#4855ad0f92e9f623b6e4f1c3ae08ac413895e9118c4a18a395546b66c4141472#g;
	s#__KEEP_OLD_CANDIDATE__#b8113be2e197a8ab06baf863da8679ff585360ef75b8c60359742f8afb862274#g;
	s#__NEW_CANDIDATE__#805c3c1ce28131847924679a70186a75d277da3ab2be9565cea02bf546150f28#g;
	s#de71c72f6dab69de7d3a2dee6fe7e98ca16c8e09d4d2811e64ef568eff40a53b#dd132ecc14bcaea73552fe7a12a3ff028e50f57435549045b4710ff4befd64cf#g;
	s#candidate-Gate3-da921x-untag-2a6dcc2a#candidate-Gate3-da921x-life27-79517c78#g;
	s#DA921x untagged dispatch#DA921x post-event lifecycle#g;
	s#2026-08-01-da921x-uevent-untagged-dispatch#2026-08-01-da921x-post-event-lifecycle#g;
	s#gemini-da921x-untag#gemini-da921x-life27#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	de71c72f6dab69de7d3a2dee6fe7e98ca16c8e09d4d2811e64ef568eff40a53b \
	candidate-Gate3-da921x-untag-2a6dcc2a \
	2026-08-01-da921x-uevent-untagged-dispatch \
	gemini-da921x-untag \
	__NEW_CANDIDATE__ \
	__KEEP_OLD_CANDIDATE__; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=4855ad0f92e9f623b6e4f1c3ae08ac413895e9118c4a18a395546b66c4141472' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=805c3c1ce28131847924679a70186a75d277da3ab2be9565cea02bf546150f28' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
