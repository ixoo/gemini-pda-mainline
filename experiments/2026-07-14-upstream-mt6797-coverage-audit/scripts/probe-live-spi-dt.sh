#!/usr/bin/env bash

# Read-only live SPI topology probe for a Gemini running Gemian.

set -euo pipefail
export LC_ALL=C

usage() {
	cat <<'EOF'
usage: probe-live-spi-dt.sh [--target USER@HOST]

The probe reads only /proc/device-tree and /sys on the target. It does not
touch SPI registers, issue transfers, change GPIOs, load drivers, or write
hardware state.
EOF
}

die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../.." && pwd)"
identity="${GEMINI_SSH_IDENTITY:-${repo_root}/artifacts/credentials/gemini_ed25519}"
target="${GEMINI_SSH_TARGET:-gemini@192.168.1.50}"

while (($#)); do
	case "$1" in
		--target)
			(($# >= 2)) || die "--target requires USER@HOST"
			target="$2"
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			die "unknown argument: $1"
			;;
	esac
done

ssh_options=(
	-o BatchMode=yes
	-o ConnectTimeout=8
	-o IdentityAgent=none
)
if [[ -r "${identity}" ]]; then
	ssh_options+=(
		-o IdentitiesOnly=yes
		-i "${identity}"
	)
fi

# shellcheck disable=SC2029
ssh "${ssh_options[@]}" "${target}" 'bash -s' <<'REMOTE'
set -euo pipefail
export LC_ALL=C

printf 'validation=live-spi-device-tree\n'
printf 'kernel=%s\n' "$(uname -a)"
printf 'model=%s\n' "$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
printf 'hardware_writes=none\n'

printf '\n[spi_nodes]\n'
for node in /proc/device-tree/soc/spi@*; do
	[ -d "${node}" ] || continue
	name="${node##*/}"
	printf 'node=%s\n' "${name}"
	for prop in compatible status reg interrupts clock-names spi-padmacro cell-index; do
		if [ -e "${node}/${prop}" ]; then
			printf '%s=' "${prop}"
			od -An -tx1 "${node}/${prop}" | tr -d ' \n'
			printf '\n'
		fi
	done
done

printf '\n[spi_masters_and_children]\n'
for master in /sys/class/spi_master/spi*; do
	[ -e "${master}" ] || continue
	master_name="${master##*/}"
	printf 'master=%s\n' "${master_name}"
	for device in "/sys/bus/spi/devices/${master_name}".*; do
		[ -e "${device}" ] || continue
		device_name="${device##*/}"
		printf 'child=%s' "${device_name}"
		if [ -r "${device}/modalias" ]; then
			printf ' modalias=%s' "$(tr -d '\n' <"${device}/modalias")"
		fi
		if [ -L "${device}/driver" ]; then
			printf ' driver=%s' "$(basename "$(readlink "${device}/driver")")"
		fi
		printf '\n'
	done
done
REMOTE
