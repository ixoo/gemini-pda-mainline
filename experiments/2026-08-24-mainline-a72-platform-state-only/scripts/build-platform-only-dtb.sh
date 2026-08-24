#!/usr/bin/env bash

# Derive the exact platform-state-only DTB twice from the physical-source DTB.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=fe67420ca4e2955a73a4a3f2e442af3534b621820cf77ae035be9bf98756425d
readonly OUTPUT_SHA256=8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1
readonly OUTPUT_SIZE=27710
readonly OUTPUT_FILE=mt6797-gemini-pda-a72-platform-only.dtb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --input-dtb FILE --output-parent DIR\n' "$0" >&2; }

input=
output_parent=
while (($#)); do
	case "$1" in
	--input-dtb) input=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$input" && -n "$output_parent" ]] || { usage; exit 2; }
for command in awk chmod cmp cp fdtget fdtput find git mkdir mktemp mv rm sha256sum sort wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
input=$(cd -- "$(dirname -- "$input")" && pwd -P)/$(basename -- "$input")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output must remain below artifacts' ;; esac
[[ -f "$input" && ! -L "$input" ]] || die 'input DTB is missing or unsafe'
[[ "$(sha256sum "$input" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source DTB changed'

workdir=$(mktemp -d "$output_parent/.a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
mkdir "$workdir/first" "$workdir/second"
for root in "$workdir/first" "$workdir/second"; do
	cp "$input" "$root/$OUTPUT_FILE"
	fdtput -t s "$root/$OUTPUT_FILE" /dvfsp-clock-backend@1001a000 status disabled
	fdtput -t s "$root/$OUTPUT_FILE" /dvfsp-bigidvfs-backend status disabled
	fdtput -t s "$root/$OUTPUT_FILE" /a72-physical-source-observer status disabled
done
cmp -s "$workdir/first/$OUTPUT_FILE" "$workdir/second/$OUTPUT_FILE" ||
	die 'independent DT derivations differ'

dtb="$workdir/first/$OUTPUT_FILE"
[[ "$(sha256sum "$dtb" | awk '{print $1}')" == "$OUTPUT_SHA256" ]] || die 'derived DTB identity changed'
[[ "$(wc -c <"$dtb" | tr -d ' ')" == "$OUTPUT_SIZE" ]] || die 'derived DTB size changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-state@10222000 status)" == okay ]] || die 'platform source is not enabled'
[[ "$(fdtget -t s "$dtb" /dvfsp-clock-backend@1001a000 status)" == disabled ]] || die 'clock backend is not disabled'
[[ "$(fdtget -t s "$dtb" /dvfsp-bigidvfs-backend status)" == disabled ]] || die 'BigiDVFS backend is not disabled'
[[ "$(fdtget -t s "$dtb" /a72-physical-source-observer status)" == disabled ]] || die 'observer is not disabled'

{
	printf 'experiment=2026-08-24-mainline-a72-platform-state-only\n'
	printf 'source_dtb_sha256=%s\nderived_dtb_sha256=%s\n' "$SOURCE_SHA256" "$OUTPUT_SHA256"
	printf 'changed_properties=3\na72_platform_state=okay\n'
	printf 'dvfsp_clock_backend=disabled\ndvfsp_bigidvfs_backend=disabled\n'
	printf 'physical_source_observer=disabled\nregister_data_writes=0\n'
	printf 'protected_calls=0\ncpu_requests=0\nresult=pass\n'
} >"$workdir/first/provenance.txt"
manifest="$workdir/SHA256SUMS"
(
	cd "$workdir/first"
	find . -type f -print0 | sort -z | xargs -0 sha256sum
) >"$manifest"
mv "$manifest" "$workdir/first/SHA256SUMS"
(
	cd "$workdir/first"
	sha256sum --check --strict SHA256SUMS >/dev/null
)
chmod 0600 "$workdir/first"/*
output="$output_parent/dtb-a72-platform-state-only-${OUTPUT_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$workdir/first" "$output"
rm -rf "$workdir/second"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-platform-state-only-dtb\nartifact=%s\ndtb_sha256=%s\n' "$output" "$OUTPUT_SHA256"
printf 'device_access=none\nhardware_write=none\n'
