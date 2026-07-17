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
usage: build-lk-compatible-dtb.sh --base DTB --output DTB [--with-simplefb]

Apply the packaging-only LK handoff overlay to an explicit Gemini base DTB.
Optionally add the isolated simple-framebuffer diagnostic overlay. The output
must not exist. This command has no device or flashing interface.
EOF
}

base=
output=
with_simplefb=0
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
		--with-simplefb)
			with_simplefb=1
			shift
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
mandatory_source="${experiment_dir}/dts/lk-handoff.dtso"
simplefb_source="${experiment_dir}/dts/lk-simplefb.dtso"
validator="${script_dir}/validate-lk-compatible-dtb.py"
[[ -r "$mandatory_source" ]] || die "missing overlay: $mandatory_source"
[[ -r "$simplefb_source" ]] || die "missing overlay: $simplefb_source"
[[ -r "$validator" ]] || die "missing validator: $validator"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-lk-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mandatory_overlay="$workdir/lk-handoff.dtbo"
mandatory_result="$workdir/lk-handoff.dtb"
dtc -q -Wno-unit_address_vs_reg -@ -I dts -O dtb \
	-o "$mandatory_overlay" "$mandatory_source"
fdtoverlay -i "$base" -o "$mandatory_result" "$mandatory_overlay"

validator_args=(--base "$base" --candidate "$mandatory_result")
if ((with_simplefb)); then
	simplefb_overlay="$workdir/lk-simplefb.dtbo"
	final_result="$workdir/lk-handoff-simplefb.dtb"
	dtc -q -@ -I dts -O dtb -o "$simplefb_overlay" "$simplefb_source"
	fdtoverlay -i "$mandatory_result" -o "$final_result" "$simplefb_overlay"
	validator_args=(--base "$base" --candidate "$final_result" --with-simplefb)
else
	final_result="$mandatory_result"
fi
python3 "$validator" "${validator_args[@]}"

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$final_result" "$output"
printf 'output=%s\n' "$output"
printf 'base_sha256=%s\n' "$(sha256sum "$base" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'simplefb=%s\n' "$([[ $with_simplefb == 1 ]] && printf yes || printf no)"
printf 'hardware_write=none\n'
