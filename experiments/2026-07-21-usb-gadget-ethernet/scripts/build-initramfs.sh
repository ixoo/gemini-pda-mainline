#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly AB_INITRAMFS_SHA256=b57dc3143e7ca7df90d742bcacc692221b4d7b6d346e5192d7bc68acaac00ea7
readonly BUSYBOX_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --baseline AB_INITRAMFS --output NEW_FILE\n' "$0" >&2; }

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

[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die 'run on the Linux AArch64 recovery VM'
[[ -f "$baseline" && ! -L "$baseline" && -n "$output" ]] || \
	die 'exact Candidate AB initramfs and output are required'
for command in awk basename chmod cpio dirname find grep gzip install ln mkdir mktemp mv \
	python3 rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$AB_INITRAMFS_SHA256" ]] || \
	die 'baseline is not the exact hardware-passed Candidate AB initramfs'
[[ -d "$(dirname -- "$output")" ]] || die 'output parent must already exist'
output_parent="$(cd -- "$(dirname -- "$output")" && pwd -P)"
output="$output_parent/$(basename -- "$output")"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_dir="$(cd -- "$script_dir/../initramfs" && pwd -P)"
validator="$script_dir/validate-initramfs.py"
sources=(init ac-record usb-net usb-shell)

hash_sources() {
	local name
	for name in "${sources[@]}"; do
		[[ -s "$source_dir/$name" && ! -L "$source_dir/$name" ]] || \
			die "AC initramfs source missing or unsafe: $name"
		sha256sum "$source_dir/$name"
	done
	sha256sum "$validator" "${BASH_SOURCE[0]}"
}

source_tree_at_start="$(hash_sources)"
workdir="$(mktemp -d "$output_parent/.candidate-ac-initramfs.XXXXXX")"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore archived `.` mode.
chmod 0755 "$workdir/root"

busybox="$workdir/root/bin/busybox"
[[ -f "$busybox" && ! -L "$busybox" && -x "$busybox" ]] || \
	die 'exact AB BusyBox is missing or not executable'
[[ "$(sha256sum "$busybox" | awk '{print $1}')" == "$BUSYBOX_SHA256" ]] || \
	die 'Candidate AB BusyBox bytes changed'
available="$("$busybox" --list)"
for applet in ip nc ping; do
	grep -Fxq "$applet" <<<"$available" || die "BusyBox applet missing: $applet"
	help="$("$busybox" "$applet" --help 2>&1)" || \
		die "BusyBox applet execution failed: $applet"
	grep -Fq 'Usage:' <<<"$help" || die "BusyBox applet help is malformed: $applet"
	case "$applet" in
	ip)
		if ! grep -Fq 'address' <<<"$help" || ! grep -Fq 'link' <<<"$help"; then
			die 'BusyBox ip lacks address/link support'
		fi
		;;
	nc)
		for token in '(use -ll with -e for persistent server)' '-p PORT' '-e PROG'; do
			grep -Fq -- "$token" <<<"$help" || die "BusyBox nc lacks contract: $token"
		done
		;;
	esac
done

install -m 0755 "$source_dir/init" "$workdir/root/init"
for name in ac-record usb-net usb-shell; do
	install -m 0755 "$source_dir/$name" "$workdir/root/bin/$name"
done
for applet in ip nc ping; do
	[[ ! -e "$workdir/root/bin/$applet" && ! -L "$workdir/root/bin/$applet" ]] || \
		die "refusing to replace inherited archive member: bin/$applet"
	ln -s busybox "$workdir/root/bin/$applet"
done

find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/candidate.img"
chmod 0600 "$workdir/candidate.img"

[[ "$(hash_sources)" == "$source_tree_at_start" ]] || \
	die 'AC initramfs sources changed during construction'
python3 "$validator" --baseline "$baseline" --candidate "$workdir/candidate.img" \
	--source-dir "$source_dir" >/dev/null
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && ! -L "$output" && ! -e "$workdir/candidate.img" ]] || \
	die 'atomic initramfs handoff failed'

printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline_sha256=%s\n' "$AB_INITRAMFS_SHA256"
printf 'changed_members=init\n'
printf 'added_members=bin/ac-record,bin/ip,bin/nc,bin/ping,bin/usb-net,bin/usb-shell\n'
printf 'busybox_sha256=%s\n' "$BUSYBOX_SHA256"
printf 'busybox_direct_execution=ip,nc,ping\n'
printf 'runtime_networking=usb0-static-10.15.19.82/24\n'
printf 'tcp_service=nc-ll-port-2323-usb-shell\n'
printf 'authentication=none\nencryption=none\ndirect_link_only=yes\n'
printf 'dhcp=none\nroutes=none\nforwarding=none\nbridge=none\nipv6=none\n'
printf 'storage_access=none\nwatchdog_userspace=none\nautomatic_reboot=none\n'
