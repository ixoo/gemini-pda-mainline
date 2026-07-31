#!/usr/bin/env bash

# Derive the exact guarded installer from the source-pinned module candidate
# installer, changing only calibrated artifact identities and record labels.
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
source_installer="$repo_root/experiments/2026-07-29-da921x-post-serviceability-module/scripts/install-boot2.sh"
readonly SOURCE_INSTALLER_SHA256=a16efb0b27ce19d954cf23f278cec3ec367150fce8f5911dad9368da343b2f1d
[[ -f "$source_installer" && ! -L "$source_installer" &&
	"$(sha256sum "$source_installer" | awk '{print $1}')" == \
	"$SOURCE_INSTALLER_SHA256" ]] || die 'source installer changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s/86b0efaa2beafa97bd6382ec457508d0b516dab813d6ebbe8b1b7de1f4f88f17/fc17b54c7b107f92297fd6715c0c2ec3b322ae79ef322b00ae8cacb332735d5e/g;
	s/b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa/f89eb0ed2608a9e6a90ad939686c06d26d7420ae2c29854ada6a836fac823377/g;
	s/de2e73daee85a8741489c74b1e8b05771ddda9d6c56c92163825aa23987831f5/d1ecf11860a2e33a4a3a8a74f53b1646e9bd67017a6efc4ea694d1f588a99db4/g;
	s/candidate-Gate3-da921x-module-b57766ab/candidate-Gate3-da921x-name-only-client-e8d29991/g;
	s/2026-07-29-da921x-post-serviceability-module/2026-07-30-da921x-name-only-client/g;
	s/post-serviceability-module/name-only-client/g;
' "$source_installer" >"$derived"
chmod 0700 "$derived"
for stale in \
	86b0efaa2beafa97bd6382ec457508d0b516dab813d6ebbe8b1b7de1f4f88f17 \
	b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa \
	de2e73daee85a8741489c74b1e8b05771ddda9d6c56c92163825aa23987831f5 \
	candidate-Gate3-da921x-module-b57766ab \
	2026-07-29-da921x-post-serviceability-module \
	post-serviceability-module; do
	! grep -Fq "$stale" "$derived" || die "derived installer retained $stale"
done
status=0
"$derived" "$@" || status=$?
exit "$status"
