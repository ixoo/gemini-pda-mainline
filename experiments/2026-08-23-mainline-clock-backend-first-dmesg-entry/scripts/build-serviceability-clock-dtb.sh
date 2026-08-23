#!/usr/bin/env bash

# Derive the runtime-proven serviceability DT twice, then enable only the
# read-free clock-backend node and require byte-identical results.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f961ae4967746ddbdf85d372ef26b595cdd20bacbda0b10d975afd20be0e8140
readonly BASE_DTB_SHA256=dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e
readonly SERVICEABILITY_DTB_SHA256=b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd
readonly OUTPUT_DTB_SHA256=7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100
readonly CLOCK_BACKEND=/dvfsp-clock-backend@1001a000
readonly BIGIDVFSP_BACKEND=/dvfsp-bigidvfs-backend
readonly RAM_CONSOLE=/ram-console

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --base-dtb FILE --output FILE\n' "$0"; }

base_dtb=
output=
while (($#)); do
	case "$1" in
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$base_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk bash chmod cmp dirname dtc fdtget fdtput grep mkdir mktemp \
	mv rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
[[ "$(sha256sum "$base_dtb" | awk '{print $1}')" == "$BASE_DTB_SHA256" ]] ||
	die 'current package DTB identity changed'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-22-mainline-first-dmesg-raw-write-qualification/scripts/build-serviceability-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

mkdir -p -- "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.clock-entry-dtb.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM

for replica in a b; do
	serviceability="$workdir/serviceability-$replica.dtb"
	clock="$workdir/clock-$replica.dtb"
	/bin/bash "$source_builder" --base-dtb "$base_dtb" --output "$serviceability" >/dev/null
	[[ "$(sha256sum "$serviceability" | awk '{print $1}')" == "$SERVICEABILITY_DTB_SHA256" ]] ||
		die 'serviceability DT identity changed'
	mv "$serviceability" "$clock"
	fdtput -ts "$clock" "$CLOCK_BACKEND" status okay
	dtc -q -I dtb -O dtb -o /dev/null "$clock"
	[[ "$(fdtget -ts "$clock" "$CLOCK_BACKEND" status)" == okay ]] ||
		die 'clock backend was not enabled'
	[[ "$(fdtget -ts "$clock" "$BIGIDVFSP_BACKEND" status)" == disabled ]] ||
		die 'BigiDVFS backend closure changed'
	[[ "$(fdtget -ts "$clock" "$RAM_CONSOLE" status)" == disabled ]] ||
		die 'ram-console closure changed'
	[[ -z "$(fdtget -l "$clock" / | grep 'protected-readback' || true)" ]] ||
		die 'protected-readback observer returned'
	[[ "$(sha256sum "$clock" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
		die 'derived clock DT identity changed'
done
cmp -s "$workdir/clock-a.dtb" "$workdir/clock-b.dtb" ||
	die 'independent DT derivations differ'
mv "$workdir/clock-a.dtb" "$output"
chmod 0600 "$output"
rm -f -- "$workdir/clock-b.dtb"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM

printf 'validation=clock-backend-first-dmesg-serviceability-dtb\n'
printf 'base_dtb_sha256=%s\nserviceability_dtb_sha256=%s\n' \
	"$BASE_DTB_SHA256" "$SERVICEABILITY_DTB_SHA256"
printf 'output_dtb_sha256=%s\nindependent_derivations=byte-identical\n' \
	"$OUTPUT_DTB_SHA256"
printf 'dtb_delta=clock-backend-status-okay-only\n'
printf 'bigidvfs_backend_status=disabled\nprotected_observer=absent\n'
printf 'CPU8_CPU9_admission=closed\ndevice_access=none\nhardware_write=none\nresult=pass\n'
