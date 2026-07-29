#!/usr/bin/env bash

# Build the fixed-function Photon helper as a deterministic static AArch64 ELF.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
export SOURCE_DATE_EPOCH=0
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# -eq 2 ]] || die 'usage: build-photon-probe.sh SOURCE OUTPUT'
source_file=$1
output=$2
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] ||
	die 'run in the Linux AArch64 recovery VM'
for command in awk dirname gcc mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
[[ -f "$source_file" && ! -L "$source_file" && -s "$source_file" ]] ||
	die 'probe source is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] ||
	die 'refusing to overwrite probe output'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
[[ -d "$output_parent" && ! -L "$output_parent" ]] ||
	die 'probe output parent is unsafe'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="$script_dir/validate-photon-probe.py"
[[ -f "$validator" && ! -L "$validator" && -s "$validator" ]] ||
	die 'probe validator is missing or unsafe'

temporary="$(mktemp "$output_parent/.photon-probe.XXXXXX")"
cleanup() { [[ ! -f "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT
rm -f -- "$temporary"
gcc -std=c11 -Os -Wall -Wextra -Werror -pedantic -static -no-pie \
	-fno-ident -fno-asynchronous-unwind-tables -fno-unwind-tables \
	-Wl,--build-id=none -s -o "$temporary" "$source_file"
chmod 0755 "$temporary"
python3 "$validator" --source "$source_file" --binary "$temporary"
binary_sha256="$(sha256sum "$temporary" | awk '{print $1}')"
mv --no-clobber --no-target-directory "$temporary" "$output"
temporary=
trap - EXIT

printf 'validation=photon-probe-built\n'
printf 'compiler=%s\n' "$(gcc -dumpfullversion -dumpversion)"
printf 'binary_sha256=%s\n' "$binary_sha256"
printf 'arguments=none\ntransactions=6-read-only-register-pointer-reads\n'
printf 'receive_prefills=a1,b2,c3,d4,e5,f6\n'
printf 'complete_success_path_transfer_count=6\n'
printf 'post_equal_pre_does_not_stop=yes\n'
printf 'post_comparison=post-differs-pre-and-post-diff-mask\n'
printf 'device_access=none-at-build\nstorage_access=none\n'
