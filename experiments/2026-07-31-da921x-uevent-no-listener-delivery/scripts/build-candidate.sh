#!/usr/bin/env bash

# Source-pin and mechanically derive the exact no-listener delivery candidate
# assembler from the validated uevent-listener discovery workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-uevent-listener-discovery/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=eaaaca35713b8c4a22941af555a54674ad1925ccb9dd5caa26a38cad8a684d77
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
	s#c01521d725e39f7384efa43b9287b5623f1378f72c3559c2279d48ba4420f035#e08571d98a3f0f394c68290b55eae6b63a6ae7e1ef15bb6e72c68cb960343ca1#g;
	s#1c18061416f0ec1d2a281c6bd94bcdb076dbd9e2748b8c6f89fbd934bd6c65f1#31f34f6582177b3c96fb2c1c2cfc18a8a38609b55b4a59554d7df3febb0fe7dc#g;
	s#d9c493efb68e4fcdbf49eff4f29ff1b18fb7f779999af230cb8e71d307cada4f#c82b5f4463e9956150a756ff85a89036465b3901e13a638f52347029fb76a0aa#g;
	s#75b333ba0ca0b5bede5c247f0dfcff5b6a145450a191ed6e7ad5e087a0e66615#3392d0dc48bae75e09acda0a74bcd75039274f41abda18d3f9030469f159c238#g;
	s#gemini-mt6797-da921x-uevent-listener-discovery\.boot\.img#gemini-mt6797-da921x-uevent-no-listener-delivery.boot.img#g;
	s#7\.1\.3-gemini-da921x-listen#7.1.3-gemini-da921x-nodeliv#g;
	s#2026-07-31-da921x-uevent-listener-discovery#2026-07-31-da921x-uevent-no-listener-delivery#g;
	s#candidate-Gate3-da921x-listen-#candidate-Gate3-da921x-nodeliv-#g;
	s#da921x-uevent-listener-discovery-candidate#da921x-uevent-no-listener-delivery-candidate#g;
	s#gemini-listen#gemini-nodeliv#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_LISTENER_DISCOVERY_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_NO_LISTENER_DELIVERY_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	c01521d725e39f7384efa43b9287b5623f1378f72c3559c2279d48ba4420f035 \
	1c18061416f0ec1d2a281c6bd94bcdb076dbd9e2748b8c6f89fbd934bd6c65f1 \
	d9c493efb68e4fcdbf49eff4f29ff1b18fb7f779999af230cb8e71d307cada4f \
	75b333ba0ca0b5bede5c247f0dfcff5b6a145450a191ed6e7ad5e087a0e66615 \
	gemini-mt6797-da921x-uevent-listener-discovery.boot.img \
	7.1.3-gemini-da921x-listen \
	2026-07-31-da921x-uevent-listener-discovery \
	candidate-Gate3-da921x-listen- \
	validation=da921x-uevent-listener-discovery-candidate \
	gemini-listen; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_NO_LISTENER_DELIVERY_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks no-listener delivery gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
