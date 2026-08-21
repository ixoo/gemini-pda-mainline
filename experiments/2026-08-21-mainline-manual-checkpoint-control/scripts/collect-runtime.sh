#!/usr/bin/env bash

# Source-pin the proven serviceability observer, specialize it for the manual
# checkpoint control, and add bounded changed-ID Gemian recovery of the two
# retained records. Recovery is read-only and follows only an exact live pass.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b7db700f2797e444294e4dad1b46aa1da85ea4dfbc55869f0698165a441685ad
readonly PROBE_SHA256=114d637fdbfb7f7fd09f960f2b0b231a79ad12d60e8f9427dca2fb8d53a2f77e
readonly LIVE_VALIDATOR_SHA256=ae39d5b4755c974c29f94b9c1b8ea909d278e52488d309e5e5ad74583d669dc8
readonly RETAINED_VALIDATOR_SHA256=52dc1ec02e24cbedfe03623b3e177899b8b5abd4cb80df484cd035dd6632460a
readonly CANDIDATE_SHA256=53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c
readonly EXPECTED_TARGET=gemini@192.168.1.50

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --deployment-boot-id UUID --output artifacts/runtime-captures/manual-checkpoint-control-attempt-1\n' "$0" >&2
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
[[ "$(basename -- "$output")" == manual-checkpoint-control-attempt-1 ]] ||
	die 'output must be the exact private attempt-1 child'
[[ "$(dirname -- "$output")" == "$private_root" ]] ||
	die 'output must remain in the private runtime-capture root'
[[ ! -e "$output" && ! -L "$output" ]] || die 'output already exists'
git -C "$repo_root" check-ignore -q "$output" || die 'output is not ignored by Git'

derived="$(mktemp "$script_dir/.derived-manual-checkpoint-collector.XXXXXXXX")"
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
        "# Pre-arm one bounded USB/netcat observation of the exact manual checkpoint\n"
        "# control. Only after two local full readbacks and serviceability pass, request\n"
        "# one native reboot and confirm a changed-ID Gemian return.",
        1,
    ),
    (
        "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3",
        "53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c",
        1,
    ),
    (
        "8ecc847e75e1e9e6b7634a16bd6714b3373cfa4996b9c6910087f4e34eabffab",
        "114d637fdbfb7f7fd09f960f2b0b231a79ad12d60e8f9427dca2fb8d53a2f77e",
        1,
    ),
    (
        "dda8ed943e27996f767f50899a5c5e56334d9f8d04ea8659563a8ac637631e7d",
        "ae39d5b4755c974c29f94b9c1b8ea909d278e52488d309e5e5ad74583d669dc8",
        1,
    ),
    ("current-tree-service-control-attempt-1", "manual-checkpoint-control-attempt-1", 3),
    ("current-service", "manual-checkpoint-control", 1),
    ("__CURRENT_SERVICE_CONTROL_RUNTIME_BEGIN__", "__MANUAL_CHECKPOINT_CONTROL_RUNTIME_BEGIN__", 1),
    ("__CURRENT_SERVICE_CONTROL_RUNTIME_END__", "__MANUAL_CHECKPOINT_CONTROL_RUNTIME_END__", 1),
    ("serviceable-control-pass", "manual-checkpoint-live-pass", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe collector derivation: expected {count}, found {actual}: {old}"
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

retained="$output/retained-slots.txt"
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
for command in awk base64 blockdev cat dd find findmnt id lsblk od readlink sha256sum stat tr uname; do
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

slot_header() {
	dd if=/dev/mem bs=1 skip="$1" count=12 status=none | od -An -tx1 | tr -d ' \n'
}
slot_payload() {
	dd if=/dev/mem bs=1 skip="$1" count=4096 status=none | base64 | tr -d '\n'
}
slot_173_header="$(slot_header $((0x444bd000)))"
slot_174_header="$(slot_header $((0x444be000)))"
slot_173_b64="$(slot_payload $((0x444bd000)))"
slot_174_b64="$(slot_payload $((0x444be000)))"

pstore_file_count=0
pstore_bytes=0
for path in /sys/fs/pstore/*; do
	[[ -f "$path" && ! -L "$path" ]] || continue
	bytes="$(stat -c '%s' "$path")"
	[[ "$bytes" =~ ^[0-9]+$ ]] || fail 'malformed pstore file size'
	pstore_file_count=$((pstore_file_count + 1))
	pstore_bytes=$((pstore_bytes + bytes))
	(( pstore_bytes <= 4194304 )) || fail 'bounded pstore recovery limit exceeded'
done
pstore_payload_b64="$({
	for path in /sys/fs/pstore/*; do
		[[ -f "$path" && ! -L "$path" ]] || continue
		cat "$path"
	done
} | base64 | tr -d '\n')"

printf 'recovery_kernel=%s\nrecovery_architecture=%s\n' "$(uname -r)" "$(uname -m)"
printf 'recovery_boot_id_sha256=%s\n' "$(printf '%s' "$boot_id" | sha256sum | awk '{print $1}')"
printf 'active_root=%s\nboot2_device=%s\nboot2_full_sha256=%s\n' \
	"$root" "$target" "$boot2_sha256"
printf 'slot_173_size=4096\nslot_174_size=4096\n'
printf 'slot_173_header=%s\nslot_174_header=%s\n' "$slot_173_header" "$slot_174_header"
printf 'slot_173_b64=%s\nslot_174_b64=%s\n' "$slot_173_b64" "$slot_174_b64"
printf 'pstore_file_count=%s\npstore_payload_b64=%s\n' "$pstore_file_count" "$pstore_payload_b64"
printf 'device_memory_writes=none\ndevice_partition_writes=none\n'
REMOTE

python3 "$retained_validator" "$retained" >"$retained_classification"
grep -Eq '^retained_classification=(writer-and-recovery-pass|live-pass-recovered-empty)$' \
	"$retained_classification" || die 'retained recovery did not classify'
printf 'retained_capture=complete\n' >>"$output/observer-events.txt"
(
	cd "$output"
	sha256sum classification.txt observer-events.txt retained-classification.txt \
		retained-slots.txt runtime.txt usb-topology.txt >SHA256SUMS
)
chmod 0600 "$output"/*
cleanup
trap - EXIT HUP INT TERM
printf 'runtime_classification=manual-checkpoint-live-pass\n'
grep -E '^retained_(classification|reason)=' "$retained_classification"
printf 'cpu_online=0-7\ncpu_offline=8-9\n'
printf 'native_reboot_to_changed_gemian=passed\ncapture=%s\n' "$output"
