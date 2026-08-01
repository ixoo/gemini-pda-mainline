#!/usr/bin/env bash

# Derive and build the exact static ARM64 normal-fallthrough listener in the
# managed VM from the runtime-proven stage-23 listener source.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7a900075db323e7000f15fcbb44602b26068e7546d68ae65c1032fb7d069ff0b
readonly DERIVED_SOURCE_SHA256=c5f1cdb6d7e5cf8a1621c3fa13a4e7c6e529ec766949acb3cc915bd024c64c60

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$#" -eq 2 && "$1" == --output ]] ||
	die "usage: $0 --output /home/USER/artifacts/gemini-pda/runtime-tools/NEW-FILE"
output=$2
for command in aarch64-linux-gnu-gcc awk chmod dirname mktemp perl rm \
	sha256sum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_file="$repo_root/experiments/2026-08-01-da921x-uevent-untagged-dispatch/listener/untagged-dispatch-listener.c"
[[ -f "$source_file" && ! -L "$source_file" ]] || die 'listener source is unsafe'
[[ "$(sha256sum "$source_file" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'listener source changed'
case "$output" in "$HOME"/artifacts/gemini-pda/runtime-tools/*) ;; *) die 'output is outside the managed runtime-tools directory' ;; esac
[[ "$output" != *$'\n'* && ! -e "$output" && ! -L "$output" ]] || die 'output must be one new safe path'
parent="$(dirname -- "$output")"
[[ -d "$parent" && ! -L "$parent" && "$(stat -c '%a' "$parent")" == 700 ]] || die 'runtime-tools directory is absent or unsafe'

derived="$(mktemp "$parent/.normal-fallthrough-listener.XXXXXXXX.c")"
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT
chmod 0600 "$derived"
perl -0pe '
	s#gemini_da921x_uevent_untagged_dispatch#gemini_da921x_uevent_normal_fallthrough#g;
	s#attempts=0 entries=0 returns=0 baseline_sockets=-1 sockets=-1 listeners=-1 allocations=-1 broadcasts=-1 retval=-1#attempts=0 callsite_entries=0 callsite_returns=0 public_returns=0 retval=-1#g;
	s#attempts=1 entries=1 returns=1 baseline_sockets=1 sockets=1 listeners=1 allocations=1 broadcasts=1 retval=0#attempts=1 callsite_entries=1 callsite_returns=1 public_returns=1 retval=0#g;
	s#untagged_dispatch_result#normal_fallthrough_result#g;
	s#"22\\n", "pre-stage"#"24\\n", "pre-stage"#g;
	s#"23\\n", "post-stage"#"25\\n", "post-stage"#g;
' "$source_file" >"$derived"
[[ "$(sha256sum "$derived" | awk '{print $1}')" == "$DERIVED_SOURCE_SHA256" ]] || die 'derived listener source identity mismatch'

aarch64-linux-gnu-gcc -std=c11 -Os -static -s -fno-ident \
	-fno-asynchronous-unwind-tables -fno-unwind-tables \
	-Wall -Wextra -Werror -Wl,--build-id=none -o "$output" "$derived"
[[ "$(stat -c '%a' "$output")" == 700 ]] || chmod 0700 "$output"
printf 'listener=%s\nderived_source_sha256=%s\nlistener_sha256=%s\nlistener_size=%s\n' \
	"$output" "$DERIVED_SOURCE_SHA256" \
	"$(sha256sum "$output" | awk '{print $1}')" "$(stat -c '%s' "$output")"
