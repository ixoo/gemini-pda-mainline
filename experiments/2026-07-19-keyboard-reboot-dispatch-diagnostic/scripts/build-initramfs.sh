#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline Y_INITRAMFS --output FILE --dispatch-result FILE\n' "$0" >&2
}

baseline=
output=
dispatch_result=
while (($#)); do
	case "$1" in
	--baseline|--output|--dispatch-result)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline) baseline=$2 ;;
		--output) output=$2 ;;
		--dispatch-result) dispatch_result=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run inside the Linux development VM'
case "$(uname -m)" in
aarch64|arm64) ;;
*) die 'exact BusyBox dispatch validation requires a Linux aarch64 host' ;;
esac
[[ -f "$baseline" && ! -L "$baseline" && -n "$output" && \
	-n "$dispatch_result" ]] || die 'exact Candidate Y initramfs and both outputs are required'
for command in awk chmod cpio dirname find gzip install mkdir mktemp mv python3 \
	rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
readonly Y_INITRAMFS_SHA256=11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$Y_INITRAMFS_SHA256" ]] || \
	die 'baseline is not exact Candidate Y initramfs'

canonical_output() {
	local requested=$1
	[[ -d "$(dirname -- "$requested")" ]] || die 'output parent must already exist'
	printf '%s/%s\n' "$(cd -- "$(dirname -- "$requested")" && pwd -P)" \
		"$(basename -- "$requested")"
}
output="$(canonical_output "$output")"
dispatch_result="$(canonical_output "$dispatch_result")"
[[ "$output" != "$dispatch_result" ]] || die 'initramfs and dispatch result must differ'
for destination in "$output" "$dispatch_result"; do
	[[ ! -e "$destination" && ! -L "$destination" ]] || \
		die "refusing to overwrite $destination"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$(cd -- "$script_dir/../initramfs" && pwd -P)"
sources=(init local-shell reboot x-record reboot-dispatch.env)
hash_sources() {
	local source
	for source in "${sources[@]}"; do
		[[ -f "$source_dir/$source" && ! -L "$source_dir/$source" ]] || \
			die "overlay source missing or unsafe: $source"
		sha256sum "$source_dir/$source"
	done
}
source_tree_at_start="$(hash_sources)"
workdir="$(mktemp -d /tmp/candidate-z-initramfs.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore the archived `.`
# mode. Canonical Candidate Y records that member as 0755.
chmod 0755 "$workdir/root"
install -m 0755 "$source_dir/init" "$workdir/root/init"
for source in local-shell reboot x-record; do
	install -m 0755 "$source_dir/$source" "$workdir/root/bin/$source"
done
install -m 0444 "$source_dir/reboot-dispatch.env" \
	"$workdir/root/bin/reboot-dispatch.env"
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/candidate.img"
chmod 0600 "$workdir/candidate.img"
[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die 'overlay sources changed during construction'
python3 "$script_dir/validate-initramfs.py" --baseline "$baseline" \
	--candidate "$workdir/candidate.img" --source-dir "$source_dir" >/dev/null
python3 "$script_dir/validate-ash-dispatch.py" \
	--initramfs "$workdir/candidate.img" >"$workdir/ash-dispatch-validation.txt"
chmod 0600 "$workdir/ash-dispatch-validation.txt"

mv --no-clobber --no-target-directory -- \
	"$workdir/ash-dispatch-validation.txt" "$dispatch_result"
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && ! -L "$output" && -f "$dispatch_result" && \
	! -L "$dispatch_result" && ! -e "$workdir/candidate.img" && \
	! -e "$workdir/ash-dispatch-validation.txt" ]] || die 'atomic output handoff failed'
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline=exact-candidate-y\n'
printf 'changed_members=init,bin/local-shell,bin/reboot,bin/x-record\n'
printf 'added_member=bin/reboot-dispatch.env:0444\n'
printf 'marker=GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z\n'
printf 'reboot_dispatch=ENV-alias-absolute-wrapper\n'
printf 'dispatch_validation=exact-busybox-dynamic-linux-aarch64\n'
printf 'watchdog_ownership=typed-only\nsoftware_reboot_fallback=none\n'
printf 'hardware_write=none\n'
