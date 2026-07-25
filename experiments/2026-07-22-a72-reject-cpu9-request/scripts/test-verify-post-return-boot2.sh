#!/usr/bin/env bash

# Run a calibrated temporary verifier with deterministic mocked SSH/storage,
# and prove the unresolved production verifier never reaches SSH.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
verifier="$script_dir/verify-post-return-boot2.sh"
control="$(mktemp -d /tmp/candidate-ak-post-return.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
mirror="$control/repo"
mirror_scripts="$mirror/experiments/2026-07-22-a72-reject-cpu9-request/scripts"
runtime_root="$mirror/artifacts/runtime-captures"
capture_dir="$runtime_root/candidate-ak-runtime-selftest"
pstore_root="$mirror/artifacts/device-pstore"
credentials="$mirror/artifacts/credentials"
fake_bin="$control/bin"
padded=1111111111111111111111111111111111111111111111111111111111111111
returned=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
boot_id=01234567-89ab-cdef-0123-456789abcdef

cleanup() { [[ ! -d "$control" ]] || rm -rf -- "$control"; }
trap cleanup EXIT
mkdir -p "$mirror_scripts" "$capture_dir" "$pstore_root" "$credentials" "$fake_bin"
chmod 0700 "$mirror_scripts" "$capture_dir" "$pstore_root" "$credentials" "$fake_bin"
chmod 0700 "$mirror/artifacts" "$runtime_root"

cp "$verifier" "$mirror_scripts/verify-post-return-boot2.sh"
cat >"$mirror_scripts/candidate_ak.py" <<'PY'
PADDED_SHA256 = "1111111111111111111111111111111111111111111111111111111111111111"
AJ_PADDED_SHA256 = "2222222222222222222222222222222222222222222222222222222222222222"
def require_artifact_pins():
    return None
PY
cat >"$mirror_scripts/validate-native-reboot.py" <<'PY'
#!/usr/bin/env python3
import sys
required = {"--capture", "--runtime-capture", "--expected-installed-full-sha256"}
if not required <= set(sys.argv):
    raise SystemExit(2)
print("validation=candidate-ak-native-reboot-request")
PY
cat >"$capture_dir/runtime.txt" <<EOF
__AK_HOST_BEGIN__
interface=en7
__AK_HOST_END__
boot_id=$boot_id
EOF
printf 'exact mocked AK native reboot evidence\n' >"$capture_dir/native-reboot.txt"
printf 'mock private key\n' >"$credentials/gemini_ed25519"
chmod 0600 "$capture_dir/runtime.txt" "$capture_dir/native-reboot.txt" "$credentials/gemini_ed25519"

candidate_source_sha="$(shasum -a 256 "$mirror_scripts/candidate_ak.py" | awk '{ print $1 }')"
runtime_sha="$(shasum -a 256 "$capture_dir/runtime.txt" | awk '{ print $1 }')"
native_sha="$(shasum -a 256 "$capture_dir/native-reboot.txt" | awk '{ print $1 }')"
native_validator_sha="$(shasum -a 256 "$mirror_scripts/validate-native-reboot.py" | awk '{ print $1 }')"
candidate_boot_sha="$(printf '%s\n' "$boot_id" | shasum -a 256 | awk '{ print $1 }')"
python3 - "$mirror_scripts/verify-post-return-boot2.sh" \
	"$padded" "$candidate_source_sha" "$runtime_sha" "$native_sha" \
	"$native_validator_sha" "$candidate_boot_sha" "$returned" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
values = sys.argv[2:]
assignments = (
    ("AK_PADDED_SHA256", values[0]),
    ("CANDIDATE_AK_SHA256", values[1]),
    ("RUNTIME_SHA256", values[2]),
    ("NATIVE_SHA256", values[3]),
    ("NATIVE_VALIDATOR_SHA256", values[4]),
    ("CANDIDATE_BOOT_ID_SHA256", values[5]),
    ("RETURNED_GEMIAN_BOOT_ID_SHA256", values[6]),
)
for name, value in assignments:
    pattern = rf"(?m)^readonly {name}=\S+$"
    text, count = re.subn(pattern, f"readonly {name}={value}", text)
    if count != 1:
        raise RuntimeError(f"unexpected verifier assignment count: {name}")
path.write_text(text)
PY

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$AK_POST_SSH_LOG"
arguments=" $* "
for required in '-o BatchMode=yes' '-o LogLevel=ERROR' '-o WarnWeakCrypto=no' '-o IdentitiesOnly=yes' '-o IdentityAgent=none' '-o StrictHostKeyChecking=yes' "-i $AK_POST_IDENTITY" 'gemini@192.168.1.50'; do
	case "$arguments" in *" $required "*) ;; *) exit 91 ;; esac
done
cat >"$AK_POST_REMOTE_STREAM"
case "$AK_POST_MODE" in
duplicate-label) printf 'duplicate boot2 label rejected\n' >&2; exit 31 ;;
probe-error) printf 'read-only use probe failed\n' >&2; exit 36 ;;
esac
kernel=3.18.41+
arch=aarch64
root=/dev/mmcblk0p29
boot_sha=$AK_POST_RETURNED
label=boot2
type=part
parent=mmcblk0
size=16777216
ro=0
mounted=no
swap=no
holders=none
full_sha=$AK_POST_INSTALLED
after_sha=$boot_sha
case "$AK_POST_MODE" in
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
printf '__AK_LIVE_BOOT2_BEGIN__\n'
printf 'kernel=%s\narchitecture=%s\nroot_source=%s\n' "$kernel" "$arch" "$root"
printf 'live_boot_id_sha256=%s\n' "$boot_sha"
printf 'boot2_path=/dev/mmcblk0p30\nboot2_kname=mmcblk0p30\nboot2_partlabel=%s\nboot2_type=%s\nboot2_parent=%s\n' "$label" "$type" "$parent"
printf 'boot2_size=%s\nboot2_read_only_flag=%s\nboot2_mountpoint=absent\nboot2_major_minor=179:30\n' "$size" "$ro"
printf 'by_partlabel_path=/dev/mmcblk0p30\nroot_conflict=no\nmounted=%s\nswap=%s\nholders=%s\n' "$mounted" "$swap" "$holders"
printf 'full_partition_sha256=%s\nexpected_full_partition_sha256=%s\n' "$full_sha" "$AK_POST_INSTALLED"
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
printf 'live_boot_id_after_sha256=%s\n__AK_LIVE_BOOT2_END__\n' "$after_sha"
EOF
chmod 0700 "$fake_bin"/*

export AK_POST_SSH_LOG="$control/ssh.log"
export AK_POST_REMOTE_STREAM="$control/remote-stream"
export AK_POST_IDENTITY="$credentials/gemini_ed25519"
export AK_POST_INSTALLED=$padded
export AK_POST_RETURNED=$returned

# The checked-in verifier must reject this synthetic identity before SSH.
# Today that is the unresolved-pin gate; after calibration it becomes an exact
# evidence/identity mismatch.
set +e
PATH="$fake_bin:$PATH" bash "$verifier" \
	--runtime-capture "$capture_dir/runtime.txt" \
	--native-reboot-capture "$capture_dir/native-reboot.txt" \
	--output "$pstore_root/candidate-ak-post-return-unresolved.txt" \
	--expected-installed-full-sha256 "$padded" \
	>"$control/unresolved.stdout" 2>"$control/unresolved.stderr"
unresolved_rc=$?
set -e
((unresolved_rc == 2)) || die "unresolved production exit was $unresolved_rc"
if grep -q 'TO_PIN_AFTER_' "$verifier"; then
	grep -q 'production pins remain unresolved' "$control/unresolved.stderr" || die 'unresolved pin refusal changed'
	production_pins=unresolved
else
	grep -Eq 'expected checksum is not Candidate AK|runtime capture identity changed|production artifact pins are unresolved or invalid' "$control/unresolved.stderr" || die 'calibrated evidence refusal changed'
	production_pins=calibrated
fi
[[ ! -e "$AK_POST_SSH_LOG" ]] || die 'unresolved production verifier reached SSH'

output_prefix="$pstore_root/candidate-ak-post-return-selftest"
run_case() {
	local mode=$1 expected_rc=$2 output
	output="$output_prefix-$mode.txt"
	export AK_POST_MODE=$mode
	set +e
	PATH="$fake_bin:$PATH" bash "$mirror_scripts/verify-post-return-boot2.sh" \
		--runtime-capture "$capture_dir/runtime.txt" \
		--native-reboot-capture "$capture_dir/native-reboot.txt" \
		--output "$output" --expected-installed-full-sha256 "$padded" \
		>"$control/$mode.stdout" 2>"$control/$mode.stderr"
	local rc=$?
	set -e
	[[ "$rc" == "$expected_rc" ]] || {
		cat "$control/$mode.stderr" >&2
		die "$mode exit was $rc, expected $expected_rc"
	}
	[[ -f "$output" && ! -L "$output" ]] || die "$mode evidence was not preserved"
}

run_case success 0
for mode in duplicate-label probe-error wrong-kernel wrong-arch wrong-root wrong-boot-id wrong-label wrong-type wrong-parent wrong-size wrong-ro mounted swap holders wrong-hash boot-changed; do
	run_case "$mode" 2
done

[[ "$(wc -l <"$AK_POST_SSH_LOG" | tr -d ' ')" == 17 ]] || die 'mocked transport invocation count changed'
# shellcheck disable=SC2016
grep -Fq 'rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT' "$AK_POST_REMOTE_STREAM" || die 'Gemian-compatible live-GPT resolution disappeared'
if grep -Eq 'lsblk.*[ ,]PATH([ ,]|$)' "$AK_POST_REMOTE_STREAM"; then
	die 'unsupported lsblk PATH column returned'
fi
grep -Fq '/proc/self/mountinfo' "$AK_POST_REMOTE_STREAM" || die 'Gemian-compatible mount-use gate disappeared'
grep -Fq 'swapon --noheadings --raw --show=NAME' "$AK_POST_REMOTE_STREAM" || die 'Gemian-compatible swap-use gate disappeared'
if grep -Fq '/proc/swaps' "$AK_POST_REMOTE_STREAM"; then
	die 'unproven procfs swap gate returned'
fi
# The literal remote-shell variable is the contract.
# shellcheck disable=SC2016
grep -Fq '/sys/class/block/$kname/ro' "$AK_POST_REMOTE_STREAM" || die 'sysfs read-only gate disappeared'
# shellcheck disable=SC2016
[[ "$(grep -Fc 'full_sha256=$(sha256sum "$target"' "$AK_POST_REMOTE_STREAM")" == 1 ]] || die 'exactly one full partition read is no longer encoded'
grep -Fq '/holders' "$AK_POST_REMOTE_STREAM" || die 'holder exclusion disappeared'
# The literal remote-shell variable is the contract.
# shellcheck disable=SC2016
if grep -Eq '(^|[[:space:]])(dd|tee|blkdiscard|mkfs|mount|umount|sync|reboot|shutdown|poweroff)([[:space:]]|$)|/dev/watchdog|>[[:space:]]*"?\$target' "$AK_POST_REMOTE_STREAM"; then
	die 'remote verifier gained a write or reboot primitive'
fi

printf 'validation=candidate-ak-post-return-boot2-mocked\n'
printf 'production_pins=%s\nsynthetic_evidence_reached_ssh=no\n' "$production_pins"
printf 'identity_geometry_use_hash_and_boot_stability_mismatches=rejected\n'
printf 'live_gpt_resolution=NAME-column\nmount_gate=mountinfo\nswap_gate=swapon\n'
printf 'transport=mocked\ndevice_access=none\n'
printf 'device_partition_reads=one-full-boot2-read-only\ndevice_write_operations=none\n'
