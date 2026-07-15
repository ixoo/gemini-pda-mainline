#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Capture a bounded, read-only snapshot after a Gemini mainline boot.
# This script never flashes, reboots, binds/unbinds, scans a bus, or writes a
# device. The output is intended for the Git-ignored artifacts/ tree.

set -euo pipefail
export LC_ALL=C

usage() {
	cat <<'EOF'
Usage: collect-mainline-runtime-evidence.sh --target USER@HOST [--output DIR]
       [--kind mainline-candidate|vendor-baseline]

The SSH key defaults to artifacts/credentials/gemini_ed25519. Override it with
KEY_FILE. The remote command is read-only and uses no sudo.
EOF
}

target=""
output_dir=""
capture_kind="mainline-candidate"
while (($#)); do
	case "$1" in
		--target)
			(($# >= 2)) || { echo "--target requires USER@HOST" >&2; exit 2; }
			target=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || { echo "--output requires a directory" >&2; exit 2; }
			output_dir=$2
			shift 2
			;;
		--kind)
			(($# >= 2)) || { echo "--kind requires a capture kind" >&2; exit 2; }
			case "$2" in
				mainline-candidate|vendor-baseline) capture_kind=$2 ;;
				*) echo "unsupported capture kind: $2" >&2; exit 2 ;;
			esac
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "unknown argument: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

[[ -n "$target" ]] || { usage >&2; exit 2; }
repo_dir=$(cd "$(dirname "$0")/../../.." && pwd -P)
key_file="$repo_dir/artifacts/credentials/gemini_ed25519"
if [[ -n "${KEY_FILE:-}" ]]; then
	key_file="$KEY_FILE"
fi
[[ -r "$key_file" ]] || { echo "unreadable key: $key_file" >&2; exit 1; }

if [[ -z "$output_dir" ]]; then
	output_dir=$repo_dir/artifacts/device-inventory/$(date -u +%Y%m%dT%H%M%SZ)-mainline-runtime
fi
mkdir -p "$output_dir"
chmod 700 "$output_dir"

connect_timeout=10
if [[ -n "${SSH_CONNECT_TIMEOUT:-}" ]]; then
	connect_timeout="$SSH_CONNECT_TIMEOUT"
fi
output_file=$output_dir/mainline-runtime.txt
set +e
{
	printf 'capture=mainline-runtime-evidence\n'
	printf 'capture_kind=%s\n' "$capture_kind"
	printf 'generated_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	printf 'target=%s\n' "$target"
	printf 'hardware_write=none\n'
	printf 'remote_sudo=not_used\n'
	printf '\n[remote_read_only_snapshot]\n'
	ssh -i "$key_file" \
		-o IdentitiesOnly=yes \
		-o IdentityAgent=none \
		-o BatchMode=yes \
		-o ConnectTimeout="$connect_timeout" \
		-o ServerAliveInterval=5 \
		-o ServerAliveCountMax=2 \
		"$target" 'bash -s' <<'REMOTE'
set +e
export LC_ALL=C

redact() {
	sed -E \
		-e 's/((androidboot\.)?(serialno|imei|meid|cid|wifi_mac|bt_mac|macaddr))=[^ ]+/\1=<redacted>/Ig' \
		-e 's/([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}/<redacted-mac>/g'
}

heading() { printf '\n===== %s =====\n' "$1"; }
read_text() {
	local path=$1
	local value
	if [[ -r "$path" ]]; then
		value=$(tr '\000' ' ' < "$path" 2>/dev/null | sed 's/[[:space:]]*$//')
		# Device-tree properties are not required to carry a trailing newline.
		# Keep the key/value stream parseable when this helper follows printf.
		printf '%s\n' "$value"
	else
		printf 'unreadable\n'
	fi
}

read_hex() {
	local path=$1
	if [[ -r "$path" ]]; then
		od -An -tx1 -v "$path" 2>/dev/null | tr -d ' \n'
	else
		printf 'unreadable'
	fi
}

heading identity
uname -a 2>&1 | redact
printf 'machine='; read_text /proc/sys/kernel/hostname
printf 'kernel_release='; uname -r 2>/dev/null
printf 'model='; read_text /proc/device-tree/model
printf 'compatible='; read_text /proc/device-tree/compatible
printf 'cmdline='; read_text /proc/cmdline | redact

heading memory_and_cpus
grep -E '^(MemTotal|MemAvailable|CmaTotal|CmaFree):' /proc/meminfo 2>/dev/null || true
grep -E '^(processor|BogoMIPS|Features|CPU architecture|model name):' /proc/cpuinfo 2>/dev/null || true

heading cpu_policy_and_handoff
for path in /sys/devices/system/cpu/online /sys/devices/system/cpu/possible \
	/sys/devices/system/cpu/present /sys/devices/system/cpu/cpu*/cpufreq/scaling_driver \
	/sys/devices/system/cpu/cpufreq/policy*/scaling_driver \
	/sys/devices/system/cpu/cpufreq/policy*/scaling_available_governors; do
	for item in $path; do
		[[ -e "$item" ]] || continue
		printf '%s=' "$item"
		read_text "$item" | redact
	done
done

heading reserved_memory_and_iomem
for node in /sys/firmware/devicetree/base/reserved-memory/*; do
	[[ -d "$node" ]] || continue
	name=${node##*/}
	printf 'reserved_node=%s\n' "$name"
	for property in reg no-map reusable; do
		path=$node/$property
		[[ -e "$path" ]] || continue
		if [[ "$property" == reg ]]; then
			printf 'reserved_%s_%s=%s\n' "$name" "$property" "$(read_hex "$path")"
		else
			printf 'reserved_%s_%s=present\n' "$name" "$property"
		fi
	done
done
grep -Ei 'System RAM|reserved|ccci|consys|spm|scp|framebuffer|atf' /proc/iomem 2>/dev/null | redact || true

heading interrupts
grep -Ei 'mtk|mmc|serial|uart|watchdog|wdt|pwrap|mt6351|pinctrl|psci|arch_timer|timer' \
	/proc/interrupts 2>/dev/null || true

heading modules_and_devices
if [[ -r /proc/modules ]]; then
	printf 'proc_modules=present\n'
	awk '{print $1}' /proc/modules | sort | grep -E '^(mtk|mt6797|mt6351|mt6397|pinctrl|8250|serial|mmc|snd|panfrost|drm|usb|fusb|auxadc|thermal)' || true
else
	printf 'proc_modules=absent\n'
fi
for bus in platform mmc i2c spi usb; do
	printf '[%s]\n' "$bus"
	find "/sys/bus/$bus/devices" -maxdepth 1 -mindepth 1 -type l -printf '%f\n' 2>/dev/null \
		| sort | grep -Ei 'mtk|mt6797|mt6351|mt6397|serial|uart|mmc|watchdog|wdt|pwrap|pinctrl|usb|fusb|thermal|auxadc' || true
done

heading console_and_boot
for path in /sys/class/tty/ttyS0/uevent /sys/class/tty/ttyS0/device/modalias \
	/sys/class/tty/ttyS0/device/driver/module /sys/firmware/devicetree/base/chosen/stdout-path; do
	printf '%s=' "$path"
	read_text "$path" | redact
done
printf 'dmesg_access='
if dmesg >/dev/null 2>&1; then
	printf 'yes\n'
		dmesg --color=never 2>/dev/null | tail -n 120 | redact
else
	printf 'no\n'
fi

heading storage_and_power
for path in /sys/block/mmcblk0/device/type /sys/block/mmcblk0/device/name \
	/sys/block/mmcblk0/device/manfid /sys/block/mmcblk0/ro \
	/sys/block/mmcblk0/device/oemid /sys/block/mmcblk0/device/date \
	/sys/block/mmcblk0/device/hwrev /sys/class/regulator/regulator.*/name \
	/sys/class/regulator/regulator.*/state /sys/class/regulator/regulator.*/microvolts \
	/sys/kernel/debug/mmc0/ios; do
	for item in $path; do
		[[ -e "$item" ]] || continue
		printf '%s=' "$item"
		read_text "$item" | redact
	done
done

heading watchdog_and_platform_drivers
for path in /sys/class/watchdog/watchdog*/identity \
	/sys/class/watchdog/watchdog*/state /sys/class/watchdog/watchdog*/timeout \
	/sys/class/watchdog/watchdog*/pretimeout /sys/class/watchdog/watchdog*/bootstatus \
	/sys/class/watchdog/watchdog*/nowayout; do
	for item in $path; do
		[[ -e "$item" ]] || continue
		printf '%s=' "$item"
		read_text "$item" | redact
	done
done
for device in /sys/bus/platform/devices/*; do
	[[ -L "$device" ]] || continue
	name=${device##*/}
	case "$name" in
		*mmc*|*msdc*|*serial*|*uart*|*pwrap*|*pmic*|*rtc*|*watchdog*|*wdt*|*toprgu*|*pinctrl*|*m4u*|*gce*|*usb*|*imgsys*|*mdcldma*|*consys*)
			printf 'platform_device=%s\n' "$name"
			if [[ -L "$device/driver" ]]; then
				printf 'platform_driver=%s\n' "$(readlink -f "$device/driver")"
			else
				printf 'platform_driver=unbound\n'
			fi
			;;
	esac
done

heading power_domains_and_clocks
for root in /sys/kernel/debug/pm_genpd /sys/kernel/debug/clk; do
	if [[ -r "$root/summary" ]]; then
		printf '[%s/summary]\n' "$root"
		sed -n '1,240p' "$root/summary" 2>/dev/null | redact
	fi
done

printf '\n===== safety =====\n'
printf 'remote_actions=read_only\n'
printf 'runtime_kernel_release='; uname -r 2>/dev/null
printf 'runtime_mainline_boot=classify_from_kernel_release_and_final_dtb\n'
REMOTE
} > "$output_file"
capture_status=$?
set -e
chmod 600 "$output_file"
if ((capture_status != 0)); then
	printf 'capture_status=ssh_failed\n' >> "$output_file"
	printf 'capture=%s status=ssh_failed\n' "$output_file" >&2
	exit "$capture_status"
fi
printf 'capture=%s\n' "$output_file"
