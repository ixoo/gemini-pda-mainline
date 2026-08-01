#!/usr/bin/env bash

# Source-pin and mechanically derive the exact bounded-listener candidate
# assembler from the validated no-listener delivery workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-uevent-no-listener-delivery/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=7705fa6310ce7c9f9ee4c92d9c2308c4b0bccf2ff655f06e8bdc98f6845e585a
[[ -f "$source_builder" && ! -L "$source_builder" &&
	"$(sha256sum "$source_builder" | awk '{print $1}')" == \
	"$SOURCE_BUILDER_SHA256" ]] || die 'source candidate builder changed'

derived="$(mktemp "${TMPDIR:-/tmp}/.derived-build-candidate.XXXXXXXX")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0700 "$derived"
perl -0pe '
	s#repo_root="\$\(cd -- "\$script_dir/\.\./\.\./\.\." && pwd -P\)"#repo_root="\${GEMINI_REPO_ROOT_OVERRIDE:?missing}"#g;
	s#e08571d98a3f0f394c68290b55eae6b63a6ae7e1ef15bb6e72c68cb960343ca1#e183216e2992421644078e016f5533cde8319eceaba49df3428215892d4fa05b#g;
	s#31f34f6582177b3c96fb2c1c2cfc18a8a38609b55b4a59554d7df3febb0fe7dc#61ac06f4f555d6ef78efde8cf264cbfb7434a8c7d78e7427c0608234d6f3303a#g;
	s#c82b5f4463e9956150a756ff85a89036465b3901e13a638f52347029fb76a0aa#7d07a967c6add93f1e32c0793299d6bede5c9b505282d9f68ff1f40b42c0efa0#g;
	s#3392d0dc48bae75e09acda0a74bcd75039274f41abda18d3f9030469f159c238#d8be44a706dec931eb64ac7a83392abb334f762e026c1619e3a8c0061402e875#g;
	s#gemini-mt6797-da921x-uevent-no-listener-delivery\.boot\.img#gemini-mt6797-da921x-uevent-bounded-listener.boot.img#g;
	s#7\.1\.3-gemini-da921x-nodeliv#7.1.3-gemini-da921x-boundlis#g;
	s#2026-07-31-da921x-uevent-no-listener-delivery#2026-08-01-da921x-uevent-bounded-listener#g;
	s#candidate-Gate3-da921x-nodeliv-#candidate-Gate3-da921x-boundlis-#g;
	s#da921x-uevent-no-listener-delivery-candidate#da921x-uevent-bounded-listener-candidate#g;
	s#gemini-nodeliv#gemini-boundlis#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_NO_LISTENER_DELIVERY_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_BOUNDED_LISTENER_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	e08571d98a3f0f394c68290b55eae6b63a6ae7e1ef15bb6e72c68cb960343ca1 \
	31f34f6582177b3c96fb2c1c2cfc18a8a38609b55b4a59554d7df3febb0fe7dc \
	c82b5f4463e9956150a756ff85a89036465b3901e13a638f52347029fb76a0aa \
	3392d0dc48bae75e09acda0a74bcd75039274f41abda18d3f9030469f159c238 \
	gemini-mt6797-da921x-uevent-no-listener-delivery.boot.img \
	7.1.3-gemini-da921x-nodeliv \
	2026-07-31-da921x-uevent-no-listener-delivery \
	candidate-Gate3-da921x-nodeliv- \
	validation=da921x-uevent-no-listener-delivery-candidate \
	gemini-nodeliv; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done

package=
previous=
for argument in "$@"; do
	if [[ "$previous" == --package ]]; then
		package=$argument
		break
	fi
	previous=$argument
done
[[ -n "$package" && -f "$package/kernel.config" ]] ||
	die 'exact package argument is required'
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_BOUNDED_LISTENER_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks bounded-listener gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
