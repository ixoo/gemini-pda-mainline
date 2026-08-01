#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# no-listener delivery candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-uevent-listener-discovery/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=6d4bda180c637474ec4160beb4440c23995e1b440aea8d400e6c99319d35642e
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
	s{s\#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2\#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a\#g;}{s#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2#bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#g;}g;
	s{s\#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7\#64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec\#g;}{s#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;}g;
	s#CANDIDATE_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#CANDIDATE_SHA256=bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#g;
	s#EXPECTED_PREDECESSOR_SHA256=64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec#EXPECTED_PREDECESSOR_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;
	s#96aca7ebe8afa592adc02920ecf0f5582cf64937b984f293efcdd555a4c78b64#ce5f05bdea2d74a9e3d9d07764749dabea93a19ffa58c1aad4990aa9d4c3af0c#g;
	s#candidate-Gate3-da921x-listen-b9465ccf#candidate-Gate3-da921x-nodeliv-4c9a8600#g;
	s#DA921x uevent listener discovery#DA921x no-listener delivery#g;
	s#2026-07-31-da921x-uevent-listener-discovery#2026-07-31-da921x-uevent-no-listener-delivery#g;
	s#gemini-da921x-listen#gemini-da921x-nodeliv#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	96aca7ebe8afa592adc02920ecf0f5582cf64937b984f293efcdd555a4c78b64 \
	candidate-Gate3-da921x-listen-b9465ccf \
	2026-07-31-da921x-uevent-listener-discovery \
	gemini-da921x-listen; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 's#d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2#bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#g;' \
	"$derived" || die 'derived installer lacks exact candidate mapping'
grep -Fq 's#1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;' \
	"$derived" || die 'derived installer lacks exact predecessor mapping'
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
