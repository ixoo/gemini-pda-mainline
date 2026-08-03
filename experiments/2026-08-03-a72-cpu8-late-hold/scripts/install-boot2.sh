#!/usr/bin/env bash

# Source-pin and mechanically derive the guarded boot2 installer for the exact
# late-hold candidate from the accepted held-online installer.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-02-a72-cpu8-held-online/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=074464f4bea0062dab763d2cc3ce69fb3b827c6fcafaea98e7f7b9910a66f602
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_INSTALLER_SHA256" ]] ||
	die 'source held-online installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-late-installer.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_LATE_SCRIPT_DIR:?missing}"#g;
	s#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af#g;
	s#fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#g;
	s#93ad961f64bcdd54d5b94afc2ed23c18de329cdce55a30b6de350bbb1f4084bb#7a5dbc965a93ea1c1e2eac48a16a2af81e0c56e96bcdf845aa01dda3ebf53ccd#g;
	s#gemian-a72-cpu8-held-online-53046cf314f7#gemian-a72-cpu8-late-hold-53ba2e4dbc20#g;
	s#Gemian A72 CPU8 held-online candidate#Gemian A72 CPU8 late-hold candidate#g;
	s#2026-08-02-a72-cpu8-held-online#2026-08-03-a72-cpu8-late-hold#g;
	s#\.gemini-a72-held#\.gemini-a72-late#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018' \
	'CANDIDATE_SHA256=2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af' \
	'ARTIFACT_MANIFEST_SHA256=7a5dbc965a93ea1c1e2eac48a16a2af81e0c56e96bcdf845aa01dda3ebf53ccd' \
	'ARTIFACT_NAME=gemian-a72-cpu8-late-hold-53ba2e4dbc20' \
	'2026-08-03-a72-cpu8-late-hold'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done
export GEMINI_LATE_SCRIPT_DIR="$script_dir"
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
