#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly BASE_SHA256=e1e4eca289320533bad5c879e78055eaa86a295080b1154c13debe29ddd8ee4a
readonly OVERLAY_SOURCE_SHA256=2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a
readonly OVERLAY_BINARY_SHA256=f2d4cec4b2dec6593a148c9bcb46cc989b825d4ea12aa46c06be0d8da11dd748
readonly OUTPUT_SHA256=f131a06474ad5665dd957d7290f7b1240ca9603028046c93f4a5527ba3aa1366

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
base=
output=
while (($#)); do
	case "$1" in
	--base|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in --base) base=$2 ;; --output) output=$2 ;; esac
		shift 2 ;;
	*) die "usage: $0 --base FILE --output FILE" ;;
	esac
done
[[ -f "$base" && ! -L "$base" ]] || die 'base DT is missing or unsafe'
[[ -n "$output" && ! -e "$output" && ! -L "$output" ]] || die 'output exists or is unsafe'
for command in awk dirname dtc fdtoverlay mkdir mktemp mv python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "missing command: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
overlay_source="$script_dir/../thermal-serviceability.dtso"
readonly script_dir repository overlay_source
[[ "$(sha256sum "$base" | awk '{print $1}')" == "$BASE_SHA256" ]] || die 'base DT identity changed'
[[ "$(sha256sum "$overlay_source" | awk '{print $1}')" == "$OVERLAY_SOURCE_SHA256" ]] || die 'overlay source identity changed'
output_parent=$(dirname -- "$output")
[[ -d "$output_parent" && ! -L "$output_parent" ]] || die 'output parent is missing or unsafe'
work=$(mktemp -d "$output_parent/.thermal-dtb-repair.XXXXXXXX")
cleanup() { [[ ! -d "${work:-}" ]] || rm -rf -- "$work"; }
trap cleanup EXIT HUP INT TERM
overlay="$work/thermal-serviceability.dtbo"
candidate="$work/mt6797-gemini-pda-thermal-serviceability.dtb"
dtc -Wno-resets_property -Wno-thermal_sensors_property -I dts -O dtb -o "$overlay" "$overlay_source"
[[ "$(sha256sum "$overlay" | awk '{print $1}')" == "$OVERLAY_BINARY_SHA256" ]] || die 'compiled overlay identity changed'
fdtoverlay -i "$base" -o "$candidate" "$overlay"
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$OUTPUT_SHA256" ]] || die 'output DT identity changed'
python3 "$script_dir/validate_dtb.py" --repository "$repository" --base "$base" --output "$candidate"
mv "$candidate" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$work"
printf 'output=%s\noutput_dtb_sha256=%s\ndevice_action=none\n' "$output" "$OUTPUT_SHA256"
