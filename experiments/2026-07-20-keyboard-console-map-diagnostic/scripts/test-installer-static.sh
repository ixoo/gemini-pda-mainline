#!/usr/bin/env bash

# Literal derived-installer checks intentionally contain unexpanded shell text.
# shellcheck disable=SC2016

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
installer="$script_dir/install-candidate-aa-boot2.sh"
aa_r0_deriver="$script_dir/derive-installer.py"
aa_r1_revision_deriver="$script_dir/derive-revision-installer.py"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
z_experiment="$repo_root/experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic"
y_experiment="$repo_root/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic"
z_deriver="$z_experiment/scripts/derive-installer.py"
y_wrapper="$y_experiment/scripts/install-candidate-y-boot2.sh"
y_deriver="$y_experiment/scripts/derive-installer.py"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
for input in \
	"$installer" \
	"$aa_r0_deriver" \
	"$aa_r1_revision_deriver" \
	"$z_deriver" \
	"$y_wrapper" \
	"$y_deriver" \
	"$x_installer"; do
	[[ -f "$input" && ! -L "$input" ]] || die "installer test input missing: $input"
done
for command in awk bash chmod cp env grep mkdir mktemp python3 rm sed sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly AA_R1_WRAPPER_TEMPLATE_SHA256=f2c07d06c7125299ee6cdce4bb9ccd65c5a43747988d9ac32b9a1b82c9decc0e
readonly AA_R1_CALIBRATED_WRAPPER_SHA256=94b26c3410dd06254b91505833cd26bb87cefb102df5b03e296370e5054f414c
readonly AA_R1_REVISION_DERIVER_SHA256=cd3676188f4d77fcff3321bdf046c46999e1859ba91903a08e6781928e983fb9
readonly AA_R0_DERIVER_SHA256=acbd27b3cf782ce7930059b4c91e00b113399a503fb84e9296a06b6199f65d1a
readonly Z_DERIVER_SHA256=7bd871c8b068a3330996d145a1979c076d79db032e7b0efe97d868a00664f51a
readonly Y_WRAPPER_SHA256=1a33de1f640650164155ed20555b162a2b9455d2495e46a3065589b2d1759268
readonly Y_DERIVER_SHA256=ac343dc456f90098fbe28062148aa2f79d1b27b436ce7065a71e8a56c13f24e7
readonly X_INSTALLER_SHA256=2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e
readonly Y_DERIVED_INSTALLER_SHA256=923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67
readonly Z_DERIVED_INSTALLER_SHA256=38b5956e3f5146bc2c8e8ddc3cec9cfb8be25bd3661949b5bd8fb5dbdba51b76
readonly AA_R0_DERIVED_INSTALLER_SHA256=c920eca1207dfe1362f947a74935a50fd934574f7becae4d056b09f362d46196
readonly AA_R0_RAW_SHA256=a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c
readonly AA_R0_RAW_SIZE=7120896
readonly AA_R0_PADDED_SHA256=157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa
readonly Z_PADDED_SHA256=ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40
readonly Y_PADDED_SHA256=dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17

readonly AA_R1_RAW_SHA256=37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7
readonly AA_R1_RAW_SIZE=7378944
readonly AA_R1_PADDED_SHA256=38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703
readonly AA_R1_DERIVED_INSTALLER_SHA256=f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f

# Synthetic, non-artifact values make the complete r1 program available for
# structural testing without pretending the current boot image is calibrated.
readonly FIXTURE_AA_R1_RAW_SHA256=1111111111111111111111111111111111111111111111111111111111111111
readonly FIXTURE_AA_R1_RAW_SIZE=7120897
readonly FIXTURE_AA_R1_PADDED_SHA256=2222222222222222222222222222222222222222222222222222222222222222
readonly FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256=ff761fd3c9a17e588a96f0a540aa8adf150e0605b2b712270dbc0ccb0a1061ca

for check in \
	"$installer:$AA_R1_CALIBRATED_WRAPPER_SHA256" \
	"$aa_r1_revision_deriver:$AA_R1_REVISION_DERIVER_SHA256" \
	"$aa_r0_deriver:$AA_R0_DERIVER_SHA256" \
	"$z_deriver:$Z_DERIVER_SHA256" \
	"$y_wrapper:$Y_WRAPPER_SHA256" \
	"$y_deriver:$Y_DERIVER_SHA256" \
	"$x_installer:$X_INSTALLER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "hash-pinned installer input changed: $path"
done
bash -n "$installer"
python3 "$aa_r1_revision_deriver" --help >/dev/null

assignment_value() {
	local name=$1
	local lines count
	lines="$(grep -E "^readonly ${name}=" "$installer" || true)"
	count="$(printf '%s\n' "$lines" | awk 'NF { count++ } END { print count + 0 }')"
	[[ "$count" == 1 ]] || die "installer pin is absent or duplicated: $name"
	printf '%s\n' "${lines#*=}"
}

for pin in \
	"AA_R1_RAW_SHA256:$AA_R1_RAW_SHA256" \
	"AA_R1_RAW_SIZE:$AA_R1_RAW_SIZE" \
	"AA_R1_PADDED_SHA256:$AA_R1_PADDED_SHA256" \
	"AA_R1_DERIVED_INSTALLER_SHA256:$AA_R1_DERIVED_INSTALLER_SHA256" \
	"EXPECTED_CURRENT_AA_R0_PADDED_SHA256:$AA_R0_PADDED_SHA256" \
	"AA_R0_RAW_SHA256:$AA_R0_RAW_SHA256" \
	"AA_R0_RAW_SIZE:$AA_R0_RAW_SIZE" \
	"AA_R0_PADDED_SHA256:$AA_R0_PADDED_SHA256" \
	"AA_R0_DERIVED_INSTALLER_SHA256:$AA_R0_DERIVED_INSTALLER_SHA256" \
	"AA_R0_DERIVER_SHA256:$AA_R0_DERIVER_SHA256" \
	"AA_R1_REVISION_DERIVER_SHA256:$AA_R1_REVISION_DERIVER_SHA256" \
	"Z_DERIVED_INSTALLER_SHA256:$Z_DERIVED_INSTALLER_SHA256" \
	"Z_DERIVER_SHA256:$Z_DERIVER_SHA256" \
	"Y_DERIVED_INSTALLER_SHA256:$Y_DERIVED_INSTALLER_SHA256" \
	"Y_WRAPPER_SHA256:$Y_WRAPPER_SHA256" \
	"Y_DERIVER_SHA256:$Y_DERIVER_SHA256" \
	"X_INSTALLER_SHA256:$X_INSTALLER_SHA256"; do
	name=${pin%%:*}
	expected=${pin##*:}
	[[ "$(assignment_value "$name")" == "$expected" ]] || \
		die "wrapper calibration/foundation pin changed: $name"
done

workdir="$(mktemp -d /tmp/candidate-aa-r1-installer-static.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

expect_status_error() {
	local expected_status=$1 expected_error=$2 label=$3
	shift 3
	set +e
	"$@" >"$workdir/$label.out" 2>"$workdir/$label.err"
	local status=$?
	set -e
	[[ "$status" == "$expected_status" ]] || \
		die "$label returned $status, expected $expected_status"
	if ! grep -Fxq "$expected_error" "$workdir/$label.err"; then
		sed 's/^/observed: /' "$workdir/$label.err" >&2
		die "$label error changed"
	fi
}

calibrate_wrapper() {
	local source=$1 output=$2 raw_sha256=$3 raw_size=$4 padded_sha256=$5
	local derived_sha256=$6
	sed \
		-e "s|^readonly AA_R1_RAW_SHA256=.*|readonly AA_R1_RAW_SHA256=$raw_sha256|" \
		-e "s|^readonly AA_R1_RAW_SIZE=.*|readonly AA_R1_RAW_SIZE=$raw_size|" \
		-e "s|^readonly AA_R1_PADDED_SHA256=.*|readonly AA_R1_PADDED_SHA256=$padded_sha256|" \
		-e "s|^readonly AA_R1_DERIVED_INSTALLER_SHA256=.*|readonly AA_R1_DERIVED_INSTALLER_SHA256=$derived_sha256|" \
		"$source" >"$output"
	chmod 0755 "$output"
}

uncalibrate_wrapper() {
	local source=$1 output=$2
	sed \
		-e 's|^readonly AA_R1_RAW_SHA256=.*|readonly AA_R1_RAW_SHA256=REPLACE_AFTER_CALIBRATION_AA_R1_BOOT_SHA256|' \
		-e 's|^readonly AA_R1_RAW_SIZE=.*|readonly AA_R1_RAW_SIZE=REPLACE_AFTER_CALIBRATION_AA_R1_BOOT_SIZE|' \
		-e 's|^readonly AA_R1_PADDED_SHA256=.*|readonly AA_R1_PADDED_SHA256=REPLACE_AFTER_CALIBRATION_AA_R1_PADDED_BOOT2_SHA256|' \
		-e 's|^readonly AA_R1_DERIVED_INSTALLER_SHA256=.*|readonly AA_R1_DERIVED_INSTALLER_SHA256=REPLACE_AFTER_CALIBRATION_AA_R1_DERIVED_INSTALLER_SHA256|' \
		"$source" >"$output"
	chmod 0755 "$output"
}

make_fixture_repo() {
	local mirror_root=$1
	local mirror_x mirror_y mirror_z mirror_aa
	mirror_x="$mirror_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts"
	mirror_y="$mirror_root/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/scripts"
	mirror_z="$mirror_root/experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts"
	mirror_aa="$mirror_root/experiments/2026-07-20-keyboard-console-map-diagnostic/scripts"
	mkdir -p "$mirror_x" "$mirror_y" "$mirror_z" "$mirror_aa"
	cp "$x_installer" "$mirror_x/install-candidate-x-boot2.sh"
	cp "$y_wrapper" "$mirror_y/install-candidate-y-boot2.sh"
	cp "$y_deriver" "$mirror_y/derive-installer.py"
	cp "$z_deriver" "$mirror_z/derive-installer.py"
	cp "$aa_r0_deriver" "$mirror_aa/derive-installer.py"
	cp "$aa_r1_revision_deriver" "$mirror_aa/derive-revision-installer.py"
	calibrate_wrapper "$installer" "$mirror_aa/install-candidate-aa-boot2.sh" \
		"$FIXTURE_AA_R1_RAW_SHA256" "$FIXTURE_AA_R1_RAW_SIZE" \
		"$FIXTURE_AA_R1_PADDED_SHA256" \
		"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
}

# Reconstruct every exact installed generation before applying the synthetic
# r1 calibration. Each resulting program is pinned independently.
derived_y="$workdir/install-candidate-y-boot2.sh"
python3 "$y_deriver" --source "$x_installer" --output "$derived_y" \
	--raw-sha256 94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee \
	--raw-size 6866944 --padded-sha256 "$Y_PADDED_SHA256"
[[ "$(sha256sum "$derived_y" | awk '{print $1}')" == \
	"$Y_DERIVED_INSTALLER_SHA256" ]] || die 'exact Candidate Y reconstruction changed'

derived_z="$workdir/install-candidate-z-boot2.sh"
python3 "$z_deriver" --source "$derived_y" --output "$derived_z" \
	--raw-sha256 985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9 \
	--raw-size 6866944 --padded-sha256 "$Z_PADDED_SHA256"
[[ "$(sha256sum "$derived_z" | awk '{print $1}')" == \
	"$Z_DERIVED_INSTALLER_SHA256" ]] || die 'exact Candidate Z reconstruction changed'

derived_aa_r0="$workdir/install-candidate-aa-r0-boot2.sh"
python3 "$aa_r0_deriver" --source "$derived_z" --output "$derived_aa_r0" \
	--raw-sha256 "$AA_R0_RAW_SHA256" --raw-size "$AA_R0_RAW_SIZE" \
	--padded-sha256 "$AA_R0_PADDED_SHA256"
bash -n "$derived_aa_r0"
[[ "$(sha256sum "$derived_aa_r0" | awk '{print $1}')" == \
	"$AA_R0_DERIVED_INSTALLER_SHA256" ]] || \
	die 'exact Candidate AA r0 reconstruction changed'

derived_aa_r1="$workdir/install-candidate-aa-r1-boot2.sh"
python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$derived_aa_r1" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" \
	--raw-size "$FIXTURE_AA_R1_RAW_SIZE" \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
bash -n "$derived_aa_r1"
[[ "$(sha256sum "$derived_aa_r1" | awk '{print $1}')" == \
	"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256" ]] || \
	die 'synthetic Candidate AA r1 derivation changed'

# Audit the exact r1 program. These strings cover live-GPT identity, root and
# in-use exclusions, stable power/boot identity, predecessor checksum, the
# final pre-write gate, one bounded write, flush, and complete readback.
for token in \
	'readlink -f /dev/disk/by-partlabel/boot2' \
	'live GPT has $row_count exact boot2 rows' \
	'boot2 parent is not mmcblk0' \
	'boot2 is not root-readable and writable' \
	'boot2 is the active root' \
	'boot2 is mounted' \
	'boot2 is active swap' \
	'boot2 has holders' \
	"power_first\" == '1|1|Full|100|Good'" \
	'boot ID changed immediately before write' \
	'boot2 changed at the final pre-write checksum' \
	'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4' \
	'blockdev --flushbufs "$target"' \
	'post-flush checksum mismatch' \
	'full boot2 readback stream length mismatch' \
	'full boot2 readback checksum mismatch' \
	'full boot2 readback differs byte-for-byte' \
	'final live boot2/root/power/boot-ID gate failed' \
	'reboot_or_shutdown_performed=no'; do
	grep -Fq "$token" "$derived_aa_r1" || \
		die "derived installer safety gate absent: $token"
done
[[ "$(grep -Fc 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4' \
	"$derived_aa_r1")" == 1 ]] || \
	die 'derived installer lacks exactly one bounded target write'
[[ "$(grep -Fc 'of="$target"' "$derived_aa_r1")" == 1 ]] || \
	die 'derived installer gained another direct target write'

for token in \
	"readonly AA_R1_RAW_SHA256=$FIXTURE_AA_R1_RAW_SHA256" \
	"readonly AA_R1_RAW_SIZE=$FIXTURE_AA_R1_RAW_SIZE" \
	"readonly AA_R1_PADDED_SHA256=$FIXTURE_AA_R1_PADDED_SHA256" \
	"readonly EXPECTED_CURRENT_AA_R0_PADDED_SHA256=$AA_R0_PADDED_SHA256" \
	'[[ "$candidate_name" == gemini-keyboard-console-map.boot.img ]]' \
	'expected_artifact_name="candidate-AA-keyboard-console-map-final-${AA_R1_RAW_SHA256:0:8}"' \
	'experiment=2026-07-20-keyboard-console-map-diagnostic' \
	'expected_previous_label=AA-r0-superseded-before-boot' \
	'initial gate returned an inconsistent AA-r0-superseded-before-boot predecessor checksum' \
	'candidate-aa-r1-padded-boot2.img' \
	'.gemini-candidate-aa-r1.' \
	'.gemini-candidate-aa-r1-root.' \
	'boot2-before-candidate-aa-r1.img' \
	'boot2-after-candidate-aa-r1.img'; do
	grep -Fq "$token" "$derived_aa_r1" || \
		die "derived artifact/predecessor token absent: $token"
done
[[ "$(grep -Fc 'candidate_label=AA-r1' "$derived_aa_r1")" == 2 ]] || \
	die 'derived installer candidate-label count changed'
[[ "$(grep -Fc 'experiment=2026-07-20-keyboard-console-map-diagnostic' \
	"$derived_aa_r1")" == 2 ]] || die 'derived installer experiment-token count changed'
[[ "$(grep -Fc 'expected_previous_label=AA-r0-superseded-before-boot' \
	"$derived_aa_r1")" == 1 ]] || die 'derived installer predecessor-label count changed'

for forbidden in \
	'Candidate Z' \
	'EXPECTED_CURRENT_Z' \
	'expected_previous_label=Z' \
	"$Z_PADDED_SHA256" \
	'boot2-before-candidate-aa.img' \
	'boot2-after-candidate-aa.img'; do
	! grep -Fq "$forbidden" "$derived_aa_r1" || \
		die "derived installer retained superseded Z state: $forbidden"
done
if grep -Eq \
	'^[[:space:]]*(sudo[[:space:]]+[^#]*)?(reboot|shutdown|poweroff|halt|kexec)([[:space:]]|$)' \
	"$derived_aa_r1" || grep -Fq 'sysrq-trigger' "$derived_aa_r1"; then
	die 'derived installer gained reboot, shutdown, kexec, or sysrq behavior'
fi

# The revision deriver must reject any altered r0 foundation, malformed or
# oversized calibration, either predecessor identity, and output overwrite.
modified_aa_r0="$workdir/modified-aa-r0.sh"
cp "$derived_aa_r0" "$modified_aa_r0"
printf '\n' >>"$modified_aa_r0"
expect_status_error 2 'error: exact Candidate AA r0 derived installer changed' \
	modified-foundation python3 "$aa_r1_revision_deriver" \
	--source "$modified_aa_r0" --output "$workdir/from-modified.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" \
	--raw-size "$FIXTURE_AA_R1_RAW_SIZE" \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 installer hashes are not calibrated SHA-256 values' \
	deriver-invalid-raw python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/invalid-raw.sh" \
	--raw-sha256 invalid --raw-size "$FIXTURE_AA_R1_RAW_SIZE" \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 installer hashes are not calibrated SHA-256 values' \
	deriver-invalid-padded python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/invalid-padded.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" \
	--raw-size "$FIXTURE_AA_R1_RAW_SIZE" --padded-sha256 invalid
expect_status_error 2 'error: Candidate AA r1 installer size is invalid or oversized' \
	deriver-oversize python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/deriver-oversize.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" --raw-size 16777217 \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
expect_status_error 2 'error: Candidate AA r1 installer size is invalid or oversized' \
	deriver-zero-size python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/deriver-zero-size.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" --raw-size 0 \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 identity equals the installed AA r0 predecessor' \
	deriver-same-raw python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/deriver-same-raw.sh" \
	--raw-sha256 "$AA_R0_RAW_SHA256" --raw-size "$FIXTURE_AA_R1_RAW_SIZE" \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 identity equals the installed AA r0 predecessor' \
	deriver-same-padded python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/deriver-same-padded.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" \
	--raw-size "$FIXTURE_AA_R1_RAW_SIZE" --padded-sha256 "$AA_R0_PADDED_SHA256"
cp "$derived_aa_r1" "$workdir/existing-output.sh"
expect_status_error 2 'error: refusing to overwrite derived installer' \
	deriver-overwrite python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$workdir/existing-output.sh" \
	--raw-sha256 "$FIXTURE_AA_R1_RAW_SHA256" \
	--raw-size "$FIXTURE_AA_R1_RAW_SIZE" \
	--padded-sha256 "$FIXTURE_AA_R1_PADDED_SHA256"

# Shadow every device-contact command before testing wrapper help and
# rejections. A calibrated fixture repository preserves the exact relative
# layout without touching the real device or requiring a real boot artifact.
mkdir "$workdir/contact-traps"
export CONTACT_MARKER="$workdir/device-contact-attempted"
for command in ssh sudo; do
	{
		printf '%s\n' '#!/usr/bin/env bash'
		printf '%s\n' "printf '%s\\n' '$command' >>\"\$CONTACT_MARKER\""
		printf '%s\n' 'exit 99'
	} >"$workdir/contact-traps/$command"
	chmod 0755 "$workdir/contact-traps/$command"
done
shadow_path="$workdir/contact-traps:$PATH"

uncalibrated_wrapper="$workdir/uncalibrated-wrapper.sh"
uncalibrate_wrapper "$installer" "$uncalibrated_wrapper"
[[ "$(sha256sum "$uncalibrated_wrapper" | awk '{print $1}')" == \
	"$AA_R1_WRAPPER_TEMPLATE_SHA256" ]] || die 'uncalibrated wrapper template changed'
expect_status_error 2 'error: calibration placeholder remains: AA_R1_RAW_SHA256' \
	uncalibrated env PATH="$shadow_path" "$uncalibrated_wrapper" --help

invalid_hash_wrapper="$workdir/invalid-hash-wrapper.sh"
calibrate_wrapper "$installer" "$invalid_hash_wrapper" invalid \
	"$FIXTURE_AA_R1_RAW_SIZE" "$FIXTURE_AA_R1_PADDED_SHA256" \
	"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
expect_status_error 2 'error: invalid calibrated SHA-256: AA_R1_RAW_SHA256' \
	wrapper-invalid-hash env PATH="$shadow_path" "$invalid_hash_wrapper" --help

oversize_wrapper="$workdir/oversize-wrapper.sh"
calibrate_wrapper "$installer" "$oversize_wrapper" \
	"$FIXTURE_AA_R1_RAW_SHA256" 16777217 "$FIXTURE_AA_R1_PADDED_SHA256" \
	"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
expect_status_error 2 'error: invalid or oversized calibrated AA_R1_RAW_SIZE' \
	wrapper-oversize env PATH="$shadow_path" "$oversize_wrapper" --help

same_raw_wrapper="$workdir/same-raw-wrapper.sh"
calibrate_wrapper "$installer" "$same_raw_wrapper" "$AA_R0_RAW_SHA256" \
	"$FIXTURE_AA_R1_RAW_SIZE" "$FIXTURE_AA_R1_PADDED_SHA256" \
	"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 identity unexpectedly equals installed AA r0 predecessor' \
	wrapper-same-raw env PATH="$shadow_path" "$same_raw_wrapper" --help

same_padded_wrapper="$workdir/same-padded-wrapper.sh"
calibrate_wrapper "$installer" "$same_padded_wrapper" \
	"$FIXTURE_AA_R1_RAW_SHA256" "$FIXTURE_AA_R1_RAW_SIZE" \
	"$AA_R0_PADDED_SHA256" "$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
expect_status_error 2 \
	'error: Candidate AA r1 identity unexpectedly equals installed AA r0 predecessor' \
	wrapper-same-padded env PATH="$shadow_path" "$same_padded_wrapper" --help

fixture_repo="$workdir/fixture-repo"
make_fixture_repo "$fixture_repo"
fixture_wrapper="$fixture_repo/experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/install-candidate-aa-boot2.sh"

bad_derived_wrapper="${fixture_wrapper%.sh}-bad-derived.sh"
calibrate_wrapper "$installer" "$bad_derived_wrapper" \
	"$FIXTURE_AA_R1_RAW_SHA256" "$FIXTURE_AA_R1_RAW_SIZE" \
	"$FIXTURE_AA_R1_PADDED_SHA256" \
	3333333333333333333333333333333333333333333333333333333333333333
expect_status_error 2 'error: derived Candidate AA r1 installer changed' \
	wrapper-bad-derived env PATH="$shadow_path" "$bad_derived_wrapper" --help

modified_repo="$workdir/modified-foundation-repo"
make_fixture_repo "$modified_repo"
modified_repo="$(cd -- "$modified_repo" && pwd -P)"
modified_wrapper="$modified_repo/experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/install-candidate-aa-boot2.sh"
modified_x="$modified_repo/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
printf '\n' >>"$modified_x"
expect_status_error 2 \
	"error: hash-pinned installer foundation changed: $modified_x" \
	wrapper-modified-foundation env PATH="$shadow_path" "$modified_wrapper" --help

PATH="$shadow_path" "$fixture_wrapper" --help >"$workdir/help.out"
grep -Fq 'usage: install-candidate-aa-boot2.sh' "$workdir/help.out" || \
	die 'fixture-calibrated wrapper help did not reach exact Candidate AA r1'
expect_status_error 2 'error: all three explicit arguments are required' \
	missing-args env PATH="$shadow_path" "$fixture_wrapper"
expect_status_error 2 'error: unknown argument: --expected-current-sha256' \
	caller-checksum-override env PATH="$shadow_path" "$fixture_wrapper" \
	--expected-current-sha256 \
	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
[[ ! -e "$CONTACT_MARKER" && ! -L "$CONTACT_MARKER" ]] || \
	die 'help or rejection path attempted device contact'

printf 'validation=candidate-aa-r1-installer-static\n'
printf 'wrapper_template_sha256=%s\ncalibrated_wrapper_sha256=%s\n' \
	"$AA_R1_WRAPPER_TEMPLATE_SHA256" "$AA_R1_CALIBRATED_WRAPPER_SHA256"
printf 'revision_deriver_sha256=%s\n' "$AA_R1_REVISION_DERIVER_SHA256"
printf 'derived_y_sha256=%s\nderived_z_sha256=%s\nderived_aa_r0_sha256=%s\n' \
	"$Y_DERIVED_INSTALLER_SHA256" "$Z_DERIVED_INSTALLER_SHA256" \
	"$AA_R0_DERIVED_INSTALLER_SHA256"
printf 'fixture_derived_aa_r1_sha256=%s\n' \
	"$FIXTURE_AA_R1_DERIVED_INSTALLER_SHA256"
printf 'aa_r1_raw_sha256=%s\naa_r1_raw_size=%s\naa_r1_padded_sha256=%s\n' \
	"$AA_R1_RAW_SHA256" "$AA_R1_RAW_SIZE" "$AA_R1_PADDED_SHA256"
printf 'aa_r1_derived_installer_sha256=%s\n' \
	"$AA_R1_DERIVED_INSTALLER_SHA256"
printf 'aa_r1_calibrated_wrapper_sha256=%s\n' \
	"$AA_R1_CALIBRATED_WRAPPER_SHA256"
printf 'bash_syntax=pass\nwrapper_rejections=8/8\nderiver_rejections=8/8\n'
printf 'bounded_target_writes=one\npredecessor=AA-r0-superseded-before-boot\n'
printf 'caller_hash_override_rejection=pass\nhelp_no_contact=pass\n'
printf 'device_contact=none\nhardware_write=none\nreboot=none\n'
