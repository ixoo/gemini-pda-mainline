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
usage: build-mm-root-dtb.sh --baseline DTB --output DTB

Derive Candidate H's DTB from exact Candidate G by appending only the
CLK_TOP_MUX_MM reference to its simple-framebuffer clocks property. Provider
phandles are resolved from the pinned DTB by path, never hard-coded.
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
validator="${script_dir}/validate-simplefb-mm-root-delta.py"
[[ -s "$validator" ]] || die "missing validator: $validator"

readonly infra_provider=/syscon@10001000
readonly top_provider=/topckgen@10000000
readonly framebuffer=/chosen/framebuffer@7dfb0000
readonly infra_clock_id=45
readonly top_clock_id=6
[[ "$(fdtget -t s "$baseline" "$infra_provider" compatible)" == \
	"mediatek,mt6797-infracfg syscon" ]] || die "unexpected infra provider"
[[ "$(fdtget -t s "$baseline" "$top_provider" compatible)" == \
	"mediatek,mt6797-topckgen" ]] || die "unexpected top provider"
[[ "$(fdtget -t u "$baseline" "$infra_provider" '#clock-cells')" == 1 ]] || \
	die "infra provider is not one-cell"
[[ "$(fdtget -t u "$baseline" "$top_provider" '#clock-cells')" == 1 ]] || \
	die "top provider is not one-cell"
infra_phandle="$(fdtget -t u "$baseline" "$infra_provider" phandle)"
top_phandle="$(fdtget -t u "$baseline" "$top_provider" phandle)"
[[ "$infra_phandle" =~ ^[1-9][0-9]*$ ]] || die "invalid infra phandle"
[[ "$top_phandle" =~ ^[1-9][0-9]*$ ]] || die "invalid top phandle"
[[ "$(fdtget -t u "$baseline" "$framebuffer" clocks)" == \
	"${infra_phandle} ${infra_clock_id}" ]] || die "baseline is not exact Candidate G clocks"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-mm-root-dtb.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

candidate="${workdir}/candidate-h.dtb"
install -m 0600 "$baseline" "$candidate"
fdtput -t u "$candidate" "$framebuffer" clocks \
	"$infra_phandle" "$infra_clock_id" "$top_phandle" "$top_clock_id"
python3 "$validator" --baseline "$baseline" --candidate "$candidate"

mkdir -p "$(dirname -- "$output")"
install -m 0600 "$candidate" "$output"
printf 'output=%s\n' "$output"
printf 'baseline_sha256=%s\n' "$(sha256sum "$baseline" | awk '{print $1}')"
printf 'output_sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'infra_provider_path=%s\n' "$infra_provider"
printf 'infra_provider_phandle_source=resolved-from-pinned-baseline-dtb\n'
printf 'top_provider_path=%s\n' "$top_provider"
printf 'top_provider_phandle_source=resolved-from-pinned-baseline-dtb\n'
printf 'added_clock_symbol=CLK_TOP_MUX_MM\n'
printf 'added_clock_id=%s\n' "$top_clock_id"
printf 'consumer_path=%s\n' "$framebuffer"
printf 'semantic_delta=append-one-simplefb-clock-specifier\n'
printf 'build_hardware_write=none\n'
