#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline X_INITRAMFS --output FILE\n' "$0" >&2; }

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
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run inside the Linux development VM'
[[ -f "$baseline" && ! -L "$baseline" && -n "$output" ]] || \
	die 'exact Candidate X initramfs and output are required'
for command in awk chmod cpio dirname find gzip install mkdir mktemp mv python3 \
	rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
readonly X_INITRAMFS_SHA256=b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$X_INITRAMFS_SHA256" ]] || \
	die 'baseline is not exact Candidate X initramfs'
[[ -d "$(dirname -- "$output")" ]] || die 'output parent must already exist'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output="$output_parent/$(basename -- "$output")"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$(cd -- "$script_dir/../initramfs" && pwd -P)"
sources=(init local-shell reboot x-record)
hash_sources() {
	local source
	for source in "${sources[@]}"; do
		[[ -f "$source_dir/$source" && ! -L "$source_dir/$source" ]] || \
			die "overlay source missing or unsafe: $source"
		sha256sum "$source_dir/$source"
	done
}
source_tree_at_start="$(hash_sources)"
workdir="$(mktemp -d /tmp/candidate-y-initramfs.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore the archived `.`
# mode. Canonical Candidate X records that member as 0755.
chmod 0755 "$workdir/root"
install -m 0755 "$source_dir/init" "$workdir/root/init"
for source in local-shell reboot x-record; do
	install -m 0755 "$source_dir/$source" "$workdir/root/bin/$source"
done
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
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$workdir/candidate.img" ]] || \
	die 'atomic initramfs handoff failed'
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline=exact-candidate-x\nchanged_members=init,bin/local-shell,bin/reboot,bin/x-record\n'
printf 'marker=GEMINI_KEYBOARD_TYPED_WATCHDOG_REBOOT_20260719_Y\n'
printf 'watchdog_ownership=typed-only\nsoftware_reboot_fallback=none\n'
printf 'hardware_write=none\n'
