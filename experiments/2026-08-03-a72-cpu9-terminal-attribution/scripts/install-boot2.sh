#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the exact CPU9
# terminal-attribution candidate from the accepted retention-window installer.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-03-a72-cpu9-retention-window/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=792be0d814871670e41dec652709f8ac888ba9a97a1e97e033f01e0f84490ab4
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_INSTALLER_SHA256" ]] ||
	die 'source retention-window installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-cpu9-terminal-installer.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_CPU9_TERMINAL_SCRIPT_DIR:?missing}"#g;
	s#6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115#933299078d78e5882055e73fcbf75447bac9abf7d42b2074f37d65fe81966a70#g;
	s#b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69#6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115#g;
	s#3a17f39db6d219a14533ca638dedc5763f455c360e74cd80f8d56f20a5e67567#e614144e8fd13b4a7d49a0a54852c9557c0a9cb8743cd149982f5725bafd1e83#g;
	s#gemian-a72-cpu9-retention-window-140bed8c432d#gemian-a72-cpu9-terminal-attribution-05012d24f84a#g;
	s#Gemian A72 CPU9 retention-window candidate#Gemian A72 CPU9 terminal-attribution candidate#g;
	s#2026-08-03-a72-cpu9-retention-window#2026-08-03-a72-cpu9-terminal-attribution#g;
	s#\.gemian-a72-cpu9-window#\.gemian-a72-cpu9-terminal#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115' \
	'CANDIDATE_SHA256=933299078d78e5882055e73fcbf75447bac9abf7d42b2074f37d65fe81966a70' \
	'ARTIFACT_MANIFEST_SHA256=e614144e8fd13b4a7d49a0a54852c9557c0a9cb8743cd149982f5725bafd1e83' \
	'ARTIFACT_NAME=gemian-a72-cpu9-terminal-attribution-05012d24f84a' \
	'2026-08-03-a72-cpu9-terminal-attribution'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done
export GEMINI_CPU9_TERMINAL_SCRIPT_DIR="$script_dir"
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
