#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly AD_INITRAMFS_SHA256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline AD_INITRAMFS --output NEW_FILE\n' "$0" >&2
}

baseline=
output=
while (($#)); do
	case "$1" in
	--baseline|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline) baseline=$2 ;;
		--output) output=$2 ;;
		esac
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

[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die 'run on the Linux AArch64 recovery VM'
[[ -f "$baseline" && ! -L "$baseline" && -n "$output" ]] || \
	die 'exact Candidate AD initramfs and output are required'
for command in awk basename chmod cpio dirname find grep gzip install mkdir mktemp mv \
	python3 rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$AD_INITRAMFS_SHA256" ]] || \
	die 'baseline is not the exact hardware-passed Candidate AD initramfs'
[[ -d "$(dirname -- "$output")" ]] || die 'output parent must already exist'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output="$output_parent/$(basename -- "$output")"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$(cd -- "$script_dir/../initramfs" && pwd -P)"
validator="$script_dir/validate-initramfs.py"
sources=(init af-cpu8)

hash_sources() {
	local name
	for name in "${sources[@]}"; do
		[[ -s "$source_dir/$name" && ! -L "$source_dir/$name" ]] || \
			die "Candidate AF initramfs source missing or unsafe: $name"
		sha256sum "$source_dir/$name"
	done
	sha256sum "$validator" "${BASH_SOURCE[0]}"
}

source_tree_at_start="$(hash_sources)"
if grep -Fq 'TO_PIN_PROVIDER_' "$source_dir/af-cpu8"; then
	die 'Candidate AF provider ABI/hook values are not pinned; build is blocked'
fi
workdir="$(mktemp -d "$output_parent/.candidate-af-initramfs.XXXXXX")"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore archived `.` mode.
chmod 0755 "$workdir/root"

[[ ! -e "$workdir/root/bin/af-cpu8" && ! -L "$workdir/root/bin/af-cpu8" ]] || \
	die 'exact Candidate AD unexpectedly contains bin/af-cpu8'
install -m 0755 "$source_dir/init" "$workdir/root/init"
install -m 0755 "$source_dir/af-cpu8" "$workdir/root/bin/af-cpu8"

find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/candidate.img"
chmod 0600 "$workdir/candidate.img"

[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die 'Candidate AF initramfs sources changed during construction'
python3 "$validator" --baseline "$baseline" --candidate "$workdir/candidate.img" \
	--source-dir "$source_dir" >/dev/null
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$workdir/candidate.img" ]] || \
	die 'atomic Candidate AF initramfs handoff failed'

printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline_sha256=%s\n' "$AD_INITRAMFS_SHA256"
printf 'changed_members=init\n'
printf 'added_members=bin/af-cpu8\n'
printf 'initramfs_baseline=exact-candidate-AD\n'
printf 'watchdog_action=open-fd3,one-handoff-ping,no-further-pings,automatic-reset\n'
printf 'cpu_write=/run/af-sys/devices/system/cpu/cpu8/online:1-once\n'
printf 'cpu9_action=validate-offline,no-write\n'
printf 'storage_access=none\n'
printf 'network_delta=none,inherited-candidate-AC-usb-service-preserved\n'
printf 'build_hardware_write=none\nflash=none\n'
