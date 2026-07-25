#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk basename cat chmod dirname find grep mkdir mktemp rm stat tar wc; do
	command -v "$command" >/dev/null 2>&1 || die "required test command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-recovery-evidence.sh"
private_root="$repo_root/artifacts/device-pstore"
control="$(mktemp -d /tmp/candidate-ai-recovery-collector.XXXXXX)"
fake_bin="$control/bin"
output="$private_root/ai-recovery-selftest-$$-$RANDOM"
short_output="$private_root/ai-recovery-short-wait-selftest-$$-$RANDOM"
wrong_hash_output="$private_root/ai-recovery-wrong-hash-selftest-$$-$RANDOM"
installed_sha256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
mkdir -m 0700 "$fake_bin" "$control/pre" "$control/post"

cleanup() {
	local candidate
	for candidate in "$output" "$short_output" "$wrong_hash_output"; do
		if [[ -d "$candidate" && ! -L "$candidate" && \
			"$(dirname -- "$candidate")" == "$private_root" && \
			"$(basename -- "$candidate")" == ai-recovery-*-selftest-* ]]; then
			rm -rf -- "$candidate"
		fi
	done
	[[ ! -d "$control" ]] || rm -rf -- "$control"
}
trap cleanup EXIT

[[ -f "$collector" && ! -L "$collector" ]] || die 'recovery collector is absent or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'recovery self-test output collision'
[[ ! -e "$short_output" && ! -L "$short_output" ]] || die 'short-wait output collision'
[[ ! -e "$wrong_hash_output" && ! -L "$wrong_hash_output" ]] || \
	die 'wrong-hash output collision'

printf '%s\n' \
	'GEMINI_OBSERVABILITY_20260717_L stale before cycle' \
	>"$control/pre/console-ramoops"
printf '%s\n' \
	'GEMINI_OBSERVABILITY_20260717_L stale before cycle' \
	'GEMINI_USB_GADGET_ETHERNET_20260721_AC inherited lineage only' \
	'GEMINI_MT6797_KERNEL_RESTART_20260720_AB inherited lineage only' \
	'reboot: Restarting system' \
	>"$control/post/console-ramoops"
printf 'unchanged stale pstore\n' >"$control/pre/dmesg-ramoops-0"
printf 'unchanged stale pstore\n' >"$control/post/dmesg-ramoops-0"
printf 'unchanged stale pstore\n' >"$control/post/dmesg-ramoops-1"
COPYFILE_DISABLE=1 tar -C "$control/pre" -cf "$control/pre.tar" .
COPYFILE_DISABLE=1 tar -C "$control/post" -cf "$control/post.tar" .
chmod 0600 "$control/pre.tar" "$control/post.tar"

cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${AI_TEST_SSH_LOG:?}" "${AI_TEST_STATE_COUNT:?}" "${AI_TEST_TRUE_COUNT:?}"
: "${AI_TEST_TAR_COUNT:?}" "${AI_TEST_PRE_TAR:?}" "${AI_TEST_POST_TAR:?}"
: "${AI_TEST_IDENTITY:?}" "${AI_TEST_REMOTE_STDIN:?}"

printf '%s\n' "$*" >>"$AI_TEST_SSH_LOG"
arguments=" $* "
for required in \
	'-o BatchMode=yes' \
	'-o IdentitiesOnly=yes' \
	'-o IdentityAgent=none' \
	'-o StrictHostKeyChecking=yes' \
	"-i $AI_TEST_IDENTITY" \
	'gemini@192.168.1.50'; do
	case "$arguments" in
	*" $required "*) ;;
	*) printf 'mock ssh missing exact contract: %s\n' "$required" >&2; exit 97 ;;
	esac
done
case "$arguments" in
*'StrictHostKeyChecking=accept-new'*) exit 98 ;;
esac

last=${!#}
case "$last" in
'sudo -n -- /bin/sh -s')
	cat >>"$AI_TEST_REMOTE_STDIN"
	count=0
	[[ ! -f "$AI_TEST_STATE_COUNT" ]] || read -r count <"$AI_TEST_STATE_COUNT"
	count=$((count + 1))
	printf '%s\n' "$count" >"$AI_TEST_STATE_COUNT"
	if ((count <= 2)); then
		boot_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
	else
		boot_id=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
	fi
	printf 'kernel=3.18.41+\n'
	printf 'architecture=aarch64\n'
	printf 'root_source=/dev/mmcblk0p29\n'
	printf 'boot_id=%s\n' "$boot_id"
	printf 'pstore_directory=present\n'
	;;
'sudo -n -- tar -C /sys/fs/pstore -cf - .')
	count=0
	[[ ! -f "$AI_TEST_TAR_COUNT" ]] || read -r count <"$AI_TEST_TAR_COUNT"
	count=$((count + 1))
	printf '%s\n' "$count" >"$AI_TEST_TAR_COUNT"
	case "$count" in
	1) cat "$AI_TEST_PRE_TAR" ;;
	2) cat "$AI_TEST_POST_TAR" ;;
	*) exit 96 ;;
	esac
	;;
true)
	count=0
	[[ ! -f "$AI_TEST_TRUE_COUNT" ]] || read -r count <"$AI_TEST_TRUE_COUNT"
	count=$((count + 1))
	printf '%s\n' "$count" >"$AI_TEST_TRUE_COUNT"
	exit 255
	;;
*)
	printf 'unexpected mock ssh remote command: %s\n' "$last" >&2
	exit 95
	;;
esac
EOF

cat >"$fake_bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod 0700 "$fake_bin/ssh" "$fake_bin/sleep"

ssh_log="$control/ssh.log"
state_count="$control/state.count"
true_count="$control/true.count"
tar_count="$control/tar.count"
remote_stdin="$control/remote-stdin.log"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
export AI_TEST_SSH_LOG="$ssh_log"
export AI_TEST_STATE_COUNT="$state_count"
export AI_TEST_TRUE_COUNT="$true_count"
export AI_TEST_TAR_COUNT="$tar_count"
export AI_TEST_PRE_TAR="$control/pre.tar"
export AI_TEST_POST_TAR="$control/post.tar"
export AI_TEST_IDENTITY="$identity"
export AI_TEST_REMOTE_STDIN="$remote_stdin"

set +e
PATH="$fake_bin:$PATH" bash "$collector" \
	--output "$short_output" \
	--installed-full-sha256 "$installed_sha256" \
	--wait-seconds 1199 \
	>"$control/short.stdout" 2>"$control/short.stderr"
short_rc=$?
set -e
[[ "$short_rc" == 2 ]] || die "short wait exit was $short_rc, expected 2"
grep -q -- '--wait-seconds must be at least 1200' "$control/short.stderr" || \
	die 'short wait rejection reason changed'
[[ ! -e "$ssh_log" ]] || die 'short wait reached SSH unexpectedly'
[[ ! -e "$short_output" && ! -L "$short_output" ]] || \
	die 'short wait published recovery evidence'

set +e
PATH="$fake_bin:$PATH" bash "$collector" \
	--output "$wrong_hash_output" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	--wait-seconds 1200 \
	>"$control/wrong-hash.stdout" 2>"$control/wrong-hash.stderr"
wrong_hash_rc=$?
set -e
[[ "$wrong_hash_rc" == 2 ]] || die "wrong-hash exit was $wrong_hash_rc, expected 2"
grep -q -- '--installed-full-sha256 is not Candidate AI' "$control/wrong-hash.stderr" || \
	die 'recovery collector accepted a different installed-image hash'
[[ ! -e "$ssh_log" ]] || die 'wrong installed-image hash reached SSH unexpectedly'
[[ ! -e "$wrong_hash_output" && ! -L "$wrong_hash_output" ]] || \
	die 'wrong installed-image hash published recovery evidence'

set +e
PATH="$fake_bin:$PATH" bash "$collector" \
	--output "$output" \
	--installed-full-sha256 "$installed_sha256" \
	--wait-seconds 1200 \
	>"$control/stdout" 2>"$control/stderr"
collector_rc=$?
set -e
if ((collector_rc != 0)); then
	cat "$control/stderr" >&2
	die "synthetic recovery collector exited $collector_rc"
fi

[[ "$(<"$state_count")" == 5 ]] || die 'collector did not take two bound snapshots plus one reconnect state'
[[ "$(<"$true_count")" == 2 ]] || die 'collector did not require two disconnect probes'
[[ "$(<"$tar_count")" == 2 ]] || die 'collector did not take exactly one pre and one post archive'
[[ -d "$output" && ! -L "$output" ]] || die 'collector did not publish private evidence'
[[ "$(stat -f '%Lp' "$output" 2>/dev/null || stat -c '%a' "$output")" == 700 ]] || \
	die 'collector output mode is not 0700'
[[ -z "$(find "$output" -type f ! -perm 0600 -print -quit)" ]] || \
	die 'collector evidence file mode is not 0600'

validation="$output/validation.txt"
cycle="$output/cycle.env"
delta="$output/pstore-delta.tsv"
[[ -f "$validation" && -f "$cycle" && -f "$delta" ]] || \
	die 'collector omitted canonical evidence records'
grep -qx 'classification=INCONCLUSIVE' "$validation" || \
	die 'generic pstore strings incorrectly attributed Candidate AI'
grep -qx 'candidate_ai_attribution=absent' "$validation" || \
	die 'inconclusive collector invented Candidate AI attribution'
grep -qx 'generic_candidate_l_ac_ab_identity_weight=zero' "$validation" || \
	die 'generic lineage identity boundary changed'
grep -qx 'ssh_strict_host_key_checking=yes' "$cycle" || \
	die 'strict host key contract was not preserved'
grep -qx 'wait_seconds=1200' "$cycle" || die '1200-second deadline was not recorded'
grep -qx 'boot_id_changed=yes' "$cycle" || die 'changed recovery boot ID was not recorded'
grep -qx 'reboot_command_issued=no' "$cycle" || die 'no-reboot boundary changed'
grep -qx 'device_write_operations=none' "$cycle" || die 'no-write boundary changed'
grep -qx 'remote_pstore_delete_operations=none' "$cycle" || \
	die 'remote pstore preservation boundary changed'
grep -q '^stale-content-renamed[[:space:]]dmesg-ramoops-1' "$delta" || \
	die 'renamed stale pstore content was not classified stale'

ssh_calls="$(wc -l <"$ssh_log" | awk '{ print $1 }')"
strict_calls="$(grep -c -- '-o StrictHostKeyChecking=yes' "$ssh_log")"
[[ "$strict_calls" == "$ssh_calls" ]] || die 'an SSH call omitted strict host key checking'
[[ "$(grep -c -- '-o IdentitiesOnly=yes' "$ssh_log")" == "$ssh_calls" ]] || \
	die 'an SSH call omitted IdentitiesOnly'
[[ "$(grep -c -- '-o IdentityAgent=none' "$ssh_log")" == "$ssh_calls" ]] || \
	die 'an SSH call used an agent'
[[ "$(grep -c -- "-i $identity" "$ssh_log")" == "$ssh_calls" ]] || \
	die 'an SSH call omitted the exact private key'
[[ "$(grep -c -- 'gemini@192.168.1.50' "$ssh_log")" == "$ssh_calls" ]] || \
	die 'an SSH call changed the exact target'
if grep -Eq 'reboot|shutdown|poweroff|/sys/fs/pstore/.+rm| dd ' "$ssh_log" "$remote_stdin"; then
	die 'mocked remote command stream contains a reboot, write, or pstore deletion'
fi

printf 'validation=candidate-ai-recovery-collector-synthetic\n'
printf 'pre_snapshot=one\npost_snapshot=one\n'
printf 'disconnect_failed_probes=2\nreconnect_changed_boot_id=passed\n'
printf 'recovery_kernel=3.18.41+\nrecovery_root=/dev/mmcblk0p29\n'
printf 'wait_minimum_1200=enforced\n'
printf 'ssh_target_identity_hostkey=exact-mocked\n'
printf 'classification_without_runtime=INCONCLUSIVE\n'
printf 'generic_candidate_l_ac_ab_identity_weight=zero\n'
printf 'remote_pstore_deletion=none\nreboot_command=none\ndevice_write_operations=none\n'
printf 'device_access=none-ssh-and-sleep-mocked\n'
