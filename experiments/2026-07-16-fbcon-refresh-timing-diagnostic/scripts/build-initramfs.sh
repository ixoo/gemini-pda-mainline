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

Replace only /init in exact Candidate H's deterministic initramfs with the
tracked Candidate I fbcon refresh/timing program. This command has no device,
partition, networking, reset, or flashing interface.
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
[[ -s "$baseline" ]] || die "exact Candidate H initramfs is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
[[ "$source_date_epoch" == 0 ]] || die "exact Candidate H derivation requires epoch zero"
for command in awk cmp cpio find gzip install sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_BASELINE_INITRAMFS_SHA256=8dc85151bececf297f99b6f22c87316a54d0fa062e29c2c64ad00334b7ad0956
readonly EXPECTED_BASELINE_INIT_SHA256=c81247da5b39ed27daae1afc0fa988f5375bc493eccb6d2e5309389c389e85bb
readonly EXPECTED_CANDIDATE_INIT_SHA256=f918e03f1df6c7e50b5673eba99d2dbe48e438e9035453908231c28c94d5d6d5
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "baseline is not exact Candidate H's initramfs"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
baseline_init_source="${repo_root}/experiments/2026-07-16-fbcon-text-diagnostic/initramfs/init"
validator="${script_dir}/validate-initramfs-delta.sh"
for input in "$init_source" "$baseline_init_source" "$validator"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done
[[ "$(sha256sum "$init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || \
	die "tracked Candidate I /init no longer matches its pinned bytes"
[[ "$(sha256sum "$baseline_init_source" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INIT_SHA256" ]] || \
	die "tracked Candidate G/H /init no longer matches its pinned bytes"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.fbcon-refresh-initramfs.XXXXXX")"
temporary="${workdir}/candidate.img"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
cmp -s "$workdir/root/init" "$baseline_init_source" || \
	die "baseline archive /init is not exact Candidate G/H"
install -m 0755 "$init_source" "$workdir/root/init"
find "$workdir/root" -exec touch -h -d "@$source_date_epoch" {} +

(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$temporary"
chmod 0600 "$temporary"

"$validator" --baseline "$baseline" --candidate "$temporary" >/dev/null
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || \
	die "generated Candidate I initramfs does not match its pinned bytes"
mv "$temporary" "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_FBCON_REFRESH_20260716_I\n'
printf 'only_archive_delta=init\n'
printf 'active_refresh_seconds=60\n'
printf 'tick_sequence=T+01..T+60\n'
printf 'final_state=static-hold-no-further-console-writes\n'
printf 'raw_framebuffer_access=none\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'runtime_reset_request=none\n'
printf 'build_hardware_write=none\nflash=none\n'
