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
usage: build-usb-diagnostic-dtb.sh --base DTB --output DTB

Apply the mandatory LK handoff overlay and the USB diagnostic status overlay
to an explicit Gemini DTB. The output must not exist. This command has no
device or flashing interface.
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
for command in dtc fdtoverlay python3 sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
mandatory_source="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/dts/lk-handoff.dtso"
usb_source="${experiment_dir}/dts/usb-gadget.dtso"
validator="${repo_root}/experiments/2026-07-16-lk-handoff-alignment/scripts/validate-lk-compatible-dtb.py"
[[ -r "$mandatory_source" ]] || die "missing overlay: $mandatory_source"
[[ -r "$usb_source" ]] || die "missing overlay: $usb_source"
[[ -r "$validator" ]] || die "missing validator: $validator"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-usbdiag-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mandatory_overlay="$workdir/lk-handoff.dtbo"
mandatory_result="$workdir/lk-handoff.dtb"
usb_overlay="$workdir/usb-gadget.dtbo"
final_result="$workdir/lk-handoff-usb-gadget.dtb"

dtc -q -Wno-unit_address_vs_reg -@ -I dts -O dtb \
	-o "$mandatory_overlay" "$mandatory_source"
fdtoverlay -i "$base" -o "$mandatory_result" "$mandatory_overlay"
dtc -q -@ -I dts -O dtb -o "$usb_overlay" "$usb_source"
fdtoverlay -i "$mandatory_result" -o "$final_result" "$usb_overlay"
python3 "$validator" --base "$base" --candidate "$final_result" \
	--with-usb-gadget

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$final_result" "$output"
printf 'output=%s\n' "$output"
printf 'base_sha256=%s\n' "$(sha256sum "$base" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'usb_gadget=yes\n'
printf 'simplefb=no\n'
printf 'hardware_write=none\n'
