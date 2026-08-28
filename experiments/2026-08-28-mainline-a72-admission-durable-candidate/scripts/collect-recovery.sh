#!/usr/bin/env bash

# Recover the exact retained admission records after the candidate resets to Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly CANDIDATE_SHA256=60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1
readonly CLASSIFIER_SHA256=ff9ece359c3b5afd8852d2e4b09e14abc339dd32950219c001f54119a442d112

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --target gemini@192.168.1.50 --deployment-dir DIR --output-dir DIR\n' "$0"
}
for command in awk chmod dirname grep mkdir mktemp mv python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

target=
deployment_dir=
output_dir=
while (($#)); do
	case "$1" in
	--target) target=${2:-}; shift 2 ;;
	--deployment-dir) deployment_dir=${2:-}; shift 2 ;;
	--output-dir) output_dir=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ "$target" == "$EXPECTED_TARGET" && -n "$deployment_dir" && -n "$output_dir" ]] || {
	usage >&2
	exit 2
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
classifier="$script_dir/classify-recovery.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
case "$deployment_dir" in /*) ;; *) deployment_dir="$repo_root/${deployment_dir#./}" ;; esac
case "$output_dir" in /*) ;; *) output_dir="$repo_root/${output_dir#./}" ;; esac
case "$deployment_dir/" in "$repo_root/artifacts/"*) ;; *) die 'deployment directory must be below artifacts' ;; esac
case "$output_dir/" in "$repo_root/artifacts/"*) ;; *) die 'output directory must be below artifacts' ;; esac
summary="$deployment_dir/deployment-summary.txt"
for input in "$classifier" "$identity" "$summary"; do
	[[ -f "$input" && ! -L "$input" ]] || die "missing or unsafe input: $input"
done
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] ||
	die 'recovery classifier changed'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
single_value() {
	local key=$1 file=$2
	awk -F= -v key="$key" '$1 == key {print substr($0, length(key) + 2); n++} END {exit n != 1}' "$file"
}
install_boot_id=$(single_value boot_id "$summary") || die 'deployment boot ID missing or duplicated'
installed_candidate=$(single_value candidate_sha256 "$summary") || die 'deployment candidate missing or duplicated'
readback_candidate=$(single_value readback_sha256 "$summary") || die 'deployment readback missing or duplicated'
[[ "$install_boot_id" =~ ^[0-9a-f-]{36}$ ]] || die 'deployment boot ID malformed'
[[ "$installed_candidate" == "$CANDIDATE_SHA256" &&
	"$readback_candidate" == "$CANDIDATE_SHA256" ]] || die 'deployment identity changed'

output_parent=$(dirname -- "$output_dir")
mkdir -p "$output_parent"
[[ ! -e "$output_dir" && ! -L "$output_dir" ]] || die 'refusing to overwrite output directory'
workdir=$(mktemp -d "$output_parent/.a72-admission-recovery.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
"${ssh_command[@]}" "$target" 'sudo -n /bin/bash -s' >"$workdir/remote-capture.txt" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in cat dd find id lsblk od readlink sha256sum tr uname wc; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || fail 'malformed boot ID'
rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2 row'
read -r boot2 label type size ro mountpoint extra <<<"$rows"
[[ "$boot2" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && "$label" == boot2 &&
	"$type" == part && "$size" == 16777216 && "$ro" == 0 &&
	-z "${mountpoint:-}" && -z "${extra:-}" && -b "$boot2" ]] ||
	fail 'boot2 live GPT identity changed or is mounted'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$boot2" ]] ||
	fail 'boot2 by-partlabel disagrees with GPT'
hex_at() {
	local address=$1 count=$2
	dd if=/dev/mem bs=1 skip="$address" count="$count" status=none |
		od -An -v -tx1 | tr -d ' \n'
}
printf 'boot_id=%s\n' "$boot_id"
printf 'kernel_release=%s\n' "$(uname -r)"
printf 'architecture=%s\n' "$(uname -m)"
printf 'model=%s\n' "$(tr -d '\000\n' </proc/device-tree/model)"
printf 'compatible=%s\n' "$(tr '\000' ',' </proc/device-tree/compatible)"
printf 'boot2_target=%s\n' "$boot2"
printf 'boot2_size=%s\n' "$size"
printf 'boot2_sha256=%s\n' "$(sha256sum "$boot2" | awk '{print $1}')"
printf 'pstore_files=%s\n' "$(find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')"
printf 'ledger_hex='; hex_at $((0x44410000)) 84; printf '\n'
printf 'entry_hex='; hex_at $((0x44411000)) 4096; printf '\n'
printf 'terminal_hex='; hex_at $((0x44412000)) 4096; printf '\n'
printf 'device_storage_writes=none\nretained_ram_writes=none\nreboot_request=none\n'
REMOTE

capture="$workdir/remote-capture.txt"
runtime_boot_id=$(single_value boot_id "$capture") || die 'runtime boot ID missing or duplicated'
boot2_sha256=$(single_value boot2_sha256 "$capture") || die 'runtime boot2 hash missing or duplicated'
ledger_hex=$(single_value ledger_hex "$capture") || die 'runtime ledger missing or duplicated'
entry_hex=$(single_value entry_hex "$capture") || die 'runtime entry trace missing or duplicated'
terminal_hex=$(single_value terminal_hex "$capture") || die 'runtime terminal trace missing or duplicated'
[[ "$runtime_boot_id" =~ ^[0-9a-f-]{36}$ && "$runtime_boot_id" != "$install_boot_id" ]] ||
	die 'no changed Gemian boot ID after deployment'
[[ "$boot2_sha256" == "$CANDIDATE_SHA256" ]] || die 'installed boot2 identity changed'
[[ "$ledger_hex" =~ ^[0-9a-f]{168}$ && "$entry_hex" =~ ^[0-9a-f]{8192}$ &&
	"$terminal_hex" =~ ^[0-9a-f]{8192}$ ]] || die 'retained capture length changed'
python3 "$classifier" --ledger-hex "$ledger_hex" --entry-hex "$entry_hex" \
	--terminal-hex "$terminal_hex" >"$workdir/classification.txt" ||
	die 'retained records rejected attribution'
{
	printf 'experiment=2026-08-28-mainline-a72-admission-durable-candidate\n'
	printf 'installed_candidate_sha256=%s\n' "$CANDIDATE_SHA256"
	printf 'deployment_boot_id=%s\nruntime_boot_id=%s\n' "$install_boot_id" "$runtime_boot_id"
	grep -E '^(kernel_release|architecture|model|compatible|boot2_target|boot2_size|boot2_sha256|pstore_files|device_storage_writes|retained_ram_writes|reboot_request)=' "$capture"
	cat "$workdir/classification.txt"
} >"$workdir/recovery-summary.txt"
(
	cd "$workdir"
	sha256sum classification.txt recovery-summary.txt remote-capture.txt >SHA256SUMS
	sha256sum --check --strict SHA256SUMS >/dev/null
)
chmod 0600 "$workdir"/*
mv "$workdir" "$output_dir"
workdir=
trap - EXIT HUP INT TERM
printf 'recovery=%s\n' "$output_dir"
grep -E '^(runtime_classification|admission_trace_state|admission_trace_detail|transition_ledger_state|result)=' "$output_dir/recovery-summary.txt"
printf 'device_storage_writes=none\nretained_ram_writes=none\n'
