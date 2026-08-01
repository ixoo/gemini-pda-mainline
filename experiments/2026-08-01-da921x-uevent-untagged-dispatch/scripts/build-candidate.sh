#!/usr/bin/env bash

# Source-pin and mechanically derive the exact untagged-dispatch candidate
# assembler from the validated single-multicast workflow.
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
source_builder="$repo_root/experiments/2026-08-01-da921x-uevent-single-multicast/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=7a244ca3a54c7b49b9e7cf65ef269474603e8efc46fcd85f17e05687550b961d
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
	s#985d6a8d3729d77fe44a481997212013c82ca44320cb0184966288c1539ce82d#6bac74cbe4f997ec874b7d72054acd6132d35f120b5505df08868e434a8cc126#g;
	s#79a602d7ad75789bdc05d6d2cb82aaa105766ad81e66d8cb946c2dd85e464f4e#1476e35697d41535cf6fe3b670cdecf1a3dda248b88549afe6f9afb050e984b3#g;
	s#9514ac0606ced57ee70418d1b7356fdca78347f88f8dfdeebef6a5a41779dd48#864a3ed384f4ae2ed7b67595189c0a5a016f843002e6d523e3dc38d84b2d94a7#g;
	s#14df73d9a42d7d4ad5cffb59ad92c38c3761318dd3f210f2404a1ca17cbb7319#3670e482ae6185018e7232af82004dbc61ea4936f0e794d9ec542cba92c15309#g;
	s#gemini-mt6797-da921x-uevent-single-multicast\.boot\.img#gemini-mt6797-da921x-uevent-untagged-dispatch.boot.img#g;
	s#7\.1\.3-gemini-da921x-mcast1#7.1.3-gemini-da921x-untag#g;
	s#2026-08-01-da921x-uevent-single-multicast#2026-08-01-da921x-uevent-untagged-dispatch#g;
	s#candidate-Gate3-da921x-mcast1-#candidate-Gate3-da921x-untag-#g;
	s#da921x-uevent-single-multicast-candidate#da921x-uevent-untagged-dispatch-candidate#g;
	s#gemini-mcast1#gemini-untag#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_SINGLE_MULTICAST_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_UNTAGGED_DISPATCH_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	985d6a8d3729d77fe44a481997212013c82ca44320cb0184966288c1539ce82d \
	79a602d7ad75789bdc05d6d2cb82aaa105766ad81e66d8cb946c2dd85e464f4e \
	9514ac0606ced57ee70418d1b7356fdca78347f88f8dfdeebef6a5a41779dd48 \
	14df73d9a42d7d4ad5cffb59ad92c38c3761318dd3f210f2404a1ca17cbb7319 \
	gemini-mt6797-da921x-uevent-single-multicast.boot.img \
	7.1.3-gemini-da921x-mcast1 \
	2026-08-01-da921x-uevent-single-multicast \
	candidate-Gate3-da921x-mcast1- \
	validation=da921x-uevent-single-multicast-candidate \
	gemini-mcast1; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_UNTAGGED_DISPATCH_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks untagged-dispatch gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
