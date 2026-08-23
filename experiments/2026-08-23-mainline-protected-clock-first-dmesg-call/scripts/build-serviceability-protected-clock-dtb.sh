#!/usr/bin/env bash

# Reproduce the runtime-proven serviceability/clock DT and add only the
# one-shot observer. BigiDVFS remains disabled; its phandle is descriptive and
# is not consumed by the raw-entry observer mode.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=344f59b2aba315fd342af564f033c5cea372bf9d05a2f2c00550bc5e03e5de05
readonly BASE_DTB_SHA256=0a6b7c72dc1182e69d377c38be7d412c225b523b9a7e6d1a47987fe232326521
readonly CLOCK_DTB_SHA256=8033f913a4cfd78c2fca9d901c5838285717e9929fc577ea369d7066423c2126
readonly OUTPUT_DTB_SHA256=31f72bcda3af4edb61d3fe18bcbaec50bef740e507b497ea617df5dd52ab772f
readonly CLOCK_BACKEND=/dvfsp-clock-backend@1001a000
readonly BIGIDVFSP_BACKEND=/dvfsp-bigidvfs-backend
readonly OBSERVER=/protected-readback-observer
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
for command in awk chmod cmp dirname dtc fdtget fdtput grep mkdir mktemp \
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
source_builder="$repo_root/experiments/2026-08-23-mainline-clock-backend-cspm-coexistence/scripts/build-serviceability-clock-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source DT builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source DT builder identity changed'

mkdir -p -- "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.protected-clock-dtb.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM

for replica in a b; do
	clock="$workdir/clock-$replica.dtb"
	candidate="$workdir/candidate-$replica.dtb"
	/bin/bash "$source_builder" --base-dtb "$base_dtb" --output "$clock" >/dev/null
	[[ "$(sha256sum "$clock" | awk '{print $1}')" == "$CLOCK_DTB_SHA256" ]] ||
		die 'serviceability/clock DT identity changed'
	mv "$clock" "$candidate"
	clock_phandle="$(fdtget -tx "$candidate" "$CLOCK_BACKEND" phandle)"
	bigidvfs_phandle="$(fdtget -tx "$candidate" "$BIGIDVFSP_BACKEND" phandle)"
	fdtput -c "$candidate" "$OBSERVER"
	fdtput -ts "$candidate" "$OBSERVER" compatible \
		mediatek,mt6797-protected-readback-observer
	fdtput -tx "$candidate" "$OBSERVER" mediatek,clock-backend "$clock_phandle"
	fdtput -tx "$candidate" "$OBSERVER" mediatek,bigidvfs-backend \
		"$bigidvfs_phandle"
	fdtput -ts "$candidate" "$OBSERVER" status okay
	dtc -q -I dtb -O dtb -o /dev/null "$candidate"
	[[ "$(fdtget -ts "$candidate" "$OBSERVER" compatible)" == \
		mediatek,mt6797-protected-readback-observer ]] ||
		die 'observer compatible changed'
	[[ "$(fdtget -tx "$candidate" "$OBSERVER" mediatek,clock-backend)" == \
		"$clock_phandle" ]] || die 'observer clock phandle changed'
	[[ "$(fdtget -tx "$candidate" "$OBSERVER" mediatek,bigidvfs-backend)" == \
		"$bigidvfs_phandle" ]] || die 'observer BigiDVFS phandle changed'
	[[ "$(fdtget -ts "$candidate" "$OBSERVER" status)" == okay ]] ||
		die 'observer was not enabled'
	[[ "$(fdtget -ts "$candidate" "$CLOCK_BACKEND" status)" == okay ]] ||
		die 'clock backend was not enabled'
	[[ "$(fdtget -ts "$candidate" "$BIGIDVFSP_BACKEND" status)" == disabled ]] ||
		die 'BigiDVFS backend closure changed'
	[[ "$(fdtget -ts "$candidate" "$RAM_CONSOLE" status)" == disabled ]] ||
		die 'ram-console closure changed'
	[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
		die 'derived protected-clock DT identity changed'
done
cmp -s "$workdir/candidate-a.dtb" "$workdir/candidate-b.dtb" ||
	die 'independent DT derivations differ'
mv "$workdir/candidate-a.dtb" "$output"
chmod 0600 "$output"
rm -f -- "$workdir/candidate-b.dtb"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM

printf 'validation=protected-clock-first-dmesg-serviceability-dtb\n'
printf 'base_dtb_sha256=%s\nclock_dtb_sha256=%s\n' \
	"$BASE_DTB_SHA256" "$CLOCK_DTB_SHA256"
printf 'output_dtb_sha256=%s\nindependent_derivations=byte-identical\n' \
	"$OUTPUT_DTB_SHA256"
printf 'clock_backend_status=okay\nbigidvfs_backend_status=disabled\n'
printf 'protected_observer_status=okay\nprotected_observer_mode=clock-only-raw-entry\n'
printf 'CPU8_CPU9_admission=closed\ndevice_access=none\nhardware_write=none\nresult=pass\n'
