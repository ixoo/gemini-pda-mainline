#!/usr/bin/env bash

# Source-pin the proven USB observer for one exact first-dmesg live result,
# then perform bounded read-only changed-ID Gemian pstore and RAM recovery.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b7db700f2797e444294e4dad1b46aa1da85ea4dfbc55869f0698165a441685ad
readonly PROBE_SHA256=99af34ba3f9bd33c6d56f105ca3a7eade0c6d4250b012bd3bb8bc303296e03a7
readonly LIVE_VALIDATOR_SHA256=78a6bfc99a1e597fe5c8d0381e1d3ece5c5648f96a28fa5842f64dd0a0c0befd
readonly RETAINED_VALIDATOR_SHA256=c87a0e0a4ed969e0c2ea5cac3fc602fb4d6dd9641fa65984c6ab912be7d48ac3
readonly CANDIDATE_SHA256=b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96
readonly EXPECTED_TARGET=gemini@192.168.1.50

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/first-dmesg-raw-write-attempt-1\n' "$0" >&2
}

for command in awk base64 basename chmod dirname git mktemp python3 rm sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

deployment_boot_id=
output=
arguments=("$@")
while (($#)); do
	case "$1" in
	--deployment-boot-id)
		(($# >= 2)) || die '--deployment-boot-id requires a value'
		[[ -z "$deployment_boot_id" ]] || die 'duplicate --deployment-boot-id'
		deployment_boot_id=$2
		shift 2
		;;
	--output)
		(($# >= 2)) || die '--output requires a value'
		[[ -z "$output" ]] || die 'duplicate --output'
		output=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
	die 'deployment boot ID is missing or malformed'
[[ -n "$output" ]] || { usage; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/collect-runtime.sh"
probe="$script_dir/remote-runtime-probe.sh"
live_validator="$script_dir/validate-runtime.py"
retained_validator="$script_dir/validate-retained.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
private_root="$repo_root/artifacts/runtime-captures"
for input in "$source_collector" "$probe" "$live_validator" "$retained_validator" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "input is missing or unsafe: $input"
done
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'
[[ "$(sha256sum "$probe" | awk '{print $1}')" == "$PROBE_SHA256" ]] || die 'probe changed'
[[ "$(sha256sum "$live_validator" | awk '{print $1}')" == "$LIVE_VALIDATOR_SHA256" ]] ||
	die 'live validator changed'
[[ "$(sha256sum "$retained_validator" | awk '{print $1}')" == "$RETAINED_VALIDATOR_SHA256" ]] ||
	die 'retained validator changed'
identity_mode="$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")"
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'runtime-capture root is unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(basename -- "$output")" == first-dmesg-raw-write-attempt-1 ]] ||
	die 'output must be the exact private attempt-1 child'
[[ "$(dirname -- "$output")" == "$private_root" ]] ||
	die 'output must remain in the private runtime-capture root'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

derived="$(mktemp "$script_dir/.derived-first-dmesg-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "# Pre-arm one bounded USB/netcat observation of the exact serviceability\n"
        "# control. Only after full classification passes, request one native reboot and\n"
        "# confirm a changed-ID Gemian return.",
        "# Pre-arm one bounded USB/netcat observation of the exact first-dmesg\n"
        "# candidate. Only after exact live attribution, request one native reboot and\n"
        "# confirm a changed-ID Gemian return.",
        1,
    ),
    (
        "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3",
        "b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96",
        1,
    ),
    (
        "8ecc847e75e1e9e6b7634a16bd6714b3373cfa4996b9c6910087f4e34eabffab",
        "99af34ba3f9bd33c6d56f105ca3a7eade0c6d4250b012bd3bb8bc303296e03a7",
        1,
    ),
    (
        "dda8ed943e27996f767f50899a5c5e56334d9f8d04ea8659563a8ac637631e7d",
        "78a6bfc99a1e597fe5c8d0381e1d3ece5c5648f96a28fa5842f64dd0a0c0befd",
        1,
    ),
    ("current-tree-service-control-attempt-1", "first-dmesg-raw-write-attempt-1", 3),
    ("current-service", "first-dmesg-raw-write", 1),
    ("__CURRENT_SERVICE_CONTROL_RUNTIME_BEGIN__", "__FIRST_DMESG_RAW_WRITE_RUNTIME_BEGIN__", 1),
    ("__CURRENT_SERVICE_CONTROL_RUNTIME_END__", "__FIRST_DMESG_RAW_WRITE_RUNTIME_END__", 1),
    ("serviceable-control-pass", "first-dmesg-raw-write-live-pass", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe first-dmesg collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "${arguments[@]}"
status=$?
set -e
(( status == 0 )) || exit "$status"

retained="$output/retained-record.txt"
retained_classification="$output/retained-classification.txt"
[[ ! -e "$retained" && ! -L "$retained" ]] || die 'retained capture path already exists'
: >"$retained"
chmod 0600 "$retained"
ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
"${ssh_command[@]}" "$EXPECTED_TARGET" \
	"sudo -n env EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_DEPLOYMENT_BOOT_ID='$deployment_boot_id' /bin/bash -s" \
	>"$retained" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk base64 basename blockdev cat dd dmesg find findmnt grep head id lsblk od readlink sha256sum stat tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -r)" == 3.18.41+ && "$(uname -m)" == aarch64 ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id="$(cat /proc/sys/kernel/random/boot_id)"
[[ "$boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ &&
	"$boot_id" != "$EXPECTED_DEPLOYMENT_BOOT_ID" ]] || fail 'recovery boot ID did not change'

rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')"
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2 row'
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$target" == /dev/mmcblk0p30 && "$label" == boot2 && "$type" == part &&
	"$size" == 16777216 && "$ro" == 0 ]] || fail 'boot2 identity changed'
[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]] ||
	fail 'boot2 is mounted or invalid'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] ||
	fail 'boot2 by-partlabel disagrees with GPT'
[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 &&
	"$(blockdev --getsize64 "$target")" == 16777216 ]] || fail 'boot2 geometry changed'
root="$(readlink -f "$(findmnt -n -o SOURCE /)")"
[[ "$root" == /dev/mmcblk0p29 && "$root" != "$target" ]] || fail 'active root changed'
boot2_sha256="$(sha256sum "$target" | awk '{print $1}')"
[[ "$boot2_sha256" == "$EXPECTED_CANDIDATE" ]] || fail 'boot2 candidate changed'
[[ -c /dev/mem ]] || fail '/dev/mem is unavailable'

record_1_header="$(dd if=/dev/mem bs=1 skip=$((0x44410000)) count=12 status=none |
	od -An -tx1 | tr -d ' \n')"
record_2_header="$(dd if=/dev/mem bs=1 skip=$((0x44411000)) count=12 status=none |
	od -An -tx1 | tr -d ' \n')"
record_1_b64="$(dd if=/dev/mem bs=1 skip=$((0x44410000)) count=4096 status=none |
	base64 | tr -d '\n')"

pstore_type="$(findmnt -n -T /sys/fs/pstore -o FSTYPE 2>/dev/null || true)"
[[ "$pstore_type" == pstore ]] || fail 'pstore is not mounted'
pstore_file_count=0
pstore_bytes=0
pstore_metadata="$({
	for path in /sys/fs/pstore/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		bytes="$(stat -c '%s' "$path")"
		[[ "$bytes" =~ ^[0-9]+$ ]] || fail 'malformed pstore file size'
		pstore_file_count=$((pstore_file_count + 1))
		pstore_bytes=$((pstore_bytes + bytes))
		(( pstore_file_count <= 64 && pstore_bytes <= 4194304 )) ||
			fail 'bounded pstore recovery limit exceeded'
		printf '%s %s\n' "$(basename "$path")" "$bytes"
	done
	printf '__COUNT__=%s\n__BYTES__=%s\n' "$pstore_file_count" "$pstore_bytes"
} )"
pstore_file_count="$(printf '%s\n' "$pstore_metadata" | awk -F= '$1 == "__COUNT__" {print $2}')"
pstore_file_metadata_b64="$(printf '%s\n' "$pstore_metadata" |
	awk '!/^__(COUNT|BYTES)__=/' | base64 | tr -d '\n')"
pstore_payload_b64="$({
	for path in /sys/fs/pstore/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		cat "$path"
	done
} | base64 | tr -d '\n')"

ramoops_dmesg="$(dmesg | grep -Ei 'pstore|ramoops|persistent ram' | head -n 256 || true)"
ramoops_registration_lines="$(printf '%s\n' "$ramoops_dmesg" |
	grep -Eic 'ramoops|persistent ram' || true)"
ramoops_parameters="$({
	for path in /sys/module/ramoops/parameters/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		printf '%s=' "$(basename "$path")"
		head -c 4096 "$path"
		printf '\n'
	done
} )"

printf 'recovery_kernel=%s\nrecovery_architecture=%s\n' "$(uname -r)" "$(uname -m)"
printf 'recovery_boot_id_sha256=%s\n' "$(printf '%s' "$boot_id" | sha256sum | awk '{print $1}')"
printf 'active_root=%s\nboot2_device=%s\nboot2_full_sha256=%s\n' \
	"$root" "$target" "$boot2_sha256"
printf 'pstore_mounted=yes\npstore_file_count=%s\n' "$pstore_file_count"
printf 'pstore_file_metadata_b64=%s\npstore_payload_b64=%s\n' \
	"$pstore_file_metadata_b64" "$pstore_payload_b64"
printf 'record_1_size=4096\nrecord_1_header=%s\nrecord_1_b64=%s\n' \
	"$record_1_header" "$record_1_b64"
printf 'record_2_header=%s\nramoops_registration_lines=%s\n' \
	"$record_2_header" "$ramoops_registration_lines"
printf 'ramoops_dmesg_b64=%s\n' "$(printf '%s' "$ramoops_dmesg" | base64 | tr -d '\n')"
printf 'ramoops_parameters_b64=%s\n' "$(printf '%s' "$ramoops_parameters" | base64 | tr -d '\n')"
printf 'device_memory_writes=none\ndevice_partition_writes=none\n'
REMOTE

python3 "$retained_validator" "$retained" >"$retained_classification"
grep -Eq '^retained_classification=(first-dmesg-cross-version-enumeration-pass|first-dmesg-direct-retention-only)$' \
	"$retained_classification" || die 'retained recovery did not classify'
printf 'retained_capture=complete\n' >>"$output/observer-events.txt"
(
	cd "$output"
	sha256sum classification.txt observer-events.txt retained-classification.txt \
		retained-record.txt runtime.txt usb-topology.txt >SHA256SUMS
)
chmod 0600 "$output"/*
cleanup
trap - EXIT HUP INT TERM
printf 'runtime_classification=first-dmesg-raw-write-live-pass\n'
grep -E '^retained_(classification|reason)=' "$retained_classification"
printf 'cpu_online=0-7\ncpu_offline=8-9\n'
printf 'native_reboot_to_changed_gemian=passed\ncapture=%s\n' "$output"
