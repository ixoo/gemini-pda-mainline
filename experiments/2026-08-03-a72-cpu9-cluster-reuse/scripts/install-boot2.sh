#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the exact CPU9
# cluster-reuse candidate from the accepted held-online installer.
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

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-installer.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_SCRIPT_DIR:?missing}"#g;
	s#936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018#b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69#g;
	s#fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda#2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af#g;
	s#93ad961f64bcdd54d5b94afc2ed23c18de329cdce55a30b6de350bbb1f4084bb#036d2f121e716466cbd99c2b249df6507e33aee041210c8b093437c16bd81acc#g;
	s#gemian-a72-cpu8-held-online-53046cf314f7#gemian-a72-cpu9-cluster-reuse-fef3d814c217#g;
	s#Gemian A72 CPU8 held-online candidate#Gemian A72 CPU9 cluster-reuse candidate#g;
	s#2026-08-02-a72-cpu8-held-online#2026-08-03-a72-cpu9-cluster-reuse#g;
	s#\.gemini-a72-held#\.gemini-a72-cpu9#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af' \
	'CANDIDATE_SHA256=b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69' \
	'ARTIFACT_MANIFEST_SHA256=036d2f121e716466cbd99c2b249df6507e33aee041210c8b093437c16bd81acc' \
	'ARTIFACT_NAME=gemian-a72-cpu9-cluster-reuse-fef3d814c217' \
	'2026-08-03-a72-cpu9-cluster-reuse'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done
export GEMINI_CPU9_SCRIPT_DIR="$script_dir"
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
