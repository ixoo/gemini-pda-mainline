#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# uevent listener-discovery candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-netlink-skb-serialization/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=c12d92bda1074558f173d98196f0423d70c08d3ab956038f4018467608d0a95a
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
	s{s\#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2\#64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec\#g;}{s#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;}g;
	s{s\#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7\#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2\#g;}{s#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#g;}g;
	s#CANDIDATE_SHA256=64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#CANDIDATE_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;
	s#EXPECTED_PREDECESSOR_SHA256=d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2#EXPECTED_PREDECESSOR_SHA256=64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#g;
	s#bfee2ba15d7d5015fd829d21bb2b31fc51fdd9605af6fb74e298bb1b8dd6d65b#96aca7ebe8afa592adc02920ecf0f5582cf64937b984f293efcdd555a4c78b64#g;
	s#candidate-Gate3-da921x-skbser-28dd17db#candidate-Gate3-da921x-listen-b9465ccf#g;
	s#DA921x netlink skb serialization#DA921x uevent listener discovery#g;
	s#2026-07-31-da921x-netlink-skb-serialization#2026-07-31-da921x-uevent-listener-discovery#g;
	s#gemini-da921x-skbser#gemini-da921x-listen#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	bfee2ba15d7d5015fd829d21bb2b31fc51fdd9605af6fb74e298bb1b8dd6d65b \
	candidate-Gate3-da921x-skbser-28dd17db \
	2026-07-31-da921x-netlink-skb-serialization \
	gemini-da921x-skbser; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 's#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;' \
	"$derived" || die 'derived installer lacks exact candidate mapping'
grep -Fq 's#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#g;' \
	"$derived" || die 'derived installer lacks exact predecessor mapping'
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
