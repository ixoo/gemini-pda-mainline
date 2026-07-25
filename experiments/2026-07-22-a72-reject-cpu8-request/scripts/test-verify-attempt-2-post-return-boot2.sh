#!/usr/bin/env bash

# Run the exact attempt-2 evidence validators, but replace SSH/storage with a
# deterministic transcript producer. No network or block device is accessed.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
verifier="$script_dir/verify-attempt-2-post-return-boot2.sh"
runtime="$repo_root/artifacts/runtime-captures/candidate-aj-hardware-attempt-2-live-20260722/runtime.txt"
native="$repo_root/artifacts/runtime-captures/candidate-aj-hardware-attempt-2-live-20260722/native-reboot.txt"
snapshot="$repo_root/artifacts/device-pstore/candidate-aj-attempt-2-post-native-20260722"
private_root="$repo_root/artifacts/device-pstore"
installed=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
returned=fc23e897afb61177e976a77265435d467bdc8917a5c7d9f7c6bc132fc04e5b7b
control="$(mktemp -d /tmp/candidate-aj-attempt2-integrity.XXXXXX)"
fake_bin="$control/bin"
output_prefix="$private_root/aj-attempt2-integrity-selftest-$$-$RANDOM"
mkdir -m 0700 "$fake_bin"

cleanup() {
	local file
	for file in "$output_prefix"-*.txt; do
		[[ ! -e "$file" ]] || rm -f -- "$file"
	done
	[[ ! -d "$control" ]] || rm -rf -- "$control"
}
trap cleanup EXIT

cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$AJ_A2_SSH_LOG"
arguments=" $* "
for required in '-o BatchMode=yes' '-o LogLevel=ERROR' '-o WarnWeakCrypto=no' '-o IdentitiesOnly=yes' '-o IdentityAgent=none' '-o StrictHostKeyChecking=yes' "-i $AJ_A2_IDENTITY" 'gemini@192.168.1.50'; do
	case "$arguments" in *" $required "*) ;; *) exit 91 ;; esac
done
cat >"$AJ_A2_REMOTE_STREAM"
case "$AJ_A2_MODE" in
duplicate-label) printf 'duplicate boot2 label rejected\n' >&2; exit 31 ;;
probe-error) printf 'read-only use probe failed\n' >&2; exit 36 ;;
esac
kernel=3.18.41+
arch=aarch64
root=/dev/mmcblk0p29
boot_sha=$AJ_A2_RETURNED
label=boot2
type=part
parent=mmcblk0
size=16777216
ro=0
mounted=no
swap=no
holders=none
full_sha=$AJ_A2_INSTALLED
after_sha=$boot_sha
case "$AJ_A2_MODE" in
wrong-kernel) kernel=3.18.40 ;;
wrong-arch) arch=armv7l ;;
wrong-root) root=/dev/mmcblk0p30 ;;
wrong-boot-id) boot_sha=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc ;;
wrong-label) label=boot3 ;;
wrong-type) type=disk ;;
wrong-parent) parent=mmcblk1 ;;
wrong-size) size=8388608 ;;
wrong-ro) ro=1 ;;
mounted) mounted=yes ;;
swap) swap=yes ;;
holders) holders=dm-0 ;;
wrong-hash) full_sha=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd ;;
boot-changed) after_sha=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee ;;
success) ;;
*) exit 92 ;;
esac
printf '__AJ_ATTEMPT2_LIVE_BOOT2_BEGIN__\n'
printf 'kernel=%s\narchitecture=%s\nroot_source=%s\n' "$kernel" "$arch" "$root"
printf 'live_boot_id_sha256=%s\n' "$boot_sha"
printf 'boot2_path=/dev/mmcblk0p30\nboot2_kname=mmcblk0p30\nboot2_partlabel=%s\nboot2_type=%s\nboot2_parent=%s\n' "$label" "$type" "$parent"
printf 'boot2_size=%s\nboot2_read_only_flag=%s\nboot2_mountpoint=absent\nboot2_major_minor=179:30\n' "$size" "$ro"
printf 'by_partlabel_path=/dev/mmcblk0p30\nroot_conflict=no\nmounted=%s\nswap=%s\nholders=%s\n' "$mounted" "$swap" "$holders"
printf 'full_partition_sha256=%s\nexpected_full_partition_sha256=%s\n' "$full_sha" "$AJ_A2_INSTALLED"
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
printf 'live_boot_id_after_sha256=%s\n__AJ_ATTEMPT2_LIVE_BOOT2_END__\n' "$after_sha"
EOF
chmod 0700 "$fake_bin/ssh"

export AJ_A2_SSH_LOG="$control/ssh.log"
export AJ_A2_REMOTE_STREAM="$control/remote-stream"
export AJ_A2_IDENTITY="$repo_root/artifacts/credentials/gemini_ed25519"
export AJ_A2_INSTALLED=$installed
export AJ_A2_RETURNED=$returned

run_case() {
	local mode=$1 expected_rc=$2 output="$output_prefix-$1.txt"
	export AJ_A2_MODE=$mode
	set +e
	PATH="$fake_bin:$PATH" bash "$verifier" --runtime-capture "$runtime" \
		--native-reboot-capture "$native" --recovery-snapshot "$snapshot" \
		--output "$output" --expected-installed-full-sha256 "$installed" \
		>"$control/$mode.stdout" 2>"$control/$mode.stderr"
	local rc=$?
	set -e
	[[ "$rc" == "$expected_rc" ]] || { cat "$control/$mode.stderr" >&2; die "$mode exit was $rc, expected $expected_rc"; }
	[[ -f "$output" && ! -L "$output" ]] || die "$mode evidence was not preserved"
}

run_case success 0
for mode in duplicate-label probe-error wrong-kernel wrong-arch wrong-root wrong-boot-id wrong-label wrong-type wrong-parent wrong-size wrong-ro mounted swap holders wrong-hash boot-changed; do
	run_case "$mode" 2
done

[[ "$(wc -l <"$AJ_A2_SSH_LOG" | tr -d ' ')" == 17 ]] || die 'mocked transport invocation count changed'
# shellcheck disable=SC2016
grep -Fq 'rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT' "$AJ_A2_REMOTE_STREAM" || die 'Gemian-compatible live-GPT resolution disappeared'
if grep -Eq 'lsblk.*[ ,]PATH([ ,]|$)' "$AJ_A2_REMOTE_STREAM"; then
	die 'unsupported lsblk PATH column returned'
fi
grep -Fq '/proc/self/mountinfo' "$AJ_A2_REMOTE_STREAM" || die 'Gemian-compatible mount-use gate disappeared'
grep -Fq 'swapon --noheadings --raw --show=NAME' "$AJ_A2_REMOTE_STREAM" || die 'Gemian-compatible swap-use gate disappeared'
if grep -Fq '/proc/swaps' "$AJ_A2_REMOTE_STREAM"; then
	die 'unproven procfs swap gate returned'
fi
grep -Fq '/sys/class/block/$kname/ro' "$AJ_A2_REMOTE_STREAM" || die 'sysfs read-only gate disappeared'
# shellcheck disable=SC2016
[[ "$(grep -Fc 'full_sha256=$(sha256sum "$target"' "$AJ_A2_REMOTE_STREAM")" == 1 ]] || die 'exactly one full partition read is no longer encoded'
grep -Fq '/holders' "$AJ_A2_REMOTE_STREAM" || die 'holder exclusion disappeared'
if grep -Eq '(^|[[:space:]])(dd|tee|blkdiscard|mkfs|mount|umount|sync|reboot|shutdown|poweroff)([[:space:]]|$)|/dev/watchdog|>[[:space:]]*"?\$target' "$AJ_A2_REMOTE_STREAM"; then
	die 'remote verifier gained a write or reboot primitive'
fi

printf 'validation=candidate-aj-attempt-2-post-return-boot2-mocked\n'
printf 'exact_runtime_native_snapshot_bindings=passed\n'
printf 'identity_geometry_use_hash_and_boot_stability_mismatches=rejected\n'
printf 'transport=mocked\ndevice_access=none\n'
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
