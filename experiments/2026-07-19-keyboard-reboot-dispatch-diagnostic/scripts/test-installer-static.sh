#!/usr/bin/env bash

# Literal derived-installer checks intentionally contain unexpanded shell text.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
installer="$script_dir/install-candidate-z-boot2.sh"
z_deriver="$script_dir/derive-installer.py"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
y_experiment="$repo_root/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic"
y_wrapper="$y_experiment/scripts/install-candidate-y-boot2.sh"
y_deriver="$y_experiment/scripts/derive-installer.py"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
for input in "$installer" "$z_deriver" "$y_wrapper" "$y_deriver" "$x_installer"; do
	[[ -f "$input" && ! -L "$input" ]] || die "installer test input missing: $input"
done
for command in awk bash chmod cp grep mkdir mktemp python3 rm sed sha256sum; do
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

readonly Z_RAW_SHA256=985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9
readonly Z_RAW_SIZE=6866944
readonly Z_PADDED_SHA256=ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40
[[ "$(assignment_value Z_RAW_SHA256)" == "$Z_RAW_SHA256" ]] || \
	die 'Candidate Z raw-image calibration changed'
[[ "$(assignment_value Z_RAW_SIZE)" == "$Z_RAW_SIZE" ]] || \
	die 'Candidate Z raw-size calibration changed'
[[ "$(assignment_value Z_PADDED_SHA256)" == "$Z_PADDED_SHA256" ]] || \
	die 'Candidate Z padded-image calibration changed'
readonly Y_PADDED_SHA256=dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17
readonly Y_DERIVED_INSTALLER_SHA256=923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67
readonly Y_WRAPPER_SHA256=1a33de1f640650164155ed20555b162a2b9455d2495e46a3065589b2d1759268
readonly Y_DERIVER_SHA256=ac343dc456f90098fbe28062148aa2f79d1b27b436ce7065a71e8a56c13f24e7
readonly X_INSTALLER_SHA256=2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e
[[ "$(assignment_value EXPECTED_CURRENT_Y_PADDED_SHA256)" == "$Y_PADDED_SHA256" ]] || \
	die 'Candidate Z predecessor pin changed'
[[ "$(assignment_value Y_DERIVED_INSTALLER_SHA256)" == \
	"$Y_DERIVED_INSTALLER_SHA256" ]] || die 'derived Candidate Y installer pin changed'
[[ "$(assignment_value Y_WRAPPER_SHA256)" == "$Y_WRAPPER_SHA256" ]] || \
	die 'Candidate Y wrapper pin changed'
[[ "$(assignment_value Y_DERIVER_SHA256)" == "$Y_DERIVER_SHA256" ]] || \
	die 'Candidate Y deriver pin changed'
[[ "$(assignment_value X_INSTALLER_SHA256)" == "$X_INSTALLER_SHA256" ]] || \
	die 'Candidate X installer pin changed'
for check in \
	"$y_wrapper:$Y_WRAPPER_SHA256" \
	"$y_deriver:$Y_DERIVER_SHA256" \
	"$x_installer:$X_INSTALLER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "hash-pinned installer foundation changed: $path"
done

workdir="$(mktemp -d /tmp/candidate-z-installer-static.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

invoke_rejection() {
	local selected=$1 expected=$2 label=$3
	set +e
	"$selected" --help >"$workdir/$label.out" 2>"$workdir/$label.err"
	local rc=$?
	set -e
	[[ "$rc" == 2 ]] || die "$label rejection returned $rc"
	grep -Fxq "$expected" "$workdir/$label.err" || die "$label rejection changed"
}

# Recreate an uncalibrated wrapper in an isolated directory. Its exact error
# proves the placeholder gate still precedes repository, SSH, and device work.
mkdir "$workdir/isolated"
sed \
	-e 's/^readonly Z_RAW_SHA256=.*/readonly Z_RAW_SHA256=REPLACE_AFTER_CALIBRATION_Z_BOOT_SHA256/' \
	-e 's/^readonly Z_RAW_SIZE=.*/readonly Z_RAW_SIZE=REPLACE_AFTER_CALIBRATION_Z_BOOT_SIZE/' \
	-e 's/^readonly Z_PADDED_SHA256=.*/readonly Z_PADDED_SHA256=REPLACE_AFTER_CALIBRATION_Z_PADDED_BOOT2_SHA256/' \
	"$installer" >"$workdir/isolated/install-candidate-z-boot2.sh"
chmod 0755 "$workdir/isolated/install-candidate-z-boot2.sh"
invoke_rejection "$workdir/isolated/install-candidate-z-boot2.sh" \
	'error: calibration placeholder remains: Z_RAW_SHA256' uncalibrated-isolated

partial="$workdir/partial.sh"
sed 's/^readonly Z_RAW_SHA256=.*/readonly Z_RAW_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
	"$workdir/isolated/install-candidate-z-boot2.sh" >"$partial"
chmod 0755 "$partial"
invoke_rejection "$partial" 'error: calibration placeholder remains: Z_RAW_SIZE' partial

calibrate_wrapper() {
	local source=$1 destination=$2 raw_sha=$3 raw_size=$4 padded_sha=$5
	sed \
		-e "s/^readonly Z_RAW_SHA256=.*/readonly Z_RAW_SHA256=$raw_sha/" \
		-e "s/^readonly Z_RAW_SIZE=.*/readonly Z_RAW_SIZE=$raw_size/" \
		-e "s/^readonly Z_PADDED_SHA256=.*/readonly Z_PADDED_SHA256=$padded_sha/" \
		"$source" >"$destination"
	chmod 0755 "$destination"
}

readonly FAKE_RAW_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
readonly FAKE_RAW_SIZE=7000000
readonly FAKE_PADDED_SHA256=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
oversize="$workdir/oversize.sh"
calibrate_wrapper "$installer" "$oversize" "$FAKE_RAW_SHA256" 16777217 \
	"$FAKE_PADDED_SHA256"
invoke_rejection "$oversize" 'error: invalid or oversized calibrated Z_RAW_SIZE' oversize

same_hash="$workdir/same-hash.sh"
calibrate_wrapper "$installer" "$same_hash" "$FAKE_RAW_SHA256" "$FAKE_RAW_SIZE" \
	"$Y_PADDED_SHA256"
invoke_rejection "$same_hash" \
	'error: Candidate Z padded hash unexpectedly equals the Candidate Y predecessor' same-hash

# Reconstruct the exact calibrated Candidate Y installer, then derive a fake-
# calibrated Z installer for static inspection. No derived code proceeds past
# --help, so this exercise cannot reach SSH or a device.
derived_y="$workdir/derived-y.sh"
python3 "$y_deriver" --source "$x_installer" --output "$derived_y" \
	--raw-sha256 94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee \
	--raw-size 6866944 --padded-sha256 "$Y_PADDED_SHA256"
[[ "$(sha256sum "$derived_y" | awk '{print $1}')" == \
	"$Y_DERIVED_INSTALLER_SHA256" ]] || die 'exact Candidate Y reconstruction changed'

derived_z="$workdir/derived-z.sh"
python3 "$z_deriver" --source "$derived_y" --output "$derived_z" \
	--raw-sha256 "$FAKE_RAW_SHA256" --raw-size "$FAKE_RAW_SIZE" \
	--padded-sha256 "$FAKE_PADDED_SHA256"
bash -n "$derived_z"
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
	grep -Fq "$token" "$derived_z" || die "derived installer safety gate absent: $token"
done
[[ "$(grep -Fc 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4' \
	"$derived_z")" == 1 ]] || die 'derived installer does not contain exactly one bounded target write'
grep -Fq "readonly Z_RAW_SHA256=$FAKE_RAW_SHA256" "$derived_z" || \
	die 'derived raw-image pin changed'
grep -Fq "readonly Z_RAW_SIZE=$FAKE_RAW_SIZE" "$derived_z" || \
	die 'derived raw-size pin changed'
grep -Fq "readonly Z_PADDED_SHA256=$FAKE_PADDED_SHA256" "$derived_z" || \
	die 'derived padded-image pin changed'
grep -Fq "readonly EXPECTED_CURRENT_Y_PADDED_SHA256=$Y_PADDED_SHA256" \
	"$derived_z" || die 'derived predecessor pin changed'
grep -Fq 'gemini-keyboard-reboot-dispatch.boot.img' "$derived_z" || \
	die 'derived Candidate Z filename changed'
grep -Fq 'expected_artifact_name="candidate-Z-keyboard-reboot-dispatch-final-${Z_RAW_SHA256:0:8}"' \
	"$derived_z" || die 'derived Candidate Z artifact contract changed'
[[ "$(grep -Fc 'candidate_label=Z' "$derived_z")" == 2 ]] || \
	die 'derived candidate labels changed'
grep -Fq 'expected_previous_label=Y' "$derived_z" || \
	die 'derived predecessor label changed'
if grep -Eq '^[[:space:]]*(sudo[[:space:]].*)?(reboot|shutdown|poweroff|halt|kexec)([[:space:]]|$)' \
	"$derived_z" || grep -Fq 'sysrq-trigger' "$derived_z"; then
	die 'derived installer gained reboot, shutdown, kexec, or sysrq behavior'
fi

# Exercise the wrapper's complete reconstruction/derivation path in an
# isolated fake repository, stopping at derived --help before device checks.
fake_repo="$workdir/fake-repo"
z_scripts="$fake_repo/experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts"
y_scripts="$fake_repo/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/scripts"
x_scripts="$fake_repo/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts"
mkdir -p "$z_scripts" "$y_scripts" "$x_scripts"
calibrate_wrapper "$installer" "$z_scripts/install-candidate-z-boot2.sh" \
	"$FAKE_RAW_SHA256" "$FAKE_RAW_SIZE" "$FAKE_PADDED_SHA256"
cp "$z_deriver" "$z_scripts/derive-installer.py"
cp "$y_wrapper" "$y_scripts/install-candidate-y-boot2.sh"
cp "$y_deriver" "$y_scripts/derive-installer.py"
cp "$x_installer" "$x_scripts/install-candidate-x-boot2.sh"
"$z_scripts/install-candidate-z-boot2.sh" --help >"$workdir/fake-help.out"
grep -Fq 'usage: install-candidate-z-boot2.sh' "$workdir/fake-help.out" || \
	die 'fake-calibrated wrapper did not reach the derived Candidate Z installer'

"$installer" --help >"$workdir/help.out" 2>"$workdir/help.err"
grep -Fq 'install-candidate-z-boot2.sh' "$workdir/help.out" "$workdir/help.err" || \
	die 'calibrated installer help did not reach the derived installer'

set +e
"$installer" --expected-current-sha256 \
	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc \
	>"$workdir/override.out" 2>"$workdir/override.err"
override_rc=$?
set -e
[[ "$override_rc" == 2 ]] || die 'caller checksum override was not rejected'
grep -Fxq 'error: unknown argument: --expected-current-sha256' \
	"$workdir/override.err" || die 'caller checksum override rejection changed'

printf 'validation=candidate-z-installer-static\n'
printf 'calibration_state=calibrated\n'
printf 'placeholder_and_partial_rejection=pass\n'
printf 'oversize_and_same-hash_rejection=pass\n'
printf 'fake_calibrated_derivation=pass\n'
printf 'foundation=hash-pinned-exact-derived-candidate-y-installer\n'
printf 'bounded_target_writes=one\npredecessor=exact-installed-candidate-y\n'
printf 'caller_hash_override_rejection=pass\n'
printf 'device_contact=none\nhardware_write=none\nreboot=none\n'
