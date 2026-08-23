#!/usr/bin/env bash

# Reproduce the runtime-proven serviceability mutations on the exact
# coexistence package DT, then enable only its read-free clock backend.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d
readonly BASE_DTB_SHA256=0a6b7c72dc1182e69d377c38be7d412c225b523b9a7e6d1a47987fe232326521
readonly SERVICEABILITY_DTB_SHA256=96243084722aa2e4a2257352470bfe8929e7e3240492483ac39a538fa856fca3
readonly OUTPUT_DTB_SHA256=8033f913a4cfd78c2fca9d901c5838285717e9929fc577ea369d7066423c2126
readonly CLOCK_BACKEND=/dvfsp-clock-backend@1001a000
readonly BIGIDVFSP_BACKEND=/dvfsp-bigidvfs-backend
readonly HANDOFF=/dvfsp-handoff@11015000
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
	mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
[[ "$(sha256sum "$base_dtb" | awk '{print $1}')" == "$BASE_DTB_SHA256" ]] ||
	die 'current package DTB identity changed'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

mkdir -p -- "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.clock-cspm-dtb.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
derived_builder="$workdir/build-serviceability-dtb.sh"
python3 - "$source_builder" "$derived_builder" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e",
        "0a6b7c72dc1182e69d377c38be7d412c225b523b9a7e6d1a47987fe232326521",
        1,
    ),
    (
        "b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd",
        "96243084722aa2e4a2257352470bfe8929e7e3240492483ac39a538fa856fca3",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe serviceability derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived_builder"

for replica in a b; do
	serviceability="$workdir/serviceability-$replica.dtb"
	clock="$workdir/clock-$replica.dtb"
	/bin/bash "$derived_builder" --base-dtb "$base_dtb" --output "$serviceability" >/dev/null
	[[ "$(sha256sum "$serviceability" | awk '{print $1}')" == "$SERVICEABILITY_DTB_SHA256" ]] ||
		die 'serviceability DT identity changed'
	mv "$serviceability" "$clock"
	fdtput -ts "$clock" "$CLOCK_BACKEND" status okay
	dtc -q -I dtb -O dtb -o /dev/null "$clock"
	handoff="$(fdtget -tx "$clock" "$HANDOFF" phandle)"
	[[ "$(fdtget -ts "$clock" "$CLOCK_BACKEND" status)" == okay ]] ||
		die 'clock backend was not enabled'
	[[ "$(fdtget -ts "$clock" "$CLOCK_BACKEND" reg-names)" == mcumixed ]] ||
		die 'clock backend register names changed'
	[[ "$(fdtget -tx "$clock" "$CLOCK_BACKEND" reg)" == '0 1001a000 0 1000' ]] ||
		die 'clock backend resource changed'
	[[ "$(fdtget -tx "$clock" "$CLOCK_BACKEND" access-controllers)" == "$handoff" ]] ||
		die 'clock backend handoff supplier changed'
	[[ "$(fdtget -ts "$clock" "$BIGIDVFSP_BACKEND" status)" == disabled ]] ||
		die 'BigiDVFS backend closure changed'
	[[ "$(fdtget -ts "$clock" "$RAM_CONSOLE" status)" == disabled ]] ||
		die 'ram-console closure changed'
	[[ -z "$(fdtget -l "$clock" / | grep 'protected-readback' || true)" ]] ||
		die 'protected-readback observer returned'
	[[ "$(sha256sum "$clock" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
		die 'derived coexistence DT identity changed'
done
cmp -s "$workdir/clock-a.dtb" "$workdir/clock-b.dtb" ||
	die 'independent DT derivations differ'
mv "$workdir/clock-a.dtb" "$output"
chmod 0600 "$output"
rm -f -- "$workdir/clock-b.dtb" "$derived_builder"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM

printf 'validation=clock-backend-cspm-coexistence-serviceability-dtb\n'
printf 'base_dtb_sha256=%s\nserviceability_dtb_sha256=%s\n' \
	"$BASE_DTB_SHA256" "$SERVICEABILITY_DTB_SHA256"
printf 'output_dtb_sha256=%s\nindependent_derivations=byte-identical\n' \
	"$OUTPUT_DTB_SHA256"
printf 'cspm_owner=handoff\nclock_backend_resource=mcumixed-only\n'
printf 'clock_backend_supplier=handoff\ndtb_delta=clock-backend-status-okay-only\n'
printf 'bigidvfs_backend_status=disabled\nprotected_observer=absent\n'
printf 'CPU8_CPU9_admission=closed\ndevice_access=none\nhardware_write=none\nresult=pass\n'
