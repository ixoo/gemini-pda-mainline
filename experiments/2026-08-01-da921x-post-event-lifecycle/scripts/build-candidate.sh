#!/usr/bin/env bash

# Source-pin and mechanically derive the exact post-event lifecycle candidate
# assembler from a validated direct module-free candidate workflow.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-of-modalias-pre-dispatch-suppression/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=751ceab618e58da84a6111ab037560e35ce3fa1d230acdb1fe71d38c9eac331b
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
	s#9462d48c8240a656155dc36f1acb5b3a572e7f913847ba8310f396c4ed1345ae#4a1be374e5eaa57017ae986a70684df48cf692752e737dea5050d171d6440afa#g;
	s#288a532de2ac512a1c95e5cf1b4ecfed3bd7a271305cc9abdb528d447872993e#f655beba038ad5d98f3af5897fb080329d45781b637ab7dcb409e8a353c54440#g;
	s#cb77083d4cff000cec37b1e64dad41e701a1ebae614d724f6fd3b51ed451f169#1fa07344f9882b5039b983ec3a3cb25b4a94c17027bc2dc71db35c2b0ea5f5ac#g;
	s#524f65d3e16066a9e77aca046c803e06ce24b9a32b0cdcc1e5b051b91fbb4757#1c0469564bd4cb52be2cfe32871cd864ecc0e76945ef6c18057966612f4e143d#g;
	s#gemini-mt6797-da921x-of-modalias-pre-dispatch-suppression\.boot\.img#gemini-mt6797-da921x-post-event-lifecycle.boot.img#g;
	s#7\.1\.3-gemini-da921x-ofpredispatch#7.1.3-gemini-da921x-life27#g;
	s#CONFIG_REGULATOR_DA9213_LEGACY=m#CONFIG_REGULATOR_DA9213_LEGACY=y#g;
	s#DA921x driver is not a module#DA921x identification driver is not built in#g;
	s#CONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_PRE_DISPATCH_SUPPRESSION_DIAGNOSTIC#CONFIG_I2C_GEMINI_DA921X_NATURAL_DEVICE_ADD_DIAGNOSTIC#g;
	s#pre-dispatch diagnostic is not enabled#natural-device-add diagnostic is not enabled#g;
	s#\.da921x-ofpredispatch-candidate#\.da921x-life27-candidate#g;
	s#gemini-ofpre#gemini-life27#g;
	s#2026-07-31-da921x-of-modalias-pre-dispatch-suppression#2026-08-01-da921x-post-event-lifecycle#g;
	s#kernel_profile=da921x-of-modalias-pre-dispatch-suppression#kernel_profile=da921x-post-event-lifecycle#g;
	s#candidate-Gate3-da921x-ofpredispatch-#candidate-Gate3-da921x-life27-#g;
	s#da921x-of-modalias-pre-dispatch-suppression-candidate#da921x-post-event-lifecycle-candidate#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	9462d48c8240a656155dc36f1acb5b3a572e7f913847ba8310f396c4ed1345ae \
	288a532de2ac512a1c95e5cf1b4ecfed3bd7a271305cc9abdb528d447872993e \
	cb77083d4cff000cec37b1e64dad41e701a1ebae614d724f6fd3b51ed451f169 \
	524f65d3e16066a9e77aca046c803e06ce24b9a32b0cdcc1e5b051b91fbb4757 \
	gemini-mt6797-da921x-of-modalias-pre-dispatch-suppression.boot.img \
	7.1.3-gemini-da921x-ofpredispatch \
	CONFIG_REGULATOR_DA9213_LEGACY=m \
	CONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_PRE_DISPATCH_SUPPRESSION_DIAGNOSTIC \
	gemini-ofpre \
	2026-07-31-da921x-of-modalias-pre-dispatch-suppression \
	candidate-Gate3-da921x-ofpredispatch- \
	validation=da921x-of-modalias-pre-dispatch-suppression-candidate; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
grep -Fq 'CONFIG_REGULATOR_DA9213_LEGACY=y' "$derived" ||
	die 'derived builder lacks built-in driver gate'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
