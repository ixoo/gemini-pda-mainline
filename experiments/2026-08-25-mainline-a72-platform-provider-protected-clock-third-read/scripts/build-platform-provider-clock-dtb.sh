#!/usr/bin/env bash

# Replace only the live-passed provider-ready observer with the three-source
# platform/provider/protected-clock observer. Preserve the exact Stage-27 tree.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=923575e4e25498f2749bb440af78372e36bb318bf5717d05ced18be600ebd6c8
readonly OUTPUT_SHA256=90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d
readonly OUTPUT_SIZE=27636
readonly PLATFORM_PHANDLE=2f
readonly PROVIDER_PHANDLE=30
readonly CLOCK_PHANDLE=31
readonly OUTPUT_FILE=mt6797-gemini-pda-a72-platform-provider-clock-third-read.dtb

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
for command in awk chmod cmp cp dtc fdtget fdtput find grep mkdir mktemp mv rm \
	rmdir sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
input=$(cd -- "$(dirname -- "$input")" && pwd -P)/$(basename -- "$input")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output must remain below artifacts' ;; esac
[[ -f "$input" && ! -L "$input" ]] || die 'input DTB is missing or unsafe'
[[ "$(sha256sum "$input" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'live-passed provider-ready DTB changed'

workdir=$(mktemp -d "$output_parent/.a72-platform-provider-clock-dtb.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
mkdir "$workdir/first" "$workdir/second"

dtc -q -s -I dtb -O dts -o "$workdir/source.sorted.dts" "$input"
[[ "$(fdtget -t x "$input" /a72-platform-state@10222000 phandle)" == \
	"$PLATFORM_PHANDLE" ]] || die 'platform-state phandle changed'
[[ "$(fdtget -t x "$input" /i2c@1100e000/regulator@68 phandle)" == \
	"$PROVIDER_PHANDLE" ]] || die 'provider phandle changed'
[[ "$(fdtget -t s "$input" /a72-platform-provider-snapshot-observer compatible)" == \
	mediatek,mt6797-a72-platform-provider-snapshot-observer ]] ||
	die 'live-passed predecessor observer changed'
[[ "$(fdtget -t x "$input" /a72-platform-provider-snapshot-observer mediatek,platform-state)" == \
	"$PLATFORM_PHANDLE" ]] || die 'predecessor platform reference changed'
[[ "$(fdtget -t x "$input" /a72-platform-provider-snapshot-observer mediatek,provider)" == \
	"$PROVIDER_PHANDLE" ]] || die 'predecessor provider reference changed'
! fdtget -l "$input" / | grep -qx a72-platform-provider-clock-observer ||
	die 'clock observer already exists in predecessor'
! fdtget "$input" /dvfsp-clock-backend@1001a000 phandle >/dev/null 2>&1 ||
	die 'clock backend already has a phandle'
! grep -q "phandle = <0x$CLOCK_PHANDLE>;" "$workdir/source.sorted.dts" ||
	die 'selected clock phandle is already in use'

derive() {
	local source=$1 output=$2
	cp "$source" "$output"
	fdtput -r "$output" /a72-platform-provider-snapshot-observer
	fdtput -c "$output" /a72-platform-provider-clock-observer
	fdtput -t s "$output" /a72-platform-provider-clock-observer compatible \
		mediatek,mt6797-a72-platform-provider-clock-observer
	fdtput -t x "$output" /a72-platform-provider-clock-observer \
		mediatek,platform-state "$PLATFORM_PHANDLE"
	fdtput -t x "$output" /a72-platform-provider-clock-observer \
		mediatek,provider "$PROVIDER_PHANDLE"
	fdtput -t x "$output" /dvfsp-clock-backend@1001a000 phandle \
		"$CLOCK_PHANDLE"
	fdtput -t x "$output" /a72-platform-provider-clock-observer \
		mediatek,clock-backend "$CLOCK_PHANDLE"
}

for root in "$workdir/first" "$workdir/second"; do
	derive "$input" "$root/$OUTPUT_FILE"
done
cmp -s "$workdir/first/$OUTPUT_FILE" "$workdir/second/$OUTPUT_FILE" ||
	die 'independent DT derivations differ'

dtb="$workdir/first/$OUTPUT_FILE"
[[ "$(sha256sum "$dtb" | awk '{print $1}')" == "$OUTPUT_SHA256" ]] ||
	die 'derived DTB identity changed'
[[ "$(wc -c <"$dtb" | tr -d ' ')" == "$OUTPUT_SIZE" ]] ||
	die 'derived DTB size changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-provider-clock-observer compatible)" == \
	mediatek,mt6797-a72-platform-provider-clock-observer ]] ||
	die 'clock observer compatible changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-provider-clock-observer mediatek,platform-state)" == \
	"$PLATFORM_PHANDLE" ]] || die 'clock observer platform reference changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-provider-clock-observer mediatek,provider)" == \
	"$PROVIDER_PHANDLE" ]] || die 'clock observer provider reference changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-provider-clock-observer mediatek,clock-backend)" == \
	"$CLOCK_PHANDLE" ]] || die 'clock observer backend reference changed'
[[ "$(fdtget -t x "$dtb" /dvfsp-clock-backend@1001a000 phandle)" == \
	"$CLOCK_PHANDLE" ]] || die 'clock backend phandle changed'
! fdtget -l "$dtb" / | grep -qx a72-platform-provider-snapshot-observer ||
	die 'predecessor observer survived replacement'
[[ "$(fdtget -t s "$dtb" /i2c@1100e000 status)" == okay ]] ||
	die 'provider I2C controller changed'
[[ "$(fdtget -t s "$dtb" /i2c@1100e000/regulator@68 compatible)" == \
	dlg,da9214-legacy ]] || die 'DA921x provider node changed'
[[ "$(fdtget -t s "$dtb" /dvfsp-bigidvfs-backend status)" == okay ]] ||
	die 'passed BigiDVFS backend changed'
[[ "$(fdtget -t s "$dtb" /dvfsp-clock-backend@1001a000 status)" == okay ]] ||
	die 'passed clock backend changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-state@10222000 status)" == okay ]] ||
	die 'passed platform state changed'

for node in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 \
	/i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix; do
	[[ "$(fdtget -t s "$dtb" "$node" status)" == okay ]] ||
		die "Stage-27 serviceability node changed: $node"
done
[[ "$(fdtget -t s "$dtb" /chosen/framebuffer@7dfb0000 compatible)" == simple-framebuffer ]] ||
	die 'Stage-27 framebuffer disappeared'
[[ "$(fdtget -t s "$dtb" /scp@10020000 status)" == disabled ]] ||
	die 'Stage-27 SCP state changed'

cp "$dtb" "$workdir/reverted.dtb"
fdtput -r "$workdir/reverted.dtb" /a72-platform-provider-clock-observer
fdtput -d "$workdir/reverted.dtb" /dvfsp-clock-backend@1001a000 phandle
fdtput -c "$workdir/reverted.dtb" /a72-platform-provider-snapshot-observer
fdtput -t s "$workdir/reverted.dtb" /a72-platform-provider-snapshot-observer compatible \
	mediatek,mt6797-a72-platform-provider-snapshot-observer
fdtput -t x "$workdir/reverted.dtb" /a72-platform-provider-snapshot-observer \
	mediatek,platform-state "$PLATFORM_PHANDLE"
fdtput -t x "$workdir/reverted.dtb" /a72-platform-provider-snapshot-observer \
	mediatek,provider "$PROVIDER_PHANDLE"
dtc -q -s -I dtb -O dts -o "$workdir/reverted.sorted.dts" "$workdir/reverted.dtb"
cmp -s "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts" ||
	die 'reverse replacement does not recover the live-passed semantic tree'

{
	printf 'experiment=2026-08-25-mainline-a72-platform-provider-protected-clock-third-read\n'
	printf 'source_dtb_sha256=%s\nderived_dtb_sha256=%s\n' "$SOURCE_SHA256" "$OUTPUT_SHA256"
	printf 'semantic_baseline_after_reverse_replacement=byte-identical-sorted-dts\n'
	printf 'removed_nodes=1\nadded_nodes=1\nadded_source_phandles=1\nadded_reference_properties=3\n'
	printf 'provider_ready_observer=absent\nplatform_provider_clock_observer=enabled\n'
	printf 'provider_phandle=0x%s\nclock_phandle=0x%s\n' "$PROVIDER_PHANDLE" "$CLOCK_PHANDLE"
	printf 'da921x_provider_node=preserved\nbigidvfs_backend=okay\nclock_backend=okay\nplatform_state=okay\n'
	printf 'offline_platform_snapshot_calls=0\nprovider_snapshots=0\nprotected_clock_calls=0\n'
	printf 'register_reads=0\nregister_writes=0\ncpu_requests=0\nresult=pass\n'
} >"$workdir/first/provenance.txt"
(
	cd "$workdir/first"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$workdir/first/SHA256SUMS"
(cd "$workdir/first" && sha256sum --check --strict SHA256SUMS >/dev/null)
chmod 0600 "$workdir/first"/*
output="$output_parent/dtb-a72-platform-provider-clock-${OUTPUT_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$workdir/first" "$output"
rm -rf -- "$workdir/second"
rm -f -- "$workdir/reverted.dtb" "$workdir/source.sorted.dts" \
	"$workdir/reverted.sorted.dts"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-platform-provider-clock-dtb\nartifact=%s\ndtb_sha256=%s\n' \
	"$output" "$OUTPUT_SHA256"
printf 'device_access=none\nhardware_write=none\n'
