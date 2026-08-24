#!/usr/bin/env bash

# Collect one bounded, read-only, changed-ID Gemian recovery after boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly CLASSIFIER_SHA256=5250345332b75511dc30b3e8b5b743e78a0ae8d96214eb8fd89ae4e0eb30ef3a
readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly CANDIDATE_SHA256=e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a
readonly DEPLOYMENT_BOOT_ID=6ac4e0b6-2979-4a5b-851c-af7282fec216
readonly OUTPUT_NAME=a72-global-initcall-attempt-1-recovery

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --output artifacts/runtime-captures/%s\n' "$0" "$OUTPUT_NAME"
}

output=
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires a value'
		[[ -z "$output" ]] || die 'duplicate --output'
		output=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage >&2; exit 2; }
for command in awk basename chmod dirname git grep mktemp mv python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
classifier="$script_dir/classify-recovery.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"
for input in "$classifier" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "input is missing or unsafe: $input"
done
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] ||
	die 'recovery classifier identity changed'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(basename -- "$output")" == "$OUTPUT_NAME" ]] || die 'output child identity changed'
[[ "$(dirname -- "$output")" == "$private_root" ]] ||
	die 'output must remain directly below the private runtime-capture root'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

stage=$(mktemp -d "$private_root/.a72-global-initcall-recovery.XXXXXXXX")
cleanup() { [[ ! -d "${stage:-}" ]] || rm -rf -- "$stage"; }
trap cleanup EXIT HUP INT TERM
capture="$stage/retained-record.txt"
classification="$stage/classification.txt"
: >"$capture"
chmod 0600 "$capture"
ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=3 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
"${ssh_command[@]}" "$EXPECTED_TARGET" \
	"sudo -n env EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_DEPLOYMENT_BOOT_ID='$DEPLOYMENT_BOOT_ID' /bin/bash -s" \
	>"$capture" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk base64 basename blockdev cat dd dmesg findmnt grep head id lsblk od readlink sha256sum stat tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -r)" == 3.18.41+ && "$(uname -m)" == aarch64 ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ &&
	"$boot_id" != "$EXPECTED_DEPLOYMENT_BOOT_ID" ]] || fail 'recovery boot ID did not change'

rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2 row'
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$label" == boot2 && "$type" == part && "$size" == 16777216 && "$ro" == 0 ]] ||
	fail 'boot2 identity changed'
[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]] ||
	fail 'boot2 is mounted or invalid'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] ||
	fail 'boot2 by-partlabel disagrees with GPT'
[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 &&
	"$(blockdev --getsize64 "$target")" == 16777216 ]] || fail 'boot2 geometry changed'
root=$(readlink -f "$(findmnt -n -o SOURCE /)")
[[ "$root" == /dev/mmcblk0p29 && "$root" != "$target" ]] || fail 'active root changed'
[[ "$target" == /dev/mmcblk0p30 ]] || fail 'boot2 partition number changed unexpectedly'
boot2_sha256=$(sha256sum "$target" | awk '{print $1}')
[[ "$boot2_sha256" == "$EXPECTED_CANDIDATE" ]] || fail 'boot2 candidate changed'
[[ -c /dev/mem ]] || fail '/dev/mem is unavailable'

record_1_header=$(dd if=/dev/mem bs=1 skip=$((0x44410000)) count=12 status=none |
	od -An -tx1 | tr -d ' \n')
record_2_header=$(dd if=/dev/mem bs=1 skip=$((0x44411000)) count=12 status=none |
	od -An -tx1 | tr -d ' \n')
record_1_b64=$(dd if=/dev/mem bs=1 skip=$((0x44410000)) count=4096 status=none |
	base64 | tr -d '\n')
record_2_b64=$(dd if=/dev/mem bs=1 skip=$((0x44411000)) count=4096 status=none |
	base64 | tr -d '\n')

pstore_type=$(findmnt -n -T /sys/fs/pstore -o FSTYPE 2>/dev/null || true)
[[ "$pstore_type" == pstore ]] || fail 'pstore is not mounted'
pstore_metadata=$({
	pstore_file_count=0
	pstore_bytes=0
	for path in /sys/fs/pstore/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		bytes=$(stat -c '%s' "$path")
		[[ "$bytes" =~ ^[0-9]+$ ]] || fail 'malformed pstore file size'
		pstore_file_count=$((pstore_file_count + 1))
		pstore_bytes=$((pstore_bytes + bytes))
		(( pstore_file_count <= 64 && pstore_bytes <= 4194304 )) ||
			fail 'bounded pstore recovery limit exceeded'
		printf '%s %s\n' "$(basename "$path")" "$bytes"
	done
	printf '__COUNT__=%s\n' "$pstore_file_count"
})
pstore_file_count=$(printf '%s\n' "$pstore_metadata" | awk -F= '$1 == "__COUNT__" {print $2}')
pstore_file_metadata_b64=$(printf '%s\n' "$pstore_metadata" |
	awk '!/^__COUNT__=/' | base64 | tr -d '\n')
pstore_payload_b64=$({
	for path in /sys/fs/pstore/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		cat "$path"
	done
} | base64 | tr -d '\n')

ramoops_dmesg=$(dmesg | grep -Ei 'pstore|ramoops|persistent ram' | head -n 256 || true)
ramoops_registration_lines=$(printf '%s\n' "$ramoops_dmesg" |
	grep -Eic 'ramoops|persistent ram' || true)
ramoops_parameters=$({
	for path in /sys/module/ramoops/parameters/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		printf '%s=' "$(basename "$path")"
		head -c 4096 "$path"
		printf '\n'
	done
})

printf 'recovery_kernel=%s\nrecovery_architecture=%s\nrecovery_boot_id=%s\n' \
	"$(uname -r)" "$(uname -m)" "$boot_id"
printf 'active_root=%s\nboot2_device=%s\nboot2_full_sha256=%s\n' \
	"$root" "$target" "$boot2_sha256"
printf 'pstore_mounted=yes\npstore_file_count=%s\n' "$pstore_file_count"
printf 'pstore_file_metadata_b64=%s\npstore_payload_b64=%s\n' \
	"$pstore_file_metadata_b64" "$pstore_payload_b64"
printf 'record_1_size=4096\nrecord_1_header=%s\nrecord_1_b64=%s\n' \
	"$record_1_header" "$record_1_b64"
printf 'record_2_size=4096\nrecord_2_header=%s\nrecord_2_b64=%s\n' \
	"$record_2_header" "$record_2_b64"
printf 'ramoops_registration_lines=%s\n' "$ramoops_registration_lines"
printf 'ramoops_dmesg_b64=%s\n' "$(printf '%s' "$ramoops_dmesg" | base64 | tr -d '\n')"
printf 'ramoops_parameters_b64=%s\n' "$(printf '%s' "$ramoops_parameters" | base64 | tr -d '\n')"
printf 'device_memory_writes=none\ndevice_partition_writes=none\n'
REMOTE

python3 "$classifier" "$capture" >"$classification"
grep -Eq '^runtime_classification=(before-subsys-init-or-writer-refused|subsys-init-only|subsys-and-fs-initcalls)$' \
	"$classification" || die 'recovery did not classify'
(
	cd "$stage"
	sha256sum classification.txt retained-record.txt >SHA256SUMS
	sha256sum --check --strict SHA256SUMS >/dev/null
)
chmod 0600 "$stage"/*
mv "$stage" "$output"
stage=
trap - EXIT HUP INT TERM
grep -E '^(runtime_classification|runtime_reason|selected_next|retained_records_1_2|cpu8_cpu9_admission|claim_scope)=' \
	"$output/classification.txt"
printf 'capture=%s\ndevice_memory_writes=none\ndevice_partition_writes=none\n' "$output"
