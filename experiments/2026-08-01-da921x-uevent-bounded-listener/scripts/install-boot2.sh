#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded boot2 installer for the
# bounded-listener candidate.
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
source_installer="$repo_root/experiments/2026-07-31-da921x-uevent-no-listener-delivery/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=38934dd53e2947390d963470b43cb2a9f1d06db3ff12af880dde1408e84de880
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
	s!\Q\#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a\#g;}\E!\#__KEEP_2DD__\#g;}!g;
	s!CANDIDATE_SHA256=2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a\#!CANDIDATE_SHA256=__KEEP_2DD__\#!g;
	s#bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#e1327619295ab7d739ebd76dbf31ac91691ad91ca086acb34728dbf69a1e54e5#g;
	s#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0#g;
	s#__KEEP_2DD__#2dd4908ba4f65785a536b079f08c87fe096c6ed490ddc3294743c5b0d515576a#g;
	s#ce5f05bdea2d74a9e3d9d07764749dabea93a19ffa58c1aad4990aa9d4c3af0c#09f3bf3bfc9e698d9a84a985b9fb65b00c273413669c5280599b266969715d43#g;
	s#candidate-Gate3-da921x-nodeliv-4c9a8600#candidate-Gate3-da921x-boundlis-e668a5ff#g;
	s#DA921x no-listener delivery#DA921x bounded listener#g;
	s#2026-07-31-da921x-uevent-no-listener-delivery#2026-08-01-da921x-uevent-bounded-listener#g;
	s#gemini-da921x-nodeliv#gemini-da921x-boundlis#g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	ce5f05bdea2d74a9e3d9d07764749dabea93a19ffa58c1aad4990aa9d4c3af0c \
	candidate-Gate3-da921x-nodeliv-4c9a8600 \
	2026-07-31-da921x-uevent-no-listener-delivery \
	gemini-da921x-nodeliv; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
grep -Fq 'EXPECTED_PREDECESSOR_SHA256=bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0' \
	"$derived" || die 'derived installer lacks exact predecessor'
grep -Fq 'CANDIDATE_SHA256=e1327619295ab7d739ebd76dbf31ac91691ad91ca086acb34728dbf69a1e54e5' \
	"$derived" || die 'derived installer lacks exact candidate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived installer lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
