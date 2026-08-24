#!/usr/bin/env bash

# Add only the read-free clock-backend probe node to the exact passed
# Stage-27 plus platform-state DTB.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd
readonly OUTPUT_SHA256=5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f
readonly OUTPUT_SIZE=27243
readonly OUTPUT_FILE=mt6797-gemini-pda-a72-clock-backend-stage27-control.dtb

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
for command in awk chmod cmp cp dtc fdtget fdtput find mkdir mktemp mv rm \
	rmdir sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
input=$(cd -- "$(dirname -- "$input")" && pwd -P)/$(basename -- "$input")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output must remain below artifacts' ;; esac
[[ -f "$input" && ! -L "$input" ]] || die 'input DTB is missing or unsafe'
[[ "$(sha256sum "$input" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'passed platform-state DTB changed'

workdir=$(mktemp -d "$output_parent/.a72-clock-backend-stage27.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
mkdir "$workdir/first" "$workdir/second"

derive() {
	local source=$1 output=$2
	cp "$source" "$output"
	fdtput -c "$output" /dvfsp-clock-backend@1001a000
	fdtput -t s "$output" /dvfsp-clock-backend@1001a000 compatible \
		mediatek,mt6797-dvfsp-clock-backend
	fdtput -t x "$output" /dvfsp-clock-backend@1001a000 reg 0 1001a000 0 1000
	fdtput -t s "$output" /dvfsp-clock-backend@1001a000 reg-names mcumixed
	fdtput -t x "$output" /dvfsp-clock-backend@1001a000 clocks 3 36
	fdtput -t s "$output" /dvfsp-clock-backend@1001a000 clock-names i2c
	fdtput -t x "$output" /dvfsp-clock-backend@1001a000 access-controllers 2c
	fdtput -t s "$output" /dvfsp-clock-backend@1001a000 status okay
}

for root in "$workdir/first" "$workdir/second"; do
	derive "$input" "$root/$OUTPUT_FILE"
done
cmp -s "$workdir/first/$OUTPUT_FILE" "$workdir/second/$OUTPUT_FILE" ||
	die 'independent DT derivations differ'

dtb="$workdir/first/$OUTPUT_FILE"
[[ "$(sha256sum "$dtb" | awk '{print $1}')" == "$OUTPUT_SHA256" ]] || die 'derived DTB identity changed'
[[ "$(wc -c <"$dtb" | tr -d ' ')" == "$OUTPUT_SIZE" ]] || die 'derived DTB size changed'
[[ "$(fdtget -t s "$dtb" /dvfsp-clock-backend@1001a000 compatible)" == \
	mediatek,mt6797-dvfsp-clock-backend ]] || die 'clock compatible changed'
[[ "$(fdtget -t x "$dtb" /dvfsp-clock-backend@1001a000 reg)" == \
	'0 1001a000 0 1000' ]] || die 'MCUMIXED resource changed'
[[ "$(fdtget -t x "$dtb" /dvfsp-clock-backend@1001a000 clocks)" == '3 36' ]] || die 'clock handle changed'
[[ "$(fdtget -t x "$dtb" /dvfsp-clock-backend@1001a000 access-controllers)" == 2c ]] || die 'handoff supplier changed'
[[ "$(fdtget -t s "$dtb" /dvfsp-clock-backend@1001a000 status)" == okay ]] || die 'clock backend is not enabled'
[[ "$(fdtget -t x "$dtb" /dvfsp-handoff@11015000 phandle)" == 2c ]] || die 'handoff phandle changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-state@10222000 status)" == okay ]] || die 'passed platform-state source changed'

for node in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 \
	/i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix; do
	[[ "$(fdtget -t s "$dtb" "$node" status)" == okay ]] || die "Stage-27 serviceability node changed: $node"
done
[[ "$(fdtget -t s "$dtb" /chosen/framebuffer@7dfb0000 compatible)" == simple-framebuffer ]] ||
	die 'Stage-27 framebuffer disappeared'
[[ "$(fdtget -t s "$dtb" /scp@10020000 status)" == disabled ]] || die 'Stage-27 SCP state changed'

cp "$dtb" "$workdir/reverted.dtb"
fdtput -r "$workdir/reverted.dtb" /dvfsp-clock-backend@1001a000
dtc -q -s -I dtb -O dts -o "$workdir/source.sorted.dts" "$input"
dtc -q -s -I dtb -O dts -o "$workdir/reverted.sorted.dts" "$workdir/reverted.dtb"
cmp -s "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts" ||
	die 'removing the clock node does not recover the passed semantic tree'

{
	printf 'experiment=2026-08-24-mainline-a72-clock-backend-stage27-control\n'
	printf 'source_dtb_sha256=%s\nderived_dtb_sha256=%s\n' "$SOURCE_SHA256" "$OUTPUT_SHA256"
	printf 'semantic_baseline_after_remove=byte-identical-sorted-dts\n'
	printf 'changed_nodes=1\nclock_backend=okay\nplatform_state=okay\n'
	printf 'clock_handle_enable=0\nmmio_reads=0\nmmio_writes=0\n'
	printf 'protected_calls=0\nbigidvfs_calls=0\ncpu_requests=0\nresult=pass\n'
} >"$workdir/first/provenance.txt"
(
	cd "$workdir/first"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$workdir/first/SHA256SUMS"
(cd "$workdir/first" && sha256sum --check --strict SHA256SUMS >/dev/null)
chmod 0600 "$workdir/first"/*
output="$output_parent/dtb-a72-clock-backend-stage27-${OUTPUT_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$workdir/first" "$output"
rm -rf -- "$workdir/second"
rm -f -- "$workdir/reverted.dtb" "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-clock-backend-stage27-dtb\nartifact=%s\ndtb_sha256=%s\n' "$output" "$OUTPUT_SHA256"
printf 'device_access=none\nhardware_write=none\n'
