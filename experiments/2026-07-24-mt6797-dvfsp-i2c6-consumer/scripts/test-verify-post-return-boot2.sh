#!/usr/bin/env bash

# Exercise a source-calibrated AP post-return verifier with mocked SSH/storage,
# and prove the checked-in unresolved verifier never reaches SSH.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
verifier="$script_dir/verify-post-return-boot2.sh"
control="$(mktemp -d /tmp/candidate-ap-post-return.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
mirror="$control/repo"
mirror_scripts="$mirror/experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts"
runtime_root="$mirror/artifacts/runtime-captures"
capture_dir="$runtime_root/candidate-ap-runtime-selftest"
evidence_root="$mirror/artifacts/device-pstore"
credentials="$mirror/artifacts/credentials"
fake_bin="$control/bin"
padded=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9
boot_id=01234567-89ab-4def-8123-456789abcdef
returned=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb

cleanup() { [[ ! -d "$control" ]] || rm -rf -- "$control"; }
trap cleanup EXIT
mkdir -p "$mirror_scripts" "$capture_dir" "$evidence_root" "$credentials" \
	"$fake_bin"
chmod 0700 "$mirror/artifacts" "$runtime_root" "$capture_dir" \
	"$evidence_root" "$credentials" "$mirror_scripts" "$fake_bin"

cp "$verifier" "$mirror_scripts/verify-post-return-boot2.sh"
cat >"$mirror_scripts/candidate_ap.py" <<'PY'
PADDED_SHA256 = "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
AO_PADDED_SHA256 = "2222222222222222222222222222222222222222222222222222222222222222"
def require_artifact_pins():
    return None
PY
cat >"$mirror_scripts/validate-native-reboot.py" <<'PY'
#!/usr/bin/env python3
import sys
required = {
    "--capture",
    "--runtime-capture",
    "--expected-installed-full-sha256",
    "--expected-runtime-outcome",
}
if not required <= set(sys.argv):
    raise SystemExit(2)
print("validation=candidate-ap-native-reboot-request")
print("candidate_boot_id=01234567-89ab-4def-8123-456789abcdef")
print("runtime_capture_sha256=fixture")
PY
printf 'exact mocked AP runtime evidence\n' >"$capture_dir/runtime.txt"
printf 'exact mocked AP native reboot evidence\n' >"$capture_dir/native-reboot.txt"
printf 'mock private key\n' >"$credentials/gemini_ed25519"
chmod 0600 "$capture_dir/runtime.txt" "$capture_dir/native-reboot.txt" \
	"$credentials/gemini_ed25519"

candidate_source_sha="$(
	shasum -a 256 "$mirror_scripts/candidate_ap.py" | awk '{ print $1 }'
)"
runtime_sha="$(
	shasum -a 256 "$capture_dir/runtime.txt" | awk '{ print $1 }'
)"
native_sha="$(
	shasum -a 256 "$capture_dir/native-reboot.txt" | awk '{ print $1 }'
)"
native_validator_sha="$(
	shasum -a 256 "$mirror_scripts/validate-native-reboot.py" | awk '{ print $1 }'
)"
candidate_boot_sha="$(
	printf '%s\n' "$boot_id" | shasum -a 256 | awk '{ print $1 }'
)"
python3 - "$mirror_scripts/verify-post-return-boot2.sh" \
	"$candidate_source_sha" "$runtime_sha" "$native_sha" \
	"$native_validator_sha" "$candidate_boot_sha" "$returned" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
assignments = (
    ("CANDIDATE_AP_SHA256", sys.argv[2]),
    ("RUNTIME_SHA256", sys.argv[3]),
    ("NATIVE_SHA256", sys.argv[4]),
    ("NATIVE_VALIDATOR_SHA256", sys.argv[5]),
    ("CANDIDATE_BOOT_ID_SHA256", sys.argv[6]),
    ("RETURNED_GEMIAN_BOOT_ID_SHA256", sys.argv[7]),
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
printf '%s\n' "$*" >>"$AP_POST_SSH_LOG"
arguments=" $* "
for required in '-o BatchMode=yes' '-o LogLevel=ERROR' \
	'-o WarnWeakCrypto=no' '-o IdentitiesOnly=yes' \
	'-o IdentityAgent=none' '-o StrictHostKeyChecking=yes' \
	"-i $AP_POST_IDENTITY" 'gemini@192.168.1.50'; do
	case "$arguments" in
	*" $required "*) ;;
	*) exit 91 ;;
	esac
done
cat >"$AP_POST_REMOTE_STREAM"

kernel=3.18.41+
architecture=aarch64
root=/dev/mmcblk0p29
boot_sha=$AP_POST_RETURNED
after_sha=$boot_sha
mounted=no
full_sha=$AP_POST_INSTALLED
case "$AP_POST_MODE" in
success) ;;
wrong-kernel) kernel=3.18.40 ;;
wrong-root) root=/dev/mmcblk0p30 ;;
wrong-boot-id)
	boot_sha=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
	;;
mounted) mounted=yes ;;
wrong-hash)
	full_sha=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
	;;
boot-changed)
	after_sha=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
	;;
*) exit 92 ;;
esac
printf '__AP_LIVE_BOOT2_BEGIN__\n'
printf 'kernel=%s\narchitecture=%s\nroot_source=%s\n' \
	"$kernel" "$architecture" "$root"
printf 'live_boot_id_sha256=%s\n' "$boot_sha"
printf 'boot2_path=/dev/mmcblk0p30\nboot2_kname=mmcblk0p30\n'
printf 'boot2_partlabel=boot2\nboot2_type=part\nboot2_parent=mmcblk0\n'
printf 'boot2_size=16777216\nboot2_read_only_flag=0\n'
printf 'boot2_mountpoint=absent\nboot2_major_minor=179:30\n'
printf 'by_partlabel_path=/dev/mmcblk0p30\n'
printf 'root_conflict=no\nmounted=%s\nswap=no\nholders=none\n' "$mounted"
printf 'full_partition_sha256=%s\n' "$full_sha"
printf 'expected_full_partition_sha256=%s\n' "$AP_POST_INSTALLED"
printf 'device_partition_reads=one-full-boot2-read-only\n'
printf 'device_write_operations=none\n'
printf 'live_boot_id_after_sha256=%s\n' "$after_sha"
printf '__AP_LIVE_BOOT2_END__\n'
EOF
chmod 0700 "$fake_bin"/*

export AP_POST_SSH_LOG="$control/ssh.log"
export AP_POST_REMOTE_STREAM="$control/remote-stream"
export AP_POST_IDENTITY="$credentials/gemini_ed25519"
export AP_POST_INSTALLED=$padded
export AP_POST_RETURNED=$returned

# The checked-in verifier must refuse before it inspects evidence or reaches
# the mocked SSH transport.
set +e
PATH="$fake_bin:$PATH" bash "$verifier" \
	--runtime-capture "$control/nonexistent/runtime.txt" \
	--native-reboot-capture "$control/nonexistent/native-reboot.txt" \
	--output "$control/nonexistent/post-return.txt" \
	--expected-installed-full-sha256 "$padded" \
	--expected-runtime-outcome PASS \
	>"$control/unresolved.stdout" 2>"$control/unresolved.stderr"
unresolved_rc=$?
set -e
((unresolved_rc == 2)) || \
	die "unresolved production exit was $unresolved_rc"
if grep -q 'TO_PIN_AFTER_' "$verifier"; then
	grep -q 'post-return production pins remain unresolved' \
		"$control/unresolved.stderr" || \
		die 'unresolved production refusal changed'
	production_pins=unresolved
else
	grep -Eq \
		'runtime capture is not one Candidate AP private child|runtime capture directory is unsafe|evidence is absent or unsafe' \
		"$control/unresolved.stderr" || \
		die 'calibrated production evidence refusal changed'
	production_pins=calibrated
fi
[[ ! -e "$AP_POST_SSH_LOG" ]] || \
	die 'unresolved production verifier reached SSH'

output_prefix="$evidence_root/candidate-ap-post-return-selftest"
run_case() {
	local mode=$1 expected_rc=$2 output
	output="$output_prefix-$mode.txt"
	export AP_POST_MODE=$mode
	set +e
	PATH="$fake_bin:$PATH" \
		bash "$mirror_scripts/verify-post-return-boot2.sh" \
			--runtime-capture "$capture_dir/runtime.txt" \
			--native-reboot-capture "$capture_dir/native-reboot.txt" \
			--output "$output" \
			--expected-installed-full-sha256 "$padded" \
			--expected-runtime-outcome PASS \
			>"$control/$mode.stdout" 2>"$control/$mode.stderr"
	local rc=$?
	set -e
	[[ "$rc" == "$expected_rc" ]] || {
		cat "$control/$mode.stderr" >&2
		die "$mode exit was $rc, expected $expected_rc"
	}
	[[ -f "$output" && ! -L "$output" ]] || \
		die "$mode evidence was not preserved"
	[[ "$(
		stat -f '%Lp' "$output" 2>/dev/null || stat -c '%a' "$output"
	)" == 600 ]] || die "$mode evidence mode changed"
}

run_case success 0
for mode in wrong-kernel wrong-root wrong-boot-id mounted wrong-hash \
	boot-changed; do
	run_case "$mode" 2
done
grep -q '^validation=candidate-ap-post-return-boot2-integrity$' \
	"$control/success.stdout" || \
	die 'calibrated success validation label changed'
[[ "$(wc -l <"$AP_POST_SSH_LOG" | tr -d ' ')" == 7 ]] || \
	die 'mocked SSH invocation count changed'

# Audit the actual remote program transported by the verifier.
grep -Fq 'rows=$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT' \
	"$AP_POST_REMOTE_STREAM" || \
	die 'live-GPT boot2 resolution disappeared'
grep -Fq '/proc/self/mountinfo' "$AP_POST_REMOTE_STREAM" || \
	die 'mount-use gate disappeared'
grep -Fq 'swapon --noheadings --raw --show=NAME' \
	"$AP_POST_REMOTE_STREAM" || die 'swap-use gate disappeared'
grep -Fq '/sys/class/block/$kname/holders' "$AP_POST_REMOTE_STREAM" || \
	die 'holder exclusion disappeared'
# The literal remote-shell variable is the contract.
# shellcheck disable=SC2016
[[ "$(grep -Fc 'full_sha256=$(sha256sum "$target"' \
	"$AP_POST_REMOTE_STREAM")" == 1 ]] || \
	die 'exactly one full boot2 partition read is no longer encoded'
if grep -Eq \
	'(^|[[:space:]])(dd|tee|blkdiscard|mkfs|mount|umount|sync|reboot|shutdown|poweroff)([[:space:]]|$)|/dev/watchdog|>[[:space:]]*"?\$target' \
	"$AP_POST_REMOTE_STREAM"; then
	die 'remote verifier gained a write or reboot primitive'
fi

printf 'validation=candidate-ap-post-return-boot2-mocked\n'
printf 'production_pins=%s\n' "$production_pins"
printf 'unresolved_production_reached_ssh=no\n'
printf 'changed_gemian_boot_and_live_gpt_binding=passed\n'
printf 'identity_mount_hash_and_boot_stability_mismatches=rejected\n'
printf 'transport=mocked\n'
printf 'device_partition_reads=one-full-boot2-read-only\n'
printf 'device_write_operations=none\n'
printf 'device_access=none\n'
