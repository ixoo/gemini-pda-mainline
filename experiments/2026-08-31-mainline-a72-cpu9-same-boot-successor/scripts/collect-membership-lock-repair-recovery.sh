#!/usr/bin/env bash

# Recover and classify the exact patch-0480 retained lanes after changed-ID Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_DEPLOYMENT_NAME=a72-cpu9-membership-lock-repair-deployment-1
readonly EXPECTED_OUTPUT_NAME=a72-cpu9-membership-lock-repair-recovery-attempt-1
readonly CANDIDATE_SHA256=65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c
readonly COLLECTOR_SHA256=9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b
readonly CLASSIFIER_SHA256=64e17462c68829e993b6437a3a96c26f9ea57adc27e47a56fd8afc130939d02f

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --target %s --deployment-dir DIR --output-dir DIR\n' \
		"$0" "$EXPECTED_TARGET"
}

target=
deployment_dir=
output_dir=
while (($#)); do
	case "$1" in
	--target)
		(($# >= 2)) || die '--target requires USER@HOST'
		target=$2
		shift 2
		;;
	--deployment-dir)
		(($# >= 2)) || die '--deployment-dir requires DIR'
		deployment_dir=$2
		shift 2
		;;
	--output-dir)
		(($# >= 2)) || die '--output-dir requires DIR'
		output_dir=$2
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ "$target" == "$EXPECTED_TARGET" && -n "$deployment_dir" && -n "$output_dir" ]] || {
	usage >&2
	exit 2
}

for command in awk basename chmod dirname find git grep mktemp mv python3 rm \
	sha256sum ssh stat xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
collector="$repo_root/scripts/collect-device-pstore"
classifier="$script_dir/classify-membership-lock-repair-recovery.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
case "$deployment_dir" in /*) ;; *) deployment_dir="$repo_root/${deployment_dir#./}" ;; esac
case "$output_dir" in /*) ;; *) output_dir="$repo_root/${output_dir#./}" ;; esac
readonly script_dir repo_root collector classifier identity deployment_dir output_dir

[[ "$(basename -- "$deployment_dir")" == "$EXPECTED_DEPLOYMENT_NAME" &&
	"$(dirname -- "$deployment_dir")" == "$repo_root/artifacts/device-install-evidence" ]] ||
	die 'deployment directory identity changed'
[[ "$(basename -- "$output_dir")" == "$EXPECTED_OUTPUT_NAME" &&
	"$(dirname -- "$output_dir")" == "$repo_root/artifacts/device-pstore" ]] ||
	die 'output directory identity changed'
git -C "$repo_root" check-ignore -q -- "$output_dir" || die 'output is not ignored by Git'
[[ ! -e "$output_dir" && ! -L "$output_dir" ]] || die 'refusing to overwrite output'

for input in "$collector" "$classifier" "$identity" \
	"$deployment_dir/deployment-summary.txt" "$deployment_dir/SHA256SUMS"; do
	[[ -f "$input" && ! -L "$input" ]] || die "missing or unsafe input: $input"
done
[[ "$(sha256sum "$collector" | awk '{print $1}')" == "$COLLECTOR_SHA256" ]] ||
	die 'source pstore collector changed'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] ||
	die 'membership-lock recovery classifier changed'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
(cd "$deployment_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'deployment evidence checksum failed'

single_value() {
	local key=$1 file=$2
	awk -F= -v key="$key" \
		'$1 == key {print substr($0, length(key) + 2); n++} END {exit n != 1}' "$file"
}

deployment_summary="$deployment_dir/deployment-summary.txt"
deployment_boot_id=$(single_value boot_id "$deployment_summary") ||
	die 'deployment boot ID missing or duplicated'
installed_candidate=$(single_value candidate_sha256 "$deployment_summary") ||
	die 'deployment candidate missing or duplicated'
readback_candidate=$(single_value readback_sha256 "$deployment_summary") ||
	die 'deployment readback missing or duplicated'
[[ "$deployment_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] ||
	die 'deployment boot ID malformed'
[[ "$installed_candidate" == "$CANDIDATE_SHA256" &&
	"$readback_candidate" == "$CANDIDATE_SHA256" ]] ||
	die 'deployment candidate identity changed'

preflight=$(mktemp "${TMPDIR:-/tmp}/.gemini-membership-lock-recovery.XXXXXXXX")
classification=$(mktemp "${TMPDIR:-/tmp}/.gemini-membership-lock-classification.XXXXXXXX")
cleanup() { rm -f -- "${preflight:-}" "${classification:-}"; }
trap cleanup EXIT HUP INT TERM
ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity"
)
"${ssh_command[@]}" "$target" 'sudo -n /bin/bash -s' >"$preflight" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk cat findmnt id lsblk readlink sha256sum tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] ||
	fail 'runtime boot ID malformed'
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
root=$(findmnt -nro SOURCE /)
[[ -n "$root" && "$root" != "$boot2" ]] || fail 'boot2 is the active root'
printf 'boot_id=%s\n' "$boot_id"
printf 'kernel_release=%s\narchitecture=%s\n' "$(uname -r)" "$(uname -m)"
printf 'root=%s\nboot2_target=%s\nboot2_size=%s\n' "$root" "$boot2" "$size"
printf 'boot2_sha256=%s\n' "$(sha256sum "$boot2" | awk '{print $1}')"
printf 'pstore_files='; find /sys/fs/pstore -maxdepth 1 -type f -printf '%f ' 2>/dev/null || true; printf '\n'
printf 'device_storage_writes=none\nretained_ram_writes=none\nreboot_request=none\n'
REMOTE

runtime_boot_id=$(single_value boot_id "$preflight") || die 'runtime boot ID missing or duplicated'
boot2_sha256=$(single_value boot2_sha256 "$preflight") || die 'runtime boot2 hash missing or duplicated'
[[ "$runtime_boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ &&
	"$runtime_boot_id" != "$deployment_boot_id" ]] ||
	die 'no changed Gemian boot ID after deployment'
[[ "$boot2_sha256" == "$CANDIDATE_SHA256" ]] || die 'installed boot2 identity changed'

"$collector" --target "$target" --identity "$identity" --output "$output_dir" \
	--expected-kernel 3.18.41+
(cd "$output_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'captured pstore evidence checksum failed'
runtime_boot_id_sha256=$(printf '%s\n' "$runtime_boot_id" | sha256sum | awk '{print $1}')
captured_boot_id_sha256=$(single_value boot_id_sha256 "$output_dir/metadata.txt") ||
	die 'captured boot ID hash missing or duplicated'
[[ "$captured_boot_id_sha256" == "$runtime_boot_id_sha256" ]] ||
	die 'pstore capture is not bound to the recovery preflight boot ID'

set +e
python3 "$classifier" --pstore-dir "$output_dir/pstore" >"$classification"
classification_rc=$?
set -e
chmod 0600 "$classification"
mv "$classification" "$output_dir/classification.txt"
classification=
{
	printf 'experiment=2026-08-31-mainline-a72-cpu9-membership-lock-repair\n'
	printf 'installed_candidate_sha256=%s\n' "$CANDIDATE_SHA256"
	printf 'deployment_boot_id=%s\nruntime_boot_id=%s\n' \
		"$deployment_boot_id" "$runtime_boot_id"
	grep -E '^(kernel_release|architecture|root|boot2_target|boot2_size|boot2_sha256|pstore_files|device_storage_writes|retained_ram_writes|reboot_request)=' "$preflight"
	cat "$output_dir/classification.txt"
} >"$output_dir/recovery-summary.txt"
chmod 0600 "$output_dir/recovery-summary.txt"
(
	cd "$output_dir"
	find . -type f ! -path ./SHA256SUMS ! -path ./SHA256SUMS.partial -print0 | sort -z | \
		xargs -0 sha256sum >SHA256SUMS.partial
	mv SHA256SUMS.partial SHA256SUMS
	sha256sum --check --strict SHA256SUMS >/dev/null
)
cleanup
trap - EXIT HUP INT TERM
printf 'recovery=%s\n' "$output_dir"
grep -E '^(runtime_classification|next_selected_branch|cpu9_online)=' \
	"$output_dir/recovery-summary.txt" || true
printf 'device_storage_writes=none\nretained_ram_writes=none\n'
((classification_rc == 0)) || exit "$classification_rc"
