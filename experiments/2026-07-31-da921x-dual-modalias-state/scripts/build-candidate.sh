#!/usr/bin/env bash

# Source-pin and mechanically derive the exact dual-modalias candidate
# assembler for the no-printk read-only-state kernel.
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
source_builder="$repo_root/experiments/2026-07-31-da921x-dual-modalias-pre-dispatch-suppression/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=7299bc9bea8ecdf68f9bd9112eb6843cc3ceab9a10d3ad86465c792cc4656382
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
	s#f43e65ebdf7be3e94f006235f1230f996dbfb6ef55db3cd3471455f3c103c21e#b6c43d9824685b8dcd764a2261c8fb8568e7ee723031f7c8e9a30be2bd3574da#g;
	s#96bb06d56eb4034ff59909fa205675d834241a7eec9bbdd6a86b5719fc39a23f#779ededc15cec4a6204d399299ff1476591de2e8297fbfe098c273e225180380#g;
	s#4a0582b9522e4bb890b423e8b061da8a320dca8ed766570fbee0e7c22eaf4e67#a280506dfbe9ae3ecadafc26cf7e6e4fd3ab9d504e1b69a1edf40684d89bca88#g;
	s#22a4491c7c830ad443ec671fb93f17e3c0e3155e79938e6b2a45b0f0050c2a02#fd9f76342305a80929194a2e8d9442925bbf3b2e4e6804b8d5266aa4c406732a#g;
	s#gemini-mt6797-da921x-dual-modalias-pre-dispatch-suppression\.boot\.img#gemini-mt6797-da921x-dual-modalias-state.boot.img#g;
	s#7\.1\.3-gemini-da921x-dualpre#7.1.3-gemini-da921x-dualstate#g;
	s#2026-07-31-da921x-dual-modalias-pre-dispatch-suppression#2026-07-31-da921x-dual-modalias-state#g;
	s#candidate-Gate3-da921x-dualpre-#candidate-Gate3-da921x-dualstate-#g;
	s#da921x-dual-modalias-pre-dispatch-suppression-candidate#da921x-dual-modalias-state-candidate#g;
	s#gemini-dualpre#gemini-dstate#g;
	s#CONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_PRE_DISPATCH_SUPPRESSION_DIAGNOSTIC=y#CONFIG_I2C_GEMINI_DA921X_DUAL_MODALIAS_STATE_DIAGNOSTIC=y#g;
	s#(\tCONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_REAL_ENV_ROLLBACK_DIAGNOSTIC); do#$1 \\\n\tCONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_PRE_DISPATCH_SUPPRESSION_DIAGNOSTIC; do#g;
' "$source_builder" >"$derived"
chmod 0700 "$derived"
for stale in \
	f43e65ebdf7be3e94f006235f1230f996dbfb6ef55db3cd3471455f3c103c21e \
	96bb06d56eb4034ff59909fa205675d834241a7eec9bbdd6a86b5719fc39a23f \
	4a0582b9522e4bb890b423e8b061da8a320dca8ed766570fbee0e7c22eaf4e67 \
	22a4491c7c830ad443ec671fb93f17e3c0e3155e79938e6b2a45b0f0050c2a02 \
	gemini-mt6797-da921x-dual-modalias-pre-dispatch-suppression.boot.img \
	7.1.3-gemini-da921x-dualpre \
	2026-07-31-da921x-dual-modalias-pre-dispatch-suppression \
	candidate-Gate3-da921x-dualpre- \
	validation=da921x-dual-modalias-pre-dispatch-suppression-candidate \
	gemini-dualpre; do
	! grep -Fq "$stale" "$derived" || die "derived builder retained $stale"
done
grep -Fq 'CONFIG_I2C_GEMINI_DA921X_DUAL_MODALIAS_STATE_DIAGNOSTIC=y' \
	"$derived" || die 'derived builder lacks state diagnostic gate'
grep -Fq 'CONFIG_I2C_GEMINI_DA921X_OF_MODALIAS_PRE_DISPATCH_SUPPRESSION_DIAGNOSTIC; do' \
	"$derived" || die 'derived builder lacks predecessor-symbol rejection'
# shellcheck disable=SC2016 # Require the literal deferred expansion.
grep -Fq 'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' "$derived" ||
	die 'derived builder lacks explicit repository root'
export GEMINI_REPO_ROOT_OVERRIDE="$repo_root"
status=0
"$derived" "$@" || status=$?
exit "$status"
