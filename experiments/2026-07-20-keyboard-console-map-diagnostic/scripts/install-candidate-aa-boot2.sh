#!/usr/bin/env bash

# The cleanup function is invoked indirectly by the EXIT trap.
# shellcheck disable=SC2317

set -euo pipefail
export LC_ALL=C
umask 077

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly AA_R1_RAW_SHA256=37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7
readonly AA_R1_RAW_SIZE=7378944
readonly AA_R1_PADDED_SHA256=38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703
readonly AA_R1_DERIVED_INSTALLER_SHA256=f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f
readonly EXPECTED_CURRENT_AA_R0_PADDED_SHA256=157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa
readonly AA_R0_RAW_SHA256=a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c
readonly AA_R0_RAW_SIZE=7120896
readonly AA_R0_PADDED_SHA256=157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa
readonly AA_R0_DERIVED_INSTALLER_SHA256=c920eca1207dfe1362f947a74935a50fd934574f7becae4d056b09f362d46196
readonly AA_R0_DERIVER_SHA256=acbd27b3cf782ce7930059b4c91e00b113399a503fb84e9296a06b6199f65d1a
readonly AA_R1_REVISION_DERIVER_SHA256=cd3676188f4d77fcff3321bdf046c46999e1859ba91903a08e6781928e983fb9
readonly Z_DERIVED_INSTALLER_SHA256=38b5956e3f5146bc2c8e8ddc3cec9cfb8be25bd3661949b5bd8fb5dbdba51b76
readonly Z_DERIVER_SHA256=7bd871c8b068a3330996d145a1979c076d79db032e7b0efe97d868a00664f51a
readonly Y_DERIVED_INSTALLER_SHA256=923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67
readonly Y_WRAPPER_SHA256=1a33de1f640650164155ed20555b162a2b9455d2495e46a3065589b2d1759268
readonly Y_DERIVER_SHA256=ac343dc456f90098fbe28062148aa2f79d1b27b436ce7065a71e8a56c13f24e7
readonly X_INSTALLER_SHA256=2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

# This gate precedes script-directory resolution, repository inspection, SSH,
# sudo, device discovery, backup creation, and every hardware write.
for name in \
	AA_R1_RAW_SHA256 \
	AA_R1_RAW_SIZE \
	AA_R1_PADDED_SHA256 \
	AA_R1_DERIVED_INSTALLER_SHA256; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in \
	AA_R1_RAW_SHA256 \
	AA_R1_PADDED_SHA256 \
	AA_R1_DERIVED_INSTALLER_SHA256 \
	EXPECTED_CURRENT_AA_R0_PADDED_SHA256 \
	AA_R0_RAW_SHA256 \
	AA_R0_PADDED_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$AA_R1_RAW_SIZE" =~ ^[1-9][0-9]*$ && "$AA_R1_RAW_SIZE" -le 16777216 ]] || \
	die 'invalid or oversized calibrated AA_R1_RAW_SIZE'
if [[ "$AA_R1_RAW_SHA256" == "$AA_R0_RAW_SHA256" || \
	"$AA_R1_PADDED_SHA256" == "$EXPECTED_CURRENT_AA_R0_PADDED_SHA256" ]]; then
	die 'Candidate AA r1 identity unexpectedly equals installed AA r0 predecessor'
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
y_experiment="$repo_root/experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic"
z_experiment="$repo_root/experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic"
x_installer="$repo_root/experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/install-candidate-x-boot2.sh"
y_wrapper="$y_experiment/scripts/install-candidate-y-boot2.sh"
y_deriver="$y_experiment/scripts/derive-installer.py"
z_deriver="$z_experiment/scripts/derive-installer.py"
aa_r0_deriver="$script_dir/derive-installer.py"
aa_r1_revision_deriver="$script_dir/derive-revision-installer.py"
for input in \
	"$x_installer" \
	"$y_wrapper" \
	"$y_deriver" \
	"$z_deriver" \
	"$aa_r0_deriver" \
	"$aa_r1_revision_deriver"; do
	[[ -f "$input" && ! -L "$input" ]] || \
		die "installer foundation missing or unsafe: $input"
done
for command in awk bash mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
for check in \
	"$x_installer:$X_INSTALLER_SHA256" \
	"$y_wrapper:$Y_WRAPPER_SHA256" \
	"$y_deriver:$Y_DERIVER_SHA256" \
	"$z_deriver:$Z_DERIVER_SHA256" \
	"$aa_r0_deriver:$AA_R0_DERIVER_SHA256" \
	"$aa_r1_revision_deriver:$AA_R1_REVISION_DERIVER_SHA256"; do
	path=${check%%:*}
	expected=${check##*:}
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || \
		die "hash-pinned installer foundation changed: $path"
done

workdir="$(mktemp -d /tmp/candidate-aa-r1-installer.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

derived_y="$workdir/install-candidate-y-boot2.sh"
python3 "$y_deriver" --source "$x_installer" --output "$derived_y" \
	--raw-sha256 94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee \
	--raw-size 6866944 \
	--padded-sha256 dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17
[[ "$(sha256sum "$derived_y" | awk '{print $1}')" == \
	"$Y_DERIVED_INSTALLER_SHA256" ]] || die 'reconstructed Candidate Y installer changed'

derived_z="$workdir/install-candidate-z-boot2.sh"
python3 "$z_deriver" --source "$derived_y" --output "$derived_z" \
	--raw-sha256 985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9 \
	--raw-size 6866944 \
	--padded-sha256 ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40
[[ "$(sha256sum "$derived_z" | awk '{print $1}')" == \
	"$Z_DERIVED_INSTALLER_SHA256" ]] || die 'reconstructed Candidate Z installer changed'

derived_aa_r0="$workdir/install-candidate-aa-r0-boot2.sh"
python3 "$aa_r0_deriver" --source "$derived_z" --output "$derived_aa_r0" \
	--raw-sha256 "$AA_R0_RAW_SHA256" --raw-size "$AA_R0_RAW_SIZE" \
	--padded-sha256 "$AA_R0_PADDED_SHA256"
[[ "$(sha256sum "$derived_aa_r0" | awk '{print $1}')" == \
	"$AA_R0_DERIVED_INSTALLER_SHA256" ]] || \
	die 'reconstructed Candidate AA r0 installer changed'

adapted="$workdir/install-candidate-aa-r1-boot2.sh"
python3 "$aa_r1_revision_deriver" \
	--source "$derived_aa_r0" --output "$adapted" \
	--raw-sha256 "$AA_R1_RAW_SHA256" --raw-size "$AA_R1_RAW_SIZE" \
	--padded-sha256 "$AA_R1_PADDED_SHA256"
bash -n "$adapted" || die 'derived Candidate AA r1 installer failed syntax validation'
[[ "$(sha256sum "$adapted" | awk '{print $1}')" == \
	"$AA_R1_DERIVED_INSTALLER_SHA256" ]] || \
	die 'derived Candidate AA r1 installer changed'

export GEMINI_REPO_ROOT="$repo_root"
set +e
"$adapted" "$@"
status=$?
set -e
exit "$status"
