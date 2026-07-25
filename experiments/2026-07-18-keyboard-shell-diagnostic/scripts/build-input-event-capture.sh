#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
[[ $# -eq 1 ]] || die "usage: build-input-event-capture.sh OUTPUT"
output=$1
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_file="${script_dir}/../src/input-event-capture.c"
[[ -s "$source_file" ]] || die "input helper source is missing"
mkdir -p "$(dirname -- "$output")"
gcc -std=gnu11 -O2 -Wall -Wextra -Werror -pedantic -static \
	-Wl,--build-id=none -o "$output" "$source_file"
file "$output" | grep -Fq 'ARM aarch64' || die "helper is not AArch64"
file "$output" | grep -Fq 'statically linked' || die "helper is not static"
if readelf -lW "$output" | grep -q ' INTERP '; then
	die "helper unexpectedly contains PT_INTERP"
fi
chmod 0755 "$output"
printf 'output=%s\nsha256=%s\nstatic=yes\npt_interp=no\neviocgrab=no\n' \
	"$output" "$(sha256sum "$output" | awk '{print $1}')"
