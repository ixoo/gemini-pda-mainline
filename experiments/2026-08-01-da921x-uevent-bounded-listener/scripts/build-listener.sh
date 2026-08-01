#!/usr/bin/env bash

# Build the exact static ARM64 runtime listener in the managed VM.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b2f08e5a0cbf063a00f1d646e1ae568d3f3ee279bdeb8e6838e28d977c167e9a

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$#" -eq 2 && "$1" == --output ]] ||
	die "usage: $0 --output /home/USER/artifacts/gemini-pda/runtime-tools/NEW-FILE"
output=$2
for command in aarch64-linux-gnu-gcc awk dirname readlink sha256sum stat; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_file="$(cd -- "$script_dir/../listener" && pwd -P)/bounded-listener.c"
[[ -f "$source_file" && ! -L "$source_file" ]] || die 'listener source is unsafe'
[[ "$(sha256sum "$source_file" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'listener source changed'
case "$output" in
"$HOME"/artifacts/gemini-pda/runtime-tools/*) ;;
*) die 'output is outside the managed runtime-tools directory' ;;
esac
[[ "$output" != *$'\n'* && ! -e "$output" && ! -L "$output" ]] ||
	die 'output must be one new safe path'
parent="$(dirname -- "$output")"
[[ -d "$parent" && ! -L "$parent" && "$(stat -c '%a' "$parent")" == 700 ]] ||
	die 'runtime-tools directory is absent or unsafe'

aarch64-linux-gnu-gcc -std=c11 -Os -static -s -fno-ident \
	-fno-asynchronous-unwind-tables -fno-unwind-tables \
	-Wall -Wextra -Werror -Wl,--build-id=none \
	-o "$output" "$source_file"
[[ "$(stat -c '%a' "$output")" == 700 ]] || chmod 0700 "$output"
printf 'listener=%s\nlistener_sha256=%s\nlistener_size=%s\n' \
	"$output" "$(sha256sum "$output" | awk '{print $1}')" \
	"$(stat -c '%s' "$output")"
