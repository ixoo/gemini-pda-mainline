#!/usr/bin/env bash

# One-deployment owner-authorized battery-threshold override. All other gates
# are mechanically retained from the checksum-pinned guarded installer.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "${1:-}" == --owner-battery-override ]] ||
	die 'explicit --owner-battery-override is required'
shift
for command in awk chmod grep mktemp perl rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-07-29-da921x-probe-isolation/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == \
	"$SOURCE_INSTALLER_SHA256" ]] || die 'source boot2 installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-rollback-power-override.XXXXXXXX")"
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#c9ea62bccb9ac3caedd8e6a77986a81cbb1e83fbaa329be4f6433cfb4da47b6e#6dcbda0cb264f5b637f6333f4946707d81ea98d38a8d52673b6fbe2cf109e3af#g;
	s#b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa#6a180e5a62a00cd7c97d461c7a1c491cd47802bd0964ef82f75ee793d6b8bede#g;
	s#b66ff99853002d1ff1e059c9894741575a5a8a1647c0a356e3e25de36482c4b5#7aa495490f2f7d3539f08ba2bf48f6320133913631c9b9a42436f733f037c105#g;
	s#candidate-Gate3-probe-disabled-1d69be03#gemian-a72-preiso-rollback-58e3efd5dcaa#g;
	s#DA921x probe-isolation candidate#Gemian A72 pre-isolation rollback candidate#g;
	s#2026-07-29-da921x-probe-isolation#2026-08-02-a72-pre-isolation-rollback-discriminator#g;
	s#\.gemini-probe-isolation#\.gemini-a72-rollback-override#g;
	s#probe-isolation#A72 pre-isolation rollback owner battery override#g;
	s#\(\( capacity >= 81 && capacity <= 100 \)\) \|\| fail '\''battery capacity is not above 80 percent'\''#(( capacity >= 70 && capacity <= 100 )) || fail '\''owner override still requires at least 70 percent battery'\''#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

grep -Fq 'EXPECTED_PREDECESSOR_SHA256=6dcbda0cb264f5b637f6333f4946707d81ea98d38a8d52673b6fbe2cf109e3af' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=6a180e5a62a00cd7c97d461c7a1c491cd47802bd0964ef82f75ee793d6b8bede' \
	"$derived" || die 'derived installer lacks exact candidate'
grep -Fq 'ARTIFACT_MANIFEST_SHA256=7aa495490f2f7d3539f08ba2bf48f6320133913631c9b9a42436f733f037c105' \
	"$derived" || die 'derived installer lacks exact manifest'
grep -Fq 'ARTIFACT_NAME=gemian-a72-preiso-rollback-58e3efd5dcaa' \
	"$derived" || die 'derived installer lacks exact artifact name'
grep -Fq "(( capacity >= 70 && capacity <= 100 )) || fail 'owner override still requires at least 70 percent battery'" \
	"$derived" || die 'derived installer lacks the exact narrowed owner override'
! grep -Fq 'capacity >= 81' "$derived" || die 'original battery threshold remains'
# shellcheck disable=SC2016
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
