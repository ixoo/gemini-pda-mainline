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
for command in awk chmod dirname file gcc grep mkdir readelf sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_file="${script_dir}/../src/input-event-capture.c"
[[ -s "$source_file" ]] || die "input helper source is missing"
grep -Fqx '#define CAPTURE_SECONDS 15' "$source_file" || \
	die "helper capture bound is not exactly 15 seconds"
grep -Fq 'deadline.tv_sec += CAPTURE_SECONDS;' "$source_file" || \
	die "helper lacks an absolute monotonic deadline"
mkdir -p "$(dirname -- "$output")"
gcc -std=gnu11 -O2 -Wall -Wextra -Werror -pedantic -static \
	-Wl,--build-id=none -o "$output" "$source_file"
file_identity="$(file "$output")"
[[ "$file_identity" == *'ARM aarch64'* ]] || die "helper is not AArch64"
[[ "$file_identity" == *'statically linked'* ]] || die "helper is not static"
if readelf -lW "$output" | grep ' INTERP ' >/dev/null; then
	die "helper unexpectedly contains PT_INTERP"
fi
chmod 0755 "$output"
printf 'sha256=%s\nstatic=yes\npt_interp=no\neviocgrab=no\n' \
	"$(sha256sum "$output" | awk '{print $1}')"
printf 'capture_seconds=15\ndevice_selection=required-exact-event-argument\n'
printf 'identity_anchor=matrix-platform-sysfs\nname_revalidation=exact-EVIOCGNAME-match\n'
