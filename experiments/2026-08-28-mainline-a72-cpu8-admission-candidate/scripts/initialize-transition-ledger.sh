#!/usr/bin/env bash

# Convert one exact stale pstore header to the transition ledger's
# logical-empty state with exactly two retained-RAM u32 writes.
set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly EXPECTED_PREFIX_SHA256=b54428eae30bf9e947b8a16941e5e54eaddadc97579805bd555272a0115e497c
readonly EXPECTED_HEADER='1128743492 130 130'
readonly BASE_ADDRESS=1145110528
readonly PREFIX_SIZE=84
readonly VALIDATOR_SHA256=cefe3d19ad05c4facbdff7725667c33105d5d714c9d6b32d5ba993d5fccd9e85

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --target gemini@192.168.1.50 --evidence-dir artifacts/device-install-evidence/a72-admission-ledger-init-1\n' "$0" >&2
}

target=
evidence_dir=
while (($#)); do
	case "$1" in
	--target) target=${2:-}; shift 2 ;;
	--evidence-dir) evidence_dir=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$target" == "$EXPECTED_TARGET" && -n "$evidence_dir" ]] || {
	usage
	exit 2
}
for command in awk basename chmod dirname git mkdir sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
validator="$script_dir/validate-transition-ledger.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
evidence_root="$repo_root/artifacts/device-install-evidence"
for input in "$validator" "$identity"; do
	[[ -f "$input" && ! -L "$input" ]] || die "required input is missing or unsafe: $input"
done
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] ||
	die 'transition-ledger validator changed'
identity_mode=$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
[[ -d "$evidence_root" && ! -L "$evidence_root" ]] || die 'evidence root is unsafe'
evidence_root=$(cd -- "$evidence_root" && pwd -P)
case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
[[ "$(dirname -- "$evidence_dir")" == "$evidence_root" &&
	"$(basename -- "$evidence_dir")" == a72-admission-ledger-init-1 ]] ||
	die 'evidence directory must be the exact attempt-1 child'
[[ ! -e "$evidence_dir" && ! -L "$evidence_dir" ]] || die 'evidence directory already exists'
git -C "$repo_root" check-ignore -q "$evidence_dir" || die 'evidence directory is not ignored'

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
remote_output="$("${ssh_command[@]}" "$target" \
	"sudo -n env EXPECTED_PREFIX_SHA256='$EXPECTED_PREFIX_SHA256' EXPECTED_HEADER='$EXPECTED_HEADER' BASE_ADDRESS='$BASE_ADDRESS' PREFIX_SIZE='$PREFIX_SIZE' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk cat dd id od sha256sum sleep tr uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
boot_id=$(cat /proc/sys/kernel/random/boot_id)
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || fail 'malformed boot ID'

power_sample() {
	local present capacity health external online
	present=$(cat /sys/class/power_supply/battery/present)
	capacity=$(cat /sys/class/power_supply/battery/capacity)
	health=$(cat /sys/class/power_supply/battery/health)
	external=0
	for online in /sys/class/power_supply/ac/online /sys/class/power_supply/usb/online \
		/sys/class/power_supply/wireless/online; do
		[[ ! -r "$online" ]] || external=$((external + $(cat "$online")))
	done
	[[ "$present" == 1 && "$capacity" =~ ^[0-9]+$ && "$health" == Good ]] || return 1
	(( capacity >= 80 || (capacity >= 40 && external >= 1) )) || return 1
	printf '%s|%s|%s|%s\n' "$present" "$capacity" "$health" "$external"
}
power_first=$(power_sample) || fail 'power gate failed'
sleep 2
power_second=$(power_sample) || fail 'second power gate failed'
[[ "$power_first" == "$power_second" ]] || fail 'power state changed between samples'

before_sha256=$(dd if=/dev/mem bs=1 skip="$BASE_ADDRESS" count="$PREFIX_SIZE" status=none |
	sha256sum | awk '{print $1}')
before_header=$(dd if=/dev/mem bs=1 skip="$BASE_ADDRESS" count=12 status=none |
	od -An -v -tu4 | tr -s ' ' | tr -d '\n' | awk '{$1=$1; print}')
[[ "$before_sha256" == "$EXPECTED_PREFIX_SHA256" && "$before_header" == "$EXPECTED_HEADER" ]] ||
	fail 'retained prefix changed before initialization'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$boot_id" ]] || fail 'boot ID changed before writes'

dd if=/dev/zero of=/dev/mem bs=4 seek=$(((BASE_ADDRESS + 4) / 4)) count=1 conv=notrunc status=none
dd if=/dev/zero of=/dev/mem bs=4 seek=$(((BASE_ADDRESS + 8) / 4)) count=1 conv=notrunc status=none

after_header=$(dd if=/dev/mem bs=1 skip="$BASE_ADDRESS" count=12 status=none |
	od -An -v -tu4 | tr -s ' ' | tr -d '\n' | awk '{$1=$1; print}')
[[ "$after_header" == '1128743492 0 0' ]] || fail 'logical-empty header readback mismatch'
after_sha256=$(dd if=/dev/mem bs=1 skip="$BASE_ADDRESS" count="$PREFIX_SIZE" status=none |
	sha256sum | awk '{print $1}')
after_hex=$(dd if=/dev/mem bs=1 skip="$BASE_ADDRESS" count="$PREFIX_SIZE" status=none |
	od -An -v -tx1 | tr -d ' \n')
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$boot_id" ]] || fail 'boot ID changed after writes'
printf 'boot_id=%s\npower=%s\n' "$boot_id" "$power_second"
printf 'before_prefix_sha256=%s\nbefore_header=%s\n' "$before_sha256" "$before_header"
printf 'retained_u32_writes=2\nafter_header=%s\nafter_prefix_sha256=%s\n' \
	"$after_header" "$after_sha256"
printf 'after_hex=%s\n' "$after_hex"
REMOTE
)" || die 'exact two-write retained-ledger initialization failed'

single_value() {
	local key=$1
	printf '%s\n' "$remote_output" | awk -F= -v key="$key" \
		'$1 == key {value=substr($0, length(key) + 2); count++} END {if (count != 1) exit 2; print value}'
}
after_hex=$(single_value after_hex) || die 'malformed post-write retained bytes'
validation=$(python3 "$validator" --hex "$after_hex") || die 'logical-empty readback validation failed'
printf '%s\n' "$validation"

mkdir -m 0700 "$evidence_dir"
summary="$evidence_dir/initialization-summary.txt"
{
	printf 'experiment=2026-08-28-mainline-a72-cpu8-admission-candidate\n'
	printf 'operation=exact-stale-pstore-header-to-logical-empty\n'
	printf 'boot_id=%s\npower=%s\n' "$(single_value boot_id)" "$(single_value power)"
	printf 'before_prefix_sha256=%s\nbefore_header=%s\n' \
		"$(single_value before_prefix_sha256)" "$(single_value before_header)"
	printf 'retained_u32_writes=%s\nafter_header=%s\nafter_prefix_sha256=%s\n' \
		"$(single_value retained_u32_writes)" "$(single_value after_header)" \
		"$(single_value after_prefix_sha256)"
	printf '%s\n' "$validation"
	printf 'device_partition_reads=none\ndevice_partition_writes=none\n'
	printf 'device_filesystem_backup=none\nshutdown=not-requested-install-follows\nresult=pass\n'
} >"$summary"
chmod 0600 "$summary"
(
	cd "$evidence_dir"
	sha256sum initialization-summary.txt >SHA256SUMS
)
chmod 0600 "$evidence_dir/SHA256SUMS"
printf 'result=pass\nretained_u32_writes=2\ntransition_ledger_state=logical-empty\n'
printf 'evidence_dir=%s\n' "$evidence_dir"
