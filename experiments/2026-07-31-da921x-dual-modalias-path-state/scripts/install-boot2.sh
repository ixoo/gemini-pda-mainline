#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# live-path-corrected dual-modalias read-only-state candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-dual-modalias-state/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=9a19687cbd540762d91ce2fc7c63634b8c8897fc86e3b96304913721ee265d23
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
	s%s#ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072#5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3#g;%s#ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072#f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015#g;%g;
	s%s#79c3bcb9afde686659be552cfb906f142f392b72c662db2dc9f623b52b3f3141#ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072#g;%s#79c3bcb9afde686659be552cfb906f142f392b72c662db2dc9f623b52b3f3141#5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3#g;%g;
	s#EXPECTED_PREDECESSOR_SHA256=ddb7fadf7cd41f7ef805e2120f299b8034b7fc5ccedea2b6da7fb9976794e072#EXPECTED_PREDECESSOR_SHA256=5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3#g;
	s#CANDIDATE_SHA256=5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3#CANDIDATE_SHA256=f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015#g;
	s#6d5a81d43509fe88d23e3ac2abf3479f044281b3f7ba02240e6683e9b8ea4dba#35438e95a7363fc8e9e5b5ad5aba0d003190f8ea37ad984fe7f6ee312656b014#g;
	s#candidate-Gate3-da921x-dualstate-53376218#candidate-Gate3-da921x-pathstate-3cda4b88#g;
	s#DA921x dual-modalias read-only-state#DA921x dual-modalias live-path state#g;
	s#2026-07-31-da921x-dual-modalias-state#2026-07-31-da921x-dual-modalias-path-state#g;
	s#gemini-da921x-dstate#gemini-da921x-pstate#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	6d5a81d43509fe88d23e3ac2abf3479f044281b3f7ba02240e6683e9b8ea4dba \
	candidate-Gate3-da921x-dualstate-53376218 \
	2026-07-31-da921x-dual-modalias-state \
	gemini-da921x-dstate; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=5c3788905c6c3270d7416997c922f0774802fafb5086e10ff5f247ca0a26a1b3' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=f3ef6a90777b14f3b1ffed2fa23f9497ec5472d380aaaa59db0fb8bd706c4015' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
