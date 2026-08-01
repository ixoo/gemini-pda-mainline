#!/usr/bin/env bash

# Source-pin and mechanically derive the exact single-multicast candidate
# assembler from the validated bounded-listener workflow.
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
source_builder="$repo_root/experiments/2026-08-01-da921x-uevent-bounded-listener/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=515e66eaabe086f3ba5f3a23ab8f091f42112d8fff6529e06c96c8ebbc5f411a
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
	s#e183216e2992421644078e016f5533cde8319eceaba49df3428215892d4fa05b#985d6a8d3729d77fe44a481997212013c82ca44320cb0184966288c1539ce82d#g;
	s#61ac06f4f555d6ef78efde8cf264cbfb7434a8c7d78e7427c0608234d6f3303a#79a602d7ad75789bdc05d6d2cb82aaa105766ad81e66d8cb946c2dd85e464f4e#g;
	s#7d07a967c6add93f1e32c0793299d6bede5c9b505282d9f68ff1f40b42c0efa0#9514ac0606ced57ee70418d1b7356fdca78347f88f8dfdeebef6a5a41779dd48#g;
	s#d8be44a706dec931eb64ac7a83392abb334f762e026c1619e3a8c0061402e875#14df73d9a42d7d4ad5cffb59ad92c38c3761318dd3f210f2404a1ca17cbb7319#g;
	s#gemini-mt6797-da921x-uevent-bounded-listener\.boot\.img#gemini-mt6797-da921x-uevent-single-multicast.boot.img#g;
	s#7\.1\.3-gemini-da921x-boundlis#7.1.3-gemini-da921x-mcast1#g;
	s#2026-08-01-da921x-uevent-bounded-listener#2026-08-01-da921x-uevent-single-multicast#g;
	s#candidate-Gate3-da921x-boundlis-#candidate-Gate3-da921x-mcast1-#g;
	s#da921x-uevent-bounded-listener-candidate#da921x-uevent-single-multicast-candidate#g;
	s#gemini-boundlis#gemini-mcast1#g;
	s#CONFIG_I2C_GEMINI_DA921X_UEVENT_BOUNDED_LISTENER_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_UEVENT_SINGLE_MULTICAST_DIAGNOSTIC#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	e183216e2992421644078e016f5533cde8319eceaba49df3428215892d4fa05b \
	61ac06f4f555d6ef78efde8cf264cbfb7434a8c7d78e7427c0608234d6f3303a \
	7d07a967c6add93f1e32c0793299d6bede5c9b505282d9f68ff1f40b42c0efa0 \
	d8be44a706dec931eb64ac7a83392abb334f762e026c1619e3a8c0061402e875 \
	gemini-mt6797-da921x-uevent-bounded-listener.boot.img \
	7.1.3-gemini-da921x-boundlis \
	2026-08-01-da921x-uevent-bounded-listener \
	candidate-Gate3-da921x-boundlis- \
	validation=da921x-uevent-bounded-listener-candidate \
	gemini-boundlis; do
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
grep -qx 'CONFIG_I2C_GEMINI_DA921X_UEVENT_SINGLE_MULTICAST_DIAGNOSTIC=y' \
	"$package/kernel.config" || die 'package lacks single-multicast gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
