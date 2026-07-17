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
usage: build-clock-retention-dtb.sh --baseline DTB --output DTB

Derive Candidate F's DTB from exact Candidate E by adding only the
CLK_INFRA_DISP_PWM clock reference to its simple-framebuffer node. The
provider phandle is resolved from the pinned DTB by path, never hard-coded.
This command has no device or flashing interface.
EOF
}

baseline=
output=
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires DTB"
			baseline=$2
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

[[ -n "$baseline" ]] || die "--baseline is required"
[[ -n "$output" ]] || die "--output is required"
[[ -s "$baseline" ]] || die "baseline DTB is missing or empty: $baseline"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for command in fdtget fdtput install python3 sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
validator="${script_dir}/validate-simplefb-clock-delta.py"
[[ -s "$validator" ]] || die "missing validator: $validator"

readonly provider=/syscon@10001000
readonly framebuffer=/chosen/framebuffer@7dfb0000
readonly clock_id=45
clock_cells="$(fdtget -t u "$baseline" "$provider" '#clock-cells')"
provider_phandle="$(fdtget -t u "$baseline" "$provider" phandle)"
[[ "$clock_cells" == 1 ]] || die "infra clock provider is not one-cell"
[[ "$provider_phandle" =~ ^[1-9][0-9]*$ ]] || die "invalid infra provider phandle"
if fdtget "$baseline" "$framebuffer" clocks >/dev/null 2>&1; then
	die "baseline framebuffer unexpectedly already has clocks"
fi

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-screen-clock-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

candidate="${workdir}/candidate-f.dtb"
install -m 0600 "$baseline" "$candidate"
fdtput -t u "$candidate" "$framebuffer" clocks "$provider_phandle" "$clock_id"
python3 "$validator" --baseline "$baseline" --candidate "$candidate"

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$candidate" "$output"
printf 'output=%s\n' "$output"
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'provider_path=%s\n' "$provider"
printf 'provider_phandle_source=resolved-from-pinned-baseline-dtb\n'
printf 'clock_symbol=CLK_INFRA_DISP_PWM\n'
printf 'clock_id=%s\n' "$clock_id"
printf 'consumer_path=%s\n' "$framebuffer"
printf 'semantic_delta=one-simplefb-clocks-property\n'
printf 'build_hardware_write=none\n'
