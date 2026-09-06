#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Stream only bounded status and digest tokens.  The host never forwards this
# stream; digest tokens are captured into its ignored mode-0700 attempt dir.

set -eu

[ "$#" -eq 3 ] || exit 64
expected_release=$1
expected_arch=$2
expected_boot=$3

read_boot() { tr -d '\n' </proc/sys/kernel/random/boot_id; }
require_identity() {
	stage=$1
	release=$(uname -r 2>/dev/null) || exit 65
	arch=$(uname -m 2>/dev/null) || exit 65
	boot=$(read_boot) || exit 65
	[ "$release" = "$expected_release" ] || exit 65
	[ "$arch" = "$expected_arch" ] || exit 65
	[ "$boot" = "$expected_boot" ] || exit 65
	printf 'release_%s=%s\n' "$stage" "$release"
	printf 'arch_%s=%s\n' "$stage" "$arch"
	printf 'boot_id_%s=%s\n' "$stage" "$boot"
}

require_identity start

lxc_raw=$(lxc-info -n android -sH -pH 2>/dev/null) || exit 66
# shellcheck disable=SC2046 # exactly two whitespace-delimited lxc-info fields
set -- $(printf '%s\n' "$lxc_raw")
[ "$#" -eq 2 ] || exit 66
[ "$1" = RUNNING ] || exit 66
case $2 in ''|*[!0-9]*) exit 66;; esac
pid=$2
proc=/proc/$pid
root=$proc/root

printf 'container_state=running\n'
printf 'pid_status=one\n'
# The host must durably record consumption and send this exact ACK.  No mount
# or fixed-file read occurs until the barrier has passed.
printf 'admission_ready=yes\n'
IFS= read -r gate || exit 67
[ "$gate" = "GEMINI-WIFI-NVRAM-CONSUME-v1" ] || exit 67

mountinfo=$proc/mountinfo
mount_status=valid
nv_count=0
data_count=0
relation=no
if [ ! -r "$mountinfo" ] || [ -L "$mountinfo" ]; then
	mount_status=unreadable
else
		mount_chunk=$(dd if="$mountinfo" bs=262145 count=1 2>/dev/null; rc=$?; printf '\001'; exit "$rc") || mount_status=unreadable
		mount_data=${mount_chunk%?}
		mount_bytes=$(printf '%s' "$mount_data" | wc -c | tr -d ' ') || mount_bytes=0
	case $mount_bytes in ''|*[!0-9]*) mount_status=unreadable;;
	*)
		if [ "$mount_bytes" -gt 262144 ]; then
			mount_status=invalid
		else
			if [ "$mount_status" = valid ]; then
				# shellcheck disable=SC2046 # the awk result is exactly three fields
				set -- $(printf '%s\n' "$mount_data" | awk '
					$5 == "/nvdata" { n++; nd=$3; nr=$4 }
					$5 == "/data/nvram" { d++; dd=$3; dr=$4 }
					END {
						if (n > 2 || d > 2) exit 2
						printf "%d %d %s\n", n + 0, d + 0,
							(n == 1 && d == 1 && nd == dd && nr == dr) ? "yes" : "no"
					}') || mount_status=invalid
				if [ "$mount_status" = valid ] && [ "$#" -eq 3 ]; then
					nv_count=$1; data_count=$2; relation=$3
				else
					mount_status=invalid
					nv_count=0; data_count=0; relation=no
				fi
			fi
		fi
	;; esac
fi
printf 'mountinfo_status=%s\n' "$mount_status"
printf 'mount_nvdata_count=%s\n' "$nv_count"
printf 'mount_data_nvram_count=%s\n' "$data_count"
printf 'mount_relation=%s\n' "$relation"

file_status() {
	path=$1
	if [ -L "$path" ]; then printf 'symlink'; return; fi
	if [ ! -e "$path" ]; then printf 'missing'; return; fi
	if [ ! -f "$path" ]; then printf 'nonregular'; return; fi
	if [ ! -r "$path" ]; then printf 'unreadable'; return; fi
	printf 'present'
}

emit_wifi() {
	path=$root/data/nvram/APCFG/APRDEB/WIFI
	status=$(file_status "$path")
	size=0
	if [ "$status" = present ]; then
		size=$(stat -c '%s' "$path" 2>/dev/null) || status=read-error
		case $size in ''|*[!0-9]*) status=read-error; size=0;; esac
		[ "$status" = present ] && [ "$size" -gt 515 ] && size=515
	fi
	envelope=not-checked
	digest=
	if [ "$status" = present ] && [ "$size" -eq 514 ]; then
		if od -An -tu1 -v "$path" 2>/dev/null | awk '
			function bxor(a,b, r,i,aa,bb) {
				r=0; for (i=0; i<8; i++) { aa=a%2; bb=b%2;
					if (aa != bb) r += 2^i; a=int(a/2); b=int(b/2) }
				return r
			}
			{ for (j=1; j<=NF; j++) {
				if (count < 512) { if (count % 2 == 0) calc=(calc+$j)%256;
					else calc=bxor(calc+0,$j); }
				else if (count == 512) marker=$j; else if (count == 513) check_trailer=$j;
				count++
			} }
			END { if (count != 514 || marker != 170 || calc != check_trailer) exit 1 }
		'; then envelope=valid; else envelope=invalid; fi
	else
		[ "$status" = present ] && envelope=invalid
	fi
	if [ "$status" = present ] && [ "$size" -eq 514 ]; then
		digest=$(sha256sum "$path" 2>/dev/null | awk 'NF == 2 { print $1 }') || status=read-error
		case $digest in
			''|*[!0123456789abcdef]*) status=read-error; digest=;;
		esac
	fi
	printf 'wifi_status=%s\n' "$status"
	printf 'wifi_size=%s\n' "$size"
	printf 'wifi_envelope=%s\n' "$envelope"
	[ -n "$digest" ] && printf 'wifi_digest=%s\n' "$digest"
}

emit_binary() {
	label=$1
	path=$2
	status=$(file_status "$path")
	size=0
	digest=
	if [ "$status" = present ]; then
		size=$(stat -c '%s' "$path" 2>/dev/null) || status=read-error
		case $size in ''|*[!0-9]*) status=read-error; size=0;; esac
		if [ "$status" = present ] && [ "$size" -gt 4194304 ]; then
			status=oversize
			size=4194305
		fi
		if [ "$status" = present ]; then
			digest=$(sha256sum "$path" 2>/dev/null | awk 'NF == 2 { print $1 }') || status=read-error
			case $digest in ''|*[!0123456789abcdef]*) status=read-error; digest=;; esac
		fi
	fi
	printf '%s_status=%s\n' "$label" "$status"
	printf '%s_size=%s\n' "$label" "$size"
	[ -n "$digest" ] && printf '%s_digest=%s\n' "$label" "$digest"
}

emit_wifi
emit_binary daemon "$root/vendor/bin/nvram_daemon"

emit_binary lib "$root/vendor/lib/libnvram.so"

require_identity end
