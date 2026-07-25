#!/usr/bin/env bash

# Literal derived-installer checks intentionally contain unexpanded shell text.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
installer="$script_dir/install-candidate-y-boot2.sh"
deriver="$script_dir/derive-installer.py"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
for input in "$installer" "$deriver" "$x_installer"; do
	[[ -f "$input" && ! -L "$input" ]] || die "installer test input missing: $input"
done
for command in awk bash chmod grep mktemp python3 rm sed sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
bash -n "$installer"

assignment_value() {
	local name=$1
	local lines count
	lines="$(grep -E "^readonly ${name}=" "$installer" || true)"
	count="$(printf '%s\n' "$lines" | awk 'NF { count++ } END { print count + 0 }')"
	[[ "$count" == 1 ]] || die "installer pin is absent or duplicated: $name"
	printf '%s\n' "${lines#*=}"
}

source_raw_sha256="$(assignment_value Y_RAW_SHA256)"
source_raw_size="$(assignment_value Y_RAW_SIZE)"
source_padded_sha256="$(assignment_value Y_PADDED_SHA256)"
source_current_x_sha256="$(assignment_value EXPECTED_CURRENT_X_PADDED_SHA256)"
source_x_installer_sha256="$(assignment_value X_INSTALLER_SHA256)"
[[ "$source_raw_sha256" == 94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee ]] || \
	die 'Candidate Y raw-image calibration changed'
[[ "$source_raw_size" == 6866944 ]] || die 'Candidate Y raw-size calibration changed'
[[ "$source_padded_sha256" == dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17 ]] || \
	die 'Candidate Y padded-image calibration changed'
[[ "$source_current_x_sha256" == e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855 ]] || \
	die 'installer predecessor is not exact installed Candidate X'
[[ "$source_x_installer_sha256" == 2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e ]] || \
	die 'Candidate X installer pin changed'
[[ "$(sha256sum "$x_installer" | awk '{print $1}')" == "$source_x_installer_sha256" ]] || \
	die 'hash-pinned Candidate X installer bytes changed'
[[ "$source_padded_sha256" != "$source_current_x_sha256" ]] || \
	die 'Candidate Y padded hash equals its Candidate X predecessor'

workdir="$(mktemp -d /tmp/candidate-y-installer-static.XXXXXX)"
cleanup() { rm -rf -- "$workdir"; }
trap cleanup EXIT

derived="$workdir/derived.sh"
python3 "$deriver" --source "$x_installer" --output "$derived" \
	--raw-sha256 "$source_raw_sha256" --raw-size "$source_raw_size" \
	--padded-sha256 "$source_padded_sha256"
bash -n "$derived"
for token in \
	'readlink -f /dev/disk/by-partlabel/boot2' \
	'boot2 is the active root' \
	'boot2 is mounted' \
	'boot2 is active swap' \
	'boot2 has holders' \
	'boot ID changed immediately before write' \
	'boot2 changed at the final pre-write checksum' \
	'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4' \
	'blockdev --flushbufs "$target"' \
	'full boot2 readback differs byte-for-byte' \
	'reboot_or_shutdown_performed=no'; do
	grep -Fq "$token" "$derived" || die "derived installer safety gate absent: $token"
done
[[ "$(grep -Fc 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4' "$derived")" == 1 ]] || \
	die 'derived installer does not contain exactly one bounded target write'
grep -Fq "readonly Y_RAW_SHA256=$source_raw_sha256" "$derived" || \
	die 'derived raw-image pin changed'
grep -Fq "readonly Y_RAW_SIZE=$source_raw_size" "$derived" || \
	die 'derived raw-size pin changed'
grep -Fq "readonly Y_PADDED_SHA256=$source_padded_sha256" "$derived" || \
	die 'derived padded-image pin changed'
grep -Fq "readonly EXPECTED_CURRENT_X_PADDED_SHA256=$source_current_x_sha256" "$derived" || \
	die 'derived predecessor pin changed'
[[ "$(grep -Fc 'candidate_label=Y' "$derived")" == 2 ]] || \
	die 'derived candidate labels changed'
grep -Fq 'expected_previous_label=X' "$derived" || die 'derived predecessor label changed'
if grep -Eq '^[[:space:]]*(sudo[[:space:]].*)?(reboot|shutdown|poweroff|halt|kexec)([[:space:]]|$)' \
	"$derived" || grep -Fq 'sysrq-trigger' "$derived"; then
	die 'derived installer gained reboot, shutdown, kexec, or sysrq behavior'
fi

"$installer" --help >"$workdir/help.out" 2>"$workdir/help.err"
grep -Fq 'install-candidate-y-boot2.sh' "$workdir/help.out" "$workdir/help.err" || \
	die 'calibrated installer help did not reach the derived installer'

invoke_rejection() {
	local selected=$1 expected=$2 label=$3
	set +e
	"$selected" --help >"$workdir/$label.out" 2>"$workdir/$label.err"
	local rc=$?
	set -e
	[[ "$rc" == 2 ]] || die "$label rejection returned $rc"
	grep -Fxq "$expected" "$workdir/$label.err" || die "$label rejection changed"
}

uncalibrated="$workdir/uncalibrated.sh"
sed \
	-e 's/^readonly Y_RAW_SHA256=.*/readonly Y_RAW_SHA256=REPLACE_AFTER_CALIBRATION_Y_BOOT_SHA256/' \
	-e 's/^readonly Y_RAW_SIZE=.*/readonly Y_RAW_SIZE=REPLACE_AFTER_CALIBRATION_Y_BOOT_SIZE/' \
	-e 's/^readonly Y_PADDED_SHA256=.*/readonly Y_PADDED_SHA256=REPLACE_AFTER_CALIBRATION_Y_PADDED_BOOT2_SHA256/' \
	"$installer" >"$uncalibrated"
chmod 0700 "$uncalibrated"
invoke_rejection "$uncalibrated" 'error: calibration placeholder remains: Y_RAW_SHA256' uncalibrated

partial="$workdir/partial.sh"
sed 's/^readonly Y_RAW_SHA256=.*/readonly Y_RAW_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
	"$uncalibrated" >"$partial"
chmod 0700 "$partial"
invoke_rejection "$partial" 'error: calibration placeholder remains: Y_RAW_SIZE' partial

oversize="$workdir/oversize.sh"
sed 's/^readonly Y_RAW_SIZE=.*/readonly Y_RAW_SIZE=16777217/' "$installer" >"$oversize"
chmod 0700 "$oversize"
invoke_rejection "$oversize" 'error: invalid or oversized calibrated Y_RAW_SIZE' oversize

same_hash="$workdir/same-hash.sh"
sed "s/^readonly Y_PADDED_SHA256=.*/readonly Y_PADDED_SHA256=$source_current_x_sha256/" \
	"$installer" >"$same_hash"
chmod 0700 "$same_hash"
invoke_rejection "$same_hash" \
	'error: Candidate Y padded hash unexpectedly equals the Candidate X predecessor' same-hash

set +e
"$installer" --expected-current-sha256 \
	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc \
	>"$workdir/override.out" 2>"$workdir/override.err"
override_rc=$?
set -e
[[ "$override_rc" == 2 ]] || die 'caller checksum override was not rejected'
grep -Fxq 'error: unknown argument: --expected-current-sha256' \
	"$workdir/override.err" || die 'caller checksum override rejection changed'

printf 'validation=candidate-y-installer-static\n'
printf 'calibration_state=calibrated\n'
printf 'placeholder_and_partial_rejection=pass\n'
printf 'oversize_and_same-hash_rejection=pass\n'
printf 'foundation=hash-pinned-calibrated-candidate-x-installer\n'
printf 'bounded_target_writes=one\npredecessor=exact-installed-candidate-x\n'
printf 'caller_hash_override_rejection=pass\n'
printf 'device_contact=none\nhardware_write=none\nreboot=none\n'
