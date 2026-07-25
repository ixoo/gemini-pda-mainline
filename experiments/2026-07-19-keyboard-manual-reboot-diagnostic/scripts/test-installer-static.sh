#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	printf 'error: %s\n' "$*" >&2
	exit 2
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
installer="$script_dir/install-candidate-x-boot2.sh"
[[ -f "$installer" && ! -L "$installer" && -x "$installer" ]] || \
	die 'Candidate X installer is missing, symlinked, or non-executable'

for command in awk bash chmod grep mktemp sed; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

bash -n "$installer" || die 'Candidate X installer failed bash syntax validation'

require_source_text() {
	local text=$1
	grep -Fq -- "$text" "$installer" || die "installer safety gate is absent: $text"
}

assignment_value() {
	local name=$1
	local lines
	local count
	lines="$(grep -E "^readonly ${name}=" "$installer" || true)"
	count="$(printf '%s\n' "$lines" | awk 'NF { count++ } END { print count + 0 }')"
	[[ "$count" == 1 ]] || die "installer pin is absent or duplicated: $name"
	printf '%s\n' "${lines#*=}"
}

source_raw_sha256="$(assignment_value X_RAW_SHA256)"
source_raw_size="$(assignment_value X_RAW_SIZE)"
source_padded_sha256="$(assignment_value X_PADDED_SHA256)"
source_current_w_sha256="$(assignment_value EXPECTED_CURRENT_W_PADDED_SHA256)"
source_pin_values=(
	"$source_raw_sha256" "$source_raw_size" "$source_padded_sha256"
	"$source_current_w_sha256"
)
source_placeholder_count=0
for value in "${source_pin_values[@]}"; do
	[[ "$value" != REPLACE_AFTER_CALIBRATION_* ]] || \
		source_placeholder_count=$((source_placeholder_count + 1))
done
case "$source_placeholder_count" in
4)
	source_calibration_state=fail-closed-placeholders
	;;
0)
	source_calibration_state=calibrated
	[[ "$source_raw_sha256" =~ ^[0-9a-f]{64}$ && \
		"$source_padded_sha256" =~ ^[0-9a-f]{64}$ ]] || \
		die 'calibrated Candidate X hashes are malformed'
	[[ "$source_raw_size" =~ ^[1-9][0-9]*$ && "$source_raw_size" -le 16777216 ]] || \
		die 'calibrated Candidate X raw size is malformed or oversized'
	[[ "$source_current_w_sha256" == \
		0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608 ]] || \
		die 'calibrated predecessor is not the exact installed Candidate W partition'
	[[ "$source_padded_sha256" != "$source_current_w_sha256" ]] || \
		die 'calibrated X padded hash equals its W predecessor'
	;;
*)
	die 'installer contains a partial calibration; all four pins must change together'
	;;
esac

for text in \
	'lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT' \
	"awk '\$2 == \"boot2\" { print }'" \
	'readlink -f /dev/disk/by-partlabel/boot2' \
	'boot2 parent is not mmcblk0' \
	'boot2 is the active root' \
	'boot2 is mounted' \
	'boot2 is active swap' \
	'boot2 has holders' \
	"\"\$power_first\" == '1|1|Full|100|Good'" \
	'boot ID changed immediately before write' \
	'boot2 changed at the final pre-write checksum' \
	"dd if=\"\$root_stage_file\" of=\"\$target\" bs=4M iflag=fullblock count=4" \
	"blockdev --flushbufs \"\$target\"" \
	'full boot2 readback differs byte-for-byte' \
	'reboot_or_shutdown_performed=no'; do
	require_source_text "$text"
done

write_count="$(grep -Fc \
	"dd if=\"\$root_stage_file\" of=\"\$target\" bs=4M iflag=fullblock count=4" \
	"$installer")"
[[ "$write_count" == 1 ]] || die 'installer does not contain exactly one bounded target write'

if grep -Fq -- '--expected-candidate-sha256' "$installer" || \
	grep -Fq -- '--expected-current-sha256' "$installer"; then
	die 'installer exposes a caller-controlled checksum override'
fi
if grep -Eq '^[[:space:]]*(sudo[[:space:]].*)?(reboot|shutdown|poweroff|halt|kexec)([[:space:]]|$)' \
	"$installer" || grep -Fq 'sysrq-trigger' "$installer"; then
	die 'installer contains a reboot, shutdown, kexec, or sysrq command path'
fi

workdir="$(mktemp -d /tmp/candidate-x-installer-static.XXXXXX)"
cleanup() {
	rm -rf -- "$workdir"
}
trap cleanup EXIT

invoke_without_device() {
	local selected_installer=$1
	local output=$2
	local error=$3
	set +e
	"$selected_installer" \
		--target gemini@192.0.2.1 \
		--candidate "$workdir/does-not-exist.boot.img" \
		--backup-dir "$workdir/not-a-private-backup" \
		>"$output" 2>"$error"
	local installer_rc=$?
	set -e
	[[ "$installer_rc" == 2 ]] || die "installer rejection returned $installer_rc"
}

uncalibrated="$workdir/uncalibrated-installer.sh"
sed \
	-e 's/^readonly X_RAW_SHA256=.*/readonly X_RAW_SHA256=REPLACE_AFTER_CALIBRATION_X_BOOT_SHA256/' \
	-e 's/^readonly X_RAW_SIZE=.*/readonly X_RAW_SIZE=REPLACE_AFTER_CALIBRATION_X_BOOT_SIZE/' \
	-e 's/^readonly X_PADDED_SHA256=.*/readonly X_PADDED_SHA256=REPLACE_AFTER_CALIBRATION_X_PADDED_BOOT2_SHA256/' \
	-e 's/^readonly EXPECTED_CURRENT_W_PADDED_SHA256=.*/readonly EXPECTED_CURRENT_W_PADDED_SHA256=REPLACE_AFTER_CALIBRATION_CURRENT_W_PADDED_BOOT2_SHA256/' \
	"$installer" >"$uncalibrated"
chmod 0700 "$uncalibrated"
invoke_without_device "$uncalibrated" "$workdir/original.out" "$workdir/original.err"
grep -Fxq 'error: calibration placeholder remains: X_RAW_SHA256' \
	"$workdir/original.err" || die 'uncalibrated installer did not fail at its first pin'

partial="$workdir/partial-installer.sh"
sed 's/^readonly X_RAW_SHA256=.*/readonly X_RAW_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
	"$uncalibrated" >"$partial"
chmod 0700 "$partial"
invoke_without_device "$partial" "$workdir/partial.out" "$workdir/partial.err"
grep -Fxq 'error: calibration placeholder remains: X_RAW_SIZE' \
	"$workdir/partial.err" || die 'partially calibrated installer did not fail closed'

calibrated="$workdir/calibrated-installer.sh"
sed \
	-e 's/^readonly X_RAW_SHA256=.*/readonly X_RAW_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
	-e 's/^readonly X_RAW_SIZE=.*/readonly X_RAW_SIZE=1/' \
	-e 's/^readonly X_PADDED_SHA256=.*/readonly X_PADDED_SHA256=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/' \
	-e 's/^readonly EXPECTED_CURRENT_W_PADDED_SHA256=.*/readonly EXPECTED_CURRENT_W_PADDED_SHA256=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc/' \
	"$installer" >"$calibrated"
chmod 0700 "$calibrated"
invoke_without_device "$calibrated" "$workdir/calibrated.out" "$workdir/calibrated.err"
if grep -Fq 'calibration placeholder remains' "$workdir/calibrated.err"; then
	die 'fully calibrated control remained behind the placeholder gate'
fi
grep -Fq 'error: private device-partition artifact root is missing or unsafe' \
	"$workdir/calibrated.err" || \
	grep -Fq 'error: missing regular Gemini identity:' "$workdir/calibrated.err" || \
	grep -Fq 'error: candidate must be a regular non-symlink file' \
		"$workdir/calibrated.err" || \
	die 'fully calibrated control did not reach a pre-SSH local artifact gate'

oversize="$workdir/oversize-installer.sh"
sed 's/^readonly X_RAW_SIZE=.*/readonly X_RAW_SIZE=16777217/' \
	"$calibrated" >"$oversize"
chmod 0700 "$oversize"
invoke_without_device "$oversize" "$workdir/oversize.out" "$workdir/oversize.err"
grep -Fxq 'error: calibrated Candidate X size exceeds logical boot2 capacity' \
	"$workdir/oversize.err" || die 'oversize calibrated candidate was not rejected'

same_hash="$workdir/same-hash-installer.sh"
sed 's/^readonly EXPECTED_CURRENT_W_PADDED_SHA256=.*/readonly EXPECTED_CURRENT_W_PADDED_SHA256=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/' \
	"$calibrated" >"$same_hash"
chmod 0700 "$same_hash"
invoke_without_device "$same_hash" "$workdir/same-hash.out" "$workdir/same-hash.err"
grep -Fxq \
	'error: Candidate X padded hash unexpectedly equals the Candidate W predecessor' \
	"$workdir/same-hash.err" || die 'same predecessor/candidate hash was not rejected'

set +e
"$installer" --expected-current-sha256 \
	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc \
	>"$workdir/override.out" 2>"$workdir/override.err"
override_rc=$?
set -e
[[ "$override_rc" == 2 ]] || die 'caller checksum override was not rejected'
grep -Fxq 'error: unknown argument: --expected-current-sha256' \
	"$workdir/override.err" || die 'caller checksum override rejection changed'

printf 'validation=candidate-x-installer-static\n'
printf 'source_calibration_state=%s\n' "$source_calibration_state"
printf 'placeholder_gate=pass\n'
printf 'partial_calibration_rejection=pass\n'
printf 'oversize_rejection=pass\n'
printf 'same_hash_rejection=pass\n'
printf 'caller_hash_override_rejection=pass\n'
printf 'device_contact=none\nhardware_write=none\nreboot=none\n'
