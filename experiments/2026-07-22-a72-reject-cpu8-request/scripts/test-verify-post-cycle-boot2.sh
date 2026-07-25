#!/usr/bin/env bash

# Exercise the post-cycle verifier with a synthetic finalized recovery bundle
# and a fully mocked SSH transport. No block device or network is accessed.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
verifier="$script_dir/verify-post-cycle-boot2.sh"
private_root="$repo_root/artifacts/device-pstore"
control="$(mktemp -d /tmp/candidate-aj-post-cycle-verifier.XXXXXX)"
fake_bin="$control/bin"
evidence="$private_root/aj-post-cycle-input-selftest-$$-$RANDOM"
output_prefix="$private_root/aj-post-cycle-output-selftest-$$-$RANDOM"
mkdir -m 0700 "$fake_bin"

cleanup() {
	if [[ -d "$evidence" && ! -L "$evidence" && "$(dirname -- "$evidence")" == "$private_root" && "$(basename -- "$evidence")" == aj-post-cycle-input-selftest-$$-* ]]; then rm -rf -- "$evidence"; fi
	local file
	for file in "$output_prefix"-*.txt; do
		if [[ -f "$file" && ! -L "$file" && "$(dirname -- "$file")" == "$private_root" && "$(basename -- "$file")" == aj-post-cycle-output-selftest-$$-* ]]; then rm -- "$file"; fi
	done
	[[ ! -d "$control" ]] || rm -rf -- "$control"
}
trap cleanup EXIT

python3 - "$script_dir" "$evidence" <<'PY'
import importlib.util
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
def load(name, module_name):
    path = root / name
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
validator = load("validate-recovery-evidence.py", "aj_post_cycle_test_validator")
tests = load("test-recovery-evidence.py", "aj_post_cycle_test_fixture")
runtime_tests = load("test-runtime-validator.py", "aj_post_cycle_runtime_fixture")
native_tests = load("test-native-reboot-validator.py", "aj_post_cycle_native_fixture")
destination = pathlib.Path(sys.argv[2])
tests.make(destination, validator, runtime_tests, native_tests, runtime_status="absent")
tests.finalize(validator, destination)
validator.validate_evidence(destination, validator.AJ.PADDED_SHA256)
PY
final_boot_sha="$(awk -F= '$1 == "final_boot_id_sha256" { print $2; count++ } END { exit count != 1 }' "$evidence/cycle.env")"
installed=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$AJ_VERIFY_SSH_LOG"
arguments=" $* "
for required in '-o BatchMode=yes' '-o IdentitiesOnly=yes' '-o IdentityAgent=none' '-o StrictHostKeyChecking=yes' "-i $AJ_VERIFY_IDENTITY" 'gemini@192.168.1.50'; do
	case "$arguments" in *" $required "*) ;; *) exit 91 ;; esac
done
cat >"$AJ_VERIFY_REMOTE_STREAM"
case "$AJ_VERIFY_MODE" in
duplicate-label) printf 'duplicate boot2 label rejected\n' >&2; exit 31 ;;
probe-error) printf 'read-only inactivity probe failed\n' >&2; exit 36 ;;
esac
kernel=3.18.41+
root=/dev/mmcblk0p29
boot_sha=$AJ_VERIFY_FINAL_BOOT_SHA
label=boot2
size=16777216
ro=0
mounted=no
full_sha=$AJ_VERIFY_INSTALLED
case "$AJ_VERIFY_MODE" in
wrong-kernel) kernel=3.18.40 ;;
wrong-root) root=/dev/mmcblk0p30 ;;
wrong-boot-id) boot_sha=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc ;;
wrong-label) label=boot3 ;;
wrong-size) size=8388608 ;;
wrong-ro) ro=1 ;;
mounted) mounted=yes ;;
wrong-hash) full_sha=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd ;;
success) ;;
*) exit 92 ;;
esac
printf '__AJ_POST_CYCLE_BOOT2_BEGIN__\n'
printf 'kernel=%s\narchitecture=aarch64\nroot_source=%s\n' "$kernel" "$root"
printf 'boot_id_sha256=%s\n' "$boot_sha"
printf 'boot2_path=/dev/mmcblk0p18\nboot2_kname=mmcblk0p18\nboot2_partlabel=%s\n' "$label"
printf 'boot2_type=part\nboot2_parent=mmcblk0\nboot2_size=%s\nboot2_read_only_flag=%s\n' "$size" "$ro"
printf 'boot2_mountpoint=absent\nboot2_major_minor=179:18\nby_partlabel_path=/dev/mmcblk0p18\n'
printf 'root_conflict=no\nmounted=%s\nswap=no\nholders=none\n' "$mounted"
printf 'full_partition_sha256=%s\nexpected_full_partition_sha256=%s\n' "$full_sha" "$AJ_VERIFY_INSTALLED"
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
printf 'boot_id_after_sha256=%s\n__AJ_POST_CYCLE_BOOT2_END__\n' "$boot_sha"
EOF
chmod 0700 "$fake_bin"/*

export AJ_VERIFY_SSH_LOG="$control/ssh.log"
export AJ_VERIFY_REMOTE_STREAM="$control/remote-stream"
export AJ_VERIFY_IDENTITY="$repo_root/artifacts/credentials/gemini_ed25519"
export AJ_VERIFY_FINAL_BOOT_SHA="$final_boot_sha"
export AJ_VERIFY_INSTALLED="$installed"

run_case() {
	local mode=$1 expected_rc=$2
	local output="$output_prefix-$mode.txt"
	export AJ_VERIFY_MODE=$mode
	set +e
	PATH="$fake_bin:$PATH" bash "$verifier" --recovery-evidence "$evidence" \
		--output "$output" --expected-installed-full-sha256 "$installed" \
		>"$control/$mode.stdout" 2>"$control/$mode.stderr"
	local rc=$?
	set -e
	[[ "$rc" == "$expected_rc" ]] || { cat "$control/$mode.stderr" >&2; die "$mode exit was $rc, expected $expected_rc"; }
	[[ -f "$output" && ! -L "$output" ]] || die "$mode mismatch evidence was not preserved"
}

run_case success 0
for mode in duplicate-label probe-error wrong-kernel wrong-root wrong-boot-id wrong-label wrong-size wrong-ro mounted wrong-hash; do
	run_case "$mode" 2
done

# The next assertions deliberately match literal remote-shell substitutions.
# shellcheck disable=SC2016
grep -Fq 'targets=$(lsblk -nrpo PATH,PARTLABEL' "$AJ_VERIFY_REMOTE_STREAM" || die 'live-GPT label enumeration disappeared'
# shellcheck disable=SC2016
grep -Fq 'test "$(printf' "$AJ_VERIFY_REMOTE_STREAM" || die 'unique boot2 label cardinality check disappeared'
# shellcheck disable=SC2016
grep -Fq 'full_sha256=$(sha256sum "$target"' "$AJ_VERIFY_REMOTE_STREAM" || die 'one full read-only boot2 checksum disappeared'
# shellcheck disable=SC2016
grep -Fq 'test "$target" != /dev/mmcblk0p29' "$AJ_VERIFY_REMOTE_STREAM" || die 'root exclusion disappeared'
# shellcheck disable=SC2016
grep -Fq 'mount_inventory=$(findmnt -rn -o SOURCE,MAJ:MIN) || exit 36' "$AJ_VERIFY_REMOTE_STREAM" || die 'fail-closed mount inventory disappeared'
grep -Fq '/proc/swaps' "$AJ_VERIFY_REMOTE_STREAM" || die 'swap exclusion disappeared'
grep -Fq "swap_inventory=\$(awk 'NR > 1 { print \$1 }' /proc/swaps) || exit 38" "$AJ_VERIFY_REMOTE_STREAM" || die 'fail-closed swap inventory disappeared'
# shellcheck disable=SC2016
grep -Fq 'holder=$(find "/sys/class/block/$kname/holders" -mindepth 1 -maxdepth 1 -print -quit) || exit 39' "$AJ_VERIFY_REMOTE_STREAM" || die 'fail-closed holder probe disappeared'
# shellcheck disable=SC2016
if grep -Eq '(^|[[:space:]])(dd|tee|blkdiscard|mkfs|mount|umount)([[:space:]]|$)|>[[:space:]]*"?\$target|/dev/watchdog|reboot|shutdown|poweroff' "$AJ_VERIFY_REMOTE_STREAM"; then
	die 'post-cycle remote stream gained a write or reboot primitive'
fi
if grep -q 'install-candidate\|derive-installer' "$AJ_VERIFY_REMOTE_STREAM"; then
	die 'post-cycle verifier reused an installer path'
fi

printf 'validation=candidate-aj-post-cycle-boot2-mocked\n'
printf 'success_exact_hash=passed\n'
printf 'duplicate_label_wrong_identity_geometry_use_hash=rejected\n'
printf 'read_only_probe_error=rejected\n'
printf 'mismatch_evidence_preserved=yes\ntransport=mocked\n'
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\ndevice_access=none\n'
