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

Replace only /init in exact Candidate M's deterministic initramfs with the
tracked Candidate N CPU1-online diagnostic. This command has no device,
partition, network, or flashing interface.
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
[[ -s "$baseline" ]] || die "exact Candidate M initramfs is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate N requires source-date-epoch zero"
for command in awk chmod cpio dirname find gzip install mkdir mktemp mv rm sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_BASELINE_INITRAMFS_SHA256=e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate M"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
validator="${script_dir}/validate-initramfs-delta.sh"
[[ -s "$init_source" ]] || die "Candidate N init source is missing"
[[ -s "$validator" ]] || die "initramfs validator is missing"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.cpu1-online-initramfs.XXXXXX")"
temporary="${workdir}/candidate.img"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
install -m 0755 "$init_source" "$workdir/root/init"
find "$workdir/root" -exec touch -h -d "@$source_date_epoch" {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$temporary"
chmod 0600 "$temporary"

"$validator" --baseline "$baseline" --candidate "$temporary" >/dev/null
candidate_sha256="$(sha256sum "$temporary" | awk '{print $1}')"
mv "$temporary" "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$candidate_sha256"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_CPU1_ONLINE_20260718_N\n'
printf 'only_archive_delta=init\n'
printf 'watchdog_action=arm-before-cpu1,one-handoff-ping,no-further-pings\n'
printf 'cpu_write=/sys/devices/system/cpu/cpu1/online:1\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'build_hardware_write=none\nflash=none\n'
