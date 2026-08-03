#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the exact pair-v7
# scheduler-context candidate from the accepted pair-v6 installer.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-03-a72-cpu9-multiline-integrity/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=a2a3f292f0bb857be0251c7bacabecfa9157b2034d3a7ecc1ccd6b5541b672c9
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_INSTALLER_SHA256" ]] ||
	die 'source pair-v5 installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-scheduler-installer.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_A72_SCHEDULER_SCRIPT_DIR:?missing}"#g;
	s#5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48#24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f#g;
	s#eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d#0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb#g;
	s#56b85e0f597436938bec5f20889ed53f4079a274e6cd82d56fb81a097522bb58#a2c207ebcaa7fdae4e5144f2075b6838f677e9bacca7fcee5bee32d43c326384#g;
	s#gemian-a72-cpu9-multiline-integrity-4e3c1b1095ee#gemian-a72-scheduler-context-f9fddf01576a#g;
	s#Gemian A72 CPU9 multiline-integrity candidate#Gemian A72 scheduler-context candidate#g;
	s#2026-08-03-a72-cpu9-multiline-integrity#2026-08-03-a72-scheduler-context#g;
	s#\.gemian-a72-cpu9-multiline#\.gemian-a72-scheduler#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb' \
	'CANDIDATE_SHA256=24377665fa5b9112266890844c06c453bb50e17680b6f6f956035c234c26ff0f' \
	'ARTIFACT_MANIFEST_SHA256=a2c207ebcaa7fdae4e5144f2075b6838f677e9bacca7fcee5bee32d43c326384' \
	'ARTIFACT_NAME=gemian-a72-scheduler-context-f9fddf01576a' \
	'2026-08-03-a72-scheduler-context'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done
export GEMINI_A72_SCHEDULER_SCRIPT_DIR="$script_dir"
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
