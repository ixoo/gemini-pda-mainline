#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-screen-marker-dtb.sh --base DTB --output DTB

Apply the mandatory LK, USB diagnostic, and simple-framebuffer overlays to an
explicit Gemini DTB. The output must not exist. This command has no device or
flashing interface.
EOF
}

base=
output=
while (($#)); do
	case "$1" in
		--base)
			(($# >= 2)) || die "--base requires DTB"
			base=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DTB"
			output=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ -n "$base" ]] || die "--base is required"
[[ -n "$output" ]] || die "--output is required"
[[ -s "$base" ]] || die "base DTB is missing or empty: $base"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for command in dtc fdtoverlay fdtget python3 sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
mandatory_source="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-handoff.dtso"
usb_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/dts/usb-gadget.dtso"
simplefb_source="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-simplefb.dtso"
validator="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/scripts/validate-lk-compatible-dtb.py"
for input in "$mandatory_source" "$usb_source" "$simplefb_source" "$validator"; do
	[[ -r "$input" ]] || die "missing input: $input"
done

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-screen-marker-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mandatory_overlay="$workdir/lk-handoff.dtbo"
mandatory_result="$workdir/lk-handoff.dtb"
usb_overlay="$workdir/usb-gadget.dtbo"
usb_result="$workdir/lk-handoff-usb-gadget.dtb"
simplefb_overlay="$workdir/lk-simplefb.dtbo"
final_result="$workdir/lk-handoff-usb-gadget-simplefb.dtb"

dtc -q -Wno-unit_address_vs_reg -@ -I dts -O dtb \
	-o "$mandatory_overlay" "$mandatory_source"
fdtoverlay -i "$base" -o "$mandatory_result" "$mandatory_overlay"
dtc -q -@ -I dts -O dtb -o "$usb_overlay" "$usb_source"
fdtoverlay -i "$mandatory_result" -o "$usb_result" "$usb_overlay"
dtc -q -@ -I dts -O dtb -o "$simplefb_overlay" "$simplefb_source"
fdtoverlay -i "$usb_result" -o "$final_result" "$simplefb_overlay"
python3 "$validator" --base "$base" --candidate "$final_result" \
	--with-usb-gadget --with-simplefb

framebuffer_node=/chosen/framebuffer@7dfb0000
read -r reg_hi reg_lo size_hi size_lo < <(
	fdtget -t x "$final_result" "$framebuffer_node" reg
)
width="$(fdtget -t u "$final_result" "$framebuffer_node" width)"
height="$(fdtget -t u "$final_result" "$framebuffer_node" height)"
stride="$(fdtget -t u "$final_result" "$framebuffer_node" stride)"
format="$(fdtget -t s "$final_result" "$framebuffer_node" format)"
[[ "$reg_hi" == 0 && "$size_hi" == 0 ]] || die "framebuffer address exceeds 32 bits"
[[ "$reg_lo" == 7dfb0000 && "$size_lo" == 1f90000 ]] || \
	die "unexpected framebuffer base or reservation size"
[[ "$width" == 1080 && "$height" == 2160 && "$stride" == 4352 ]] || \
	die "unexpected framebuffer geometry"
[[ "$format" == a8r8g8b8 ]] || die "unexpected framebuffer format"
((stride >= width * 4)) || die "framebuffer stride is smaller than visible row bytes"
visible_span=$((stride * height))
reservation_size=$((16#$size_lo))
framebuffer_base=$((16#$reg_lo))
((visible_span <= reservation_size)) || die "visible frame exceeds reservation"
reservation_end=$((framebuffer_base + reservation_size))
((reservation_end == 0x7ff40000)) || die "unexpected framebuffer reservation end"

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$final_result" "$output"
printf 'output=%s\n' "$output"
printf 'base_sha256=%s\n' "$(sha256sum "$base" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'usb_gadget=yes\n'
printf 'simplefb=yes\n'
printf 'framebuffer_base=0x7dfb0000\n'
printf 'framebuffer_reservation_size=0x1f90000\n'
printf 'framebuffer_visible_bytes=0x8f7000\n'
printf 'framebuffer_minimum_row_bytes=4320\n'
printf 'framebuffer_reservation_end=0x7ff40000\n'
printf 'framebuffer_semantic_contract=passed\n'
printf 'build_hardware_write=none\n'
