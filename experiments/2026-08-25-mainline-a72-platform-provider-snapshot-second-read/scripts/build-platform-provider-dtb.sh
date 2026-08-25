#!/usr/bin/env bash

# Replace only the passed platform-only observer with the composed platform and
# provider observer. Preserve the exact passed Stage-27 serviceability tree.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284
readonly OUTPUT_SHA256=ee8baf009bd3c94e59c91a4d4b6090e6280e4045b5a0ff8abdcd0c0ef2f6d1ac
readonly OUTPUT_SIZE=27531
readonly PLATFORM_PHANDLE=2f
readonly OUTPUT_FILE=mt6797-gemini-pda-a72-platform-provider-snapshot-second-read.dtb

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
	die 'runtime-passed platform-snapshot DTB changed'

workdir=$(mktemp -d "$output_parent/.a72-platform-provider-dtb.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
mkdir "$workdir/first" "$workdir/second"

dtc -q -s -I dtb -O dts -o "$workdir/source.sorted.dts" "$input"
[[ "$(fdtget -t x "$input" /a72-platform-state@10222000 phandle)" == \
	"$PLATFORM_PHANDLE" ]] || die 'passed platform-state phandle changed'
fdtget -l "$input" / | grep -qx a72-platform-snapshot-observer ||
	die 'passed platform-only observer is absent'
! fdtget -l "$input" / | grep -qx a72-platform-provider-snapshot-observer ||
	die 'composed observer already exists in predecessor'

derive() {
	local source=$1 output=$2
	cp "$source" "$output"
	fdtput -r "$output" /a72-platform-snapshot-observer
	fdtput -c "$output" /a72-platform-provider-snapshot-observer
	fdtput -t s "$output" /a72-platform-provider-snapshot-observer compatible \
		mediatek,mt6797-a72-platform-provider-snapshot-observer
	fdtput -t x "$output" /a72-platform-provider-snapshot-observer \
		mediatek,platform-state "$PLATFORM_PHANDLE"
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
[[ "$(fdtget -t s "$dtb" /a72-platform-provider-snapshot-observer compatible)" == \
	mediatek,mt6797-a72-platform-provider-snapshot-observer ]] ||
	die 'observer compatible changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-provider-snapshot-observer mediatek,platform-state)" == \
	"$PLATFORM_PHANDLE" ]] || die 'observer source reference changed'
! fdtget -l "$dtb" / | grep -qx a72-platform-snapshot-observer ||
	die 'platform-only observer survived replacement'
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
fdtput -r "$workdir/reverted.dtb" /a72-platform-provider-snapshot-observer
fdtput -c "$workdir/reverted.dtb" /a72-platform-snapshot-observer
fdtput -t s "$workdir/reverted.dtb" /a72-platform-snapshot-observer compatible \
	mediatek,mt6797-a72-platform-snapshot-observer
fdtput -t x "$workdir/reverted.dtb" /a72-platform-snapshot-observer \
	mediatek,platform-state "$PLATFORM_PHANDLE"
dtc -q -s -I dtb -O dts -o "$workdir/reverted.sorted.dts" "$workdir/reverted.dtb"
cmp -s "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts" ||
	die 'replacing the composed observer does not recover the passed semantic tree'

{
	printf 'experiment=2026-08-25-mainline-a72-platform-provider-snapshot-second-read\n'
	printf 'source_dtb_sha256=%s\nderived_dtb_sha256=%s\n' "$SOURCE_SHA256" "$OUTPUT_SHA256"
	printf 'semantic_baseline_after_reverse_replacement=byte-identical-sorted-dts\n'
	printf 'removed_nodes=1\nadded_nodes=1\nadded_reference_properties=1\n'
	printf 'platform_only_observer=absent\ncomposed_observer=enabled\n'
	printf 'da921x_provider_node=preserved\nbigidvfs_backend=okay\nclock_backend=okay\nplatform_state=okay\n'
	printf 'offline_platform_snapshot_calls=0\nprovider_snapshots=0\nsecure_calls=0\n'
	printf 'register_reads=0\nregister_writes=0\ncpu_requests=0\nresult=pass\n'
} >"$workdir/first/provenance.txt"
(
	cd "$workdir/first"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$workdir/first/SHA256SUMS"
(cd "$workdir/first" && sha256sum --check --strict SHA256SUMS >/dev/null)
chmod 0600 "$workdir/first"/*
output="$output_parent/dtb-a72-platform-provider-snapshot-${OUTPUT_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$workdir/first" "$output"
rm -rf -- "$workdir/second"
rm -f -- "$workdir/reverted.dtb" "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-platform-provider-snapshot-dtb\nartifact=%s\ndtb_sha256=%s\n' \
	"$output" "$OUTPUT_SHA256"
printf 'device_access=none\nhardware_write=none\n'
