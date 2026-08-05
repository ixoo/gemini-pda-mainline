#!/usr/bin/env bash

# Source-pin and derive the guarded boot2 installer for the scheduler-context
# kthread-unpark candidate from the accepted pair-v5/multiline installer.
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
# Invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317,SC2329
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#script_dir="\$\(cd -- "\$\(dirname -- "\$\{BASH_SOURCE\[0\]\}"\)" && pwd -P\)"#script_dir="\${GEMINI_A72_SCHEDULER_SCRIPT_DIR:?missing}"#g;
	s#5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48#5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5#g;
	s#eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d#2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8#g;
	s#56b85e0f597436938bec5f20889ed53f4079a274e6cd82d56fb81a097522bb58#9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5#g;
	s#gemian-a72-cpu9-multiline-integrity-4e3c1b1095ee#gemian-a72-scheduler-unpark-f3e235f3c196#g;
	s#Gemian A72 CPU9 multiline-integrity candidate#Gemian A72 scheduler kthread-unpark candidate#g;
	s#2026-08-03-a72-cpu9-multiline-integrity#2026-08-03-a72-scheduler-context#g;
	s#\.gemian-a72-cpu9-multiline#\.gemian-a72-scheduler-unpark#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for token in \
	'EXPECTED_PREDECESSOR_SHA256=2268e23559e8d36e4339a4fd912d0108721ed818e628dfc857cab2ab8e8049a8' \
	'CANDIDATE_SHA256=5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5' \
	'ARTIFACT_MANIFEST_SHA256=9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5' \
	'ARTIFACT_NAME=gemian-a72-scheduler-unpark-f3e235f3c196' \
	'2026-08-03-a72-scheduler-context'; do
	grep -Fq "$token" "$derived" || die "derived installer lacks: $token"
done
export GEMINI_A72_SCHEDULER_SCRIPT_DIR="$script_dir"
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
