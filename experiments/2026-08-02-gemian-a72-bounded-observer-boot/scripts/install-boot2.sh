#!/usr/bin/env bash

# Source-pin and mechanically derive the exact guarded boot2 installer for the
# bounded Gemian A72 owner observer.
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
source_installer="$repo_root/experiments/2026-07-29-da921x-probe-isolation/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == \
	"$SOURCE_INSTALLER_SHA256" ]] || die 'source boot2 installer changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-a72-observer-installer.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#c9ea62bccb9ac3caedd8e6a77986a81cbb1e83fbaa329be4f6433cfb4da47b6e#805c3c1ce28131847924679a70186a75d277da3ab2be9565cea02bf546150f28#g;
	s#b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa#33ace2c30a8877be2a4b917135aa994ad718201f98ec36d8506a3b1f1d03a7aa#g;
	s#b66ff99853002d1ff1e059c9894741575a5a8a1647c0a356e3e25de36482c4b5#880fa678eff2641a1559e65aef1f6904d608a49507285e3ef77de884bc21098c#g;
	s#candidate-Gate3-probe-disabled-1d69be03#gemian-a72-bounded-observer-d3ec1e13123e#g;
	s#DA921x probe-isolation candidate#bounded Gemian A72 owner-observer candidate#g;
	s#2026-07-29-da921x-probe-isolation#2026-08-02-gemian-a72-bounded-observer-boot#g;
	s#\.gemini-probe-isolation#\.gemini-a72-observer#g;
	s#probe-isolation#bounded A72 observer#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"

for stale in \
	c9ea62bccb9ac3caedd8e6a77986a81cbb1e83fbaa329be4f6433cfb4da47b6e \
	b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa \
	b66ff99853002d1ff1e059c9894741575a5a8a1647c0a356e3e25de36482c4b5 \
	candidate-Gate3-probe-disabled-1d69be03 \
	2026-07-29-da921x-probe-isolation \
	.gemini-probe-isolation; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=805c3c1ce28131847924679a70186a75d277da3ab2be9565cea02bf546150f28' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=33ace2c30a8877be2a4b917135aa994ad718201f98ec36d8506a3b1f1d03a7aa' \
	"$derived" || die 'derived installer lacks exact candidate'
grep -Fq 'ARTIFACT_MANIFEST_SHA256=880fa678eff2641a1559e65aef1f6904d608a49507285e3ef77de884bc21098c' \
	"$derived" || die 'derived installer lacks exact manifest'
grep -Fq 'ARTIFACT_NAME=gemian-a72-bounded-observer-d3ec1e13123e' \
	"$derived" || die 'derived installer lacks exact artifact name'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
