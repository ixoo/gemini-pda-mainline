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

Replace only /init in exact Candidate L's deterministic initramfs with the
tracked Candidate M watchdog-registration diagnostic. This command has no
device, partition, network, or flashing interface.
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
[[ -s "$baseline" ]] || die "exact Candidate L initramfs is required"
[[ -n "$output" ]] || die "--output is required"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
[[ "$source_date_epoch" =~ ^[0-9]+$ && "$source_date_epoch" == 0 ]] || \
	die "Candidate M requires source-date-epoch zero"
for command in awk chmod cpio dirname find gzip install mkdir mktemp mv rm sha256sum sort touch wc; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

readonly EXPECTED_BASELINE_INITRAMFS_SHA256=52dd9145b3d85d8f73990f5798b494293aab17d86a066f79f33274207986de32
readonly EXPECTED_CANDIDATE_INIT_SHA256=005dddd59b1918d18ff03d15671ab84b2453c67bc6db911dde6fdaded47e54d0
readonly EXPECTED_CANDIDATE_INITRAMFS_SHA256=e0edeceb127e08cd0b01749e289474479ccebe8f33995d39014d7dcf8c5b25fc
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == \
	"$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || die "baseline is not exact Candidate L"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
init_source="${experiment_dir}/initramfs/init"
validator="${script_dir}/validate-initramfs-delta.sh"
[[ -s "$init_source" ]] || die "Candidate M init source is missing"
[[ -s "$validator" ]] || die "initramfs validator is missing"
[[ "$(sha256sum "$init_source" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INIT_SHA256" ]] || die "Candidate M init source changed"

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.watchdog-registration-initramfs.XXXXXX")"
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
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == \
	"$EXPECTED_CANDIDATE_INITRAMFS_SHA256" ]] || \
	die "Candidate M initramfs does not match its pinned bytes"
mv "$temporary" "$output"

printf 'output=%s\n' "$output"
printf 'size=%s\n' "$(wc -c <"$output")"
printf 'sha256=%s\n' "$EXPECTED_CANDIDATE_INITRAMFS_SHA256"
printf 'source_date_epoch=%s\n' "$source_date_epoch"
printf 'marker=GEMINI_WATCHDOG_REGISTRATION_20260718_M\n'
printf 'only_archive_delta=init\n'
printf 'watchdog_irq=omitted-in-candidate-dtb\n'
printf 'watchdog_return=one-handoff-ping-then-single-stage-TOPRGU-expiry,timeout-31s,failure-boundary-40s\n'
printf 'storage_access=none\n'
printf 'runtime_networking=none\n'
printf 'build_hardware_write=none\nflash=none\n'
