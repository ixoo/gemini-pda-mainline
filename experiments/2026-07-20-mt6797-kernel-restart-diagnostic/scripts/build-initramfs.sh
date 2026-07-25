#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline AA_R1_INITRAMFS --output NEW_FILE\n' "$0" >&2; }

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
	die 'exact AA r1 initramfs and output are required'
for command in awk chmod cpio dirname find gzip install mkdir mktemp mv python3 \
	rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -d "$(dirname -- "$output")" ]] || die 'output parent must already exist'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output="$output_parent/$(basename -- "$output")"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$(cd -- "$script_dir/../initramfs" && pwd -P)"
validator="$script_dir/validate-initramfs.py"
expected_baseline="$(PYTHONPATH="$script_dir" python3 -c \
	'from ab_contract import AA_INITRAMFS_SHA256; print(AA_INITRAMFS_SHA256)')"
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$expected_baseline" ]] || \
	die 'baseline is not exact hardware-passed Candidate AA r1 initramfs'

sources=(init local-shell reboot x-record)
hash_sources() {
	local name
	for name in "${sources[@]}"; do
		[[ -s "$source_dir/$name" && ! -L "$source_dir/$name" ]] || \
			die "AB initramfs source missing or unsafe: $name"
		sha256sum "$source_dir/$name"
	done
	sha256sum "$validator" "$script_dir/ab_contract.py"
}
source_tree_at_start="$(hash_sources)"
workdir="$(mktemp -d "$output_parent/.candidate-ab-initramfs.XXXXXX")"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore archived `.` mode.
chmod 0755 "$workdir/root"
install -m 0755 "$source_dir/init" "$workdir/root/init"
for name in local-shell reboot x-record; do
	install -m 0755 "$source_dir/$name" "$workdir/root/bin/$name"
done
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/candidate.img"
chmod 0600 "$workdir/candidate.img"

[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die 'AB initramfs sources changed during construction'
python3 "$validator" --baseline "$baseline" --candidate "$workdir/candidate.img" \
	--source-dir "$source_dir" >/dev/null
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$workdir/candidate.img" ]] || \
	die 'atomic initramfs handoff failed'

printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline=exact-hardware-passed-candidate-aa-r1\n'
printf 'changed_members=init,bin/local-shell,bin/reboot,bin/x-record\n'
printf 'keymap_and_gate=exact-aa-r1-with-attribution-only-shell-transform\n'
printf 'manual_reboot=busybox-reboot-no-sync-force\n'
printf 'watchdog_userspace=start-none,open-none,ping-none,countdown-none,fallback-none\n'
printf 'automatic_reboot=none\nstorage_access=none\nhardware_write=none\n'
