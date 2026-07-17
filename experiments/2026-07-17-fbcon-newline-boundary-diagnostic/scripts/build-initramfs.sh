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
usage: build-initramfs.sh --baseline FILE --output PATH
       [--source-date-epoch N]

Replace only /init in exact Candidate J's deterministic initramfs with the
tracked Candidate K newline-boundary program. No hardware interface exists.
EOF
}

baseline=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--baseline)
			(($# >= 2)) || die "--baseline requires FILE"
			baseline=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires PATH"
			output=$2
			shift 2
			;;
		--source-date-epoch)
			(($# >= 2)) || die "--source-date-epoch requires N"
			source_date_epoch=$2
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

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -s "$baseline" ]] || die "exact Candidate J initramfs is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "exact Candidate J derivation requires source-date-epoch zero"
for command in awk cmp cpio find gzip install sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_J_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
readonly EXPECTED_J_INIT_SHA256=f918e03f1df6c7e50b5673eba99d2dbe48e438e9035453908231c28c94d5d6d5
readonly EXPECTED_K_INIT_SHA256=c1b3cfa8bcda856d4afe3b54cbdef947b055e7c045b7c311af286ba51b5cd58b
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_J_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate J initramfs"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
baseline_init_source="${repo_root}/experiments/2026-07-16-fbcon-refresh-timing-diagnostic/initramfs/init"
validator="${script_dir}/validate-initramfs-delta.sh"
for input in "$init_source" "$baseline_init_source" "$validator"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done
[[ "$(sha256sum "$init_source" | awk '{print $1}')" == \
	"$EXPECTED_K_INIT_SHA256" ]] || die "tracked Candidate K /init bytes changed"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_J_INIT_SHA256" ]] || die "tracked Candidate I/J /init bytes changed"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.candidate-k-initramfs.XXXXXX")"
temporary="${workdir}/candidate.img"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir "${workdir}/root"
gzip -dc "$baseline" | (cd "${workdir}/root" && cpio -idmu --quiet)
cmp -s "${workdir}/root/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate I/J"
install -m 0755 "$init_source" "${workdir}/root/init"
find "${workdir}/root" -exec touch -h -d "@$source_date_epoch" {} +
(
	cd "${workdir}/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$temporary"
chmod 0600 "$temporary"

"$validator" --baseline "$baseline" --candidate "$temporary" >/dev/null
mv "$temporary" "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_FBCON_BOUNDARY_20260717_K\n'
printf 'only_archive_delta=init\n'
printf 'phase1=20x-leading-cr-no-newline\n'
printf 'phase2=12x-newline-terminated\n'
printf 'final_state=static-hold-no-further-console-writes\n'
printf 'tracked_init_forbidden_storage_fbdev_raw_memory_mmio_i2c_reset_watchdog_network_usb_control_access=none\n'
printf 'build_hardware_write=none\nflash=none\n'
