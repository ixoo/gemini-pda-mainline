#!/usr/bin/env bash

# Mocked transport test: missing companion files must still publish exact
# pre/post evidence and derive only the unique AJ pstore partial attribution.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-recovery-evidence.sh"
private_root="$repo_root/artifacts/device-pstore"
runtime_root="$repo_root/artifacts/runtime-captures"
control="$(mktemp -d /tmp/candidate-aj-recovery-collector.XXXXXX)"
fake_bin="$control/bin"
runtime_dir="$runtime_root/aj-recovery-collector-selftest-$$-$RANDOM"
output="$private_root/aj-recovery-collector-selftest-$$-$RANDOM"
invalid_runtime_dir="$runtime_root/aj-recovery-invalid-selftest-$$-$RANDOM"
invalid_output="$private_root/aj-recovery-invalid-selftest-$$-$RANDOM"
mkdir -m 0700 "$fake_bin" "$runtime_dir" "$invalid_runtime_dir" "$control/pre" "$control/post"

cleanup() {
	if [[ -d "$output" && ! -L "$output" && "$(dirname -- "$output")" == "$private_root" && "$(basename -- "$output")" == aj-recovery-collector-selftest-$$-* ]]; then rm -rf -- "$output"; fi
	if [[ -d "$invalid_output" && ! -L "$invalid_output" && "$(dirname -- "$invalid_output")" == "$private_root" && "$(basename -- "$invalid_output")" == aj-recovery-invalid-selftest-$$-* ]]; then rm -rf -- "$invalid_output"; fi
	if [[ -d "$runtime_dir" && ! -L "$runtime_dir" && "$(dirname -- "$runtime_dir")" == "$runtime_root" && "$(basename -- "$runtime_dir")" == aj-recovery-collector-selftest-$$-* ]]; then rm -rf -- "$runtime_dir"; fi
	if [[ -d "$invalid_runtime_dir" && ! -L "$invalid_runtime_dir" && "$(dirname -- "$invalid_runtime_dir")" == "$runtime_root" && "$(basename -- "$invalid_runtime_dir")" == aj-recovery-invalid-selftest-$$-* ]]; then rm -rf -- "$invalid_runtime_dir"; fi
	[[ ! -d "$control" ]] || rm -rf -- "$control"
}
trap cleanup EXIT

printf 'old recovery pstore record\n' >"$control/pre/console-ramoops"
python3 - "$script_dir/candidate_aj.py" "$control/post/console-ramoops" <<'PY'
import importlib.util
import pathlib
import sys
source = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("aj_collector_test_identity", source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
path = pathlib.Path(sys.argv[2])
path.write_text(
    "old recovery pstore record\n"
    + f"Kernel command line: {module.CMDLINE}\n"
    + "mt6797-psci: CPU8 boot rejected: A72 power sequence inactive\n"
    + "CPU8: failed to boot: -11\n",
    encoding="utf-8",
)
PY
COPYFILE_DISABLE=1 tar -C "$control/pre" -cf "$control/pre.tar" .
COPYFILE_DISABLE=1 tar -C "$control/post" -cf "$control/post.tar" .
chmod 0600 "$control/pre.tar" "$control/post.tar"
python3 - "$script_dir" "$control/invalid-runtime.txt" <<'PY'
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
validator = load("validate-runtime.py", "aj_collector_invalid_runtime")
tests = load("test-runtime-validator.py", "aj_collector_invalid_fixture")
content = tests.fixture(validator).replace("\r\n", "\n")
content = content.replace(validator.EXPECTED_CONFIG_SHA256, "0" * 64, 1)
path = pathlib.Path(sys.argv[2])
path.write_text(content, encoding="utf-8")
path.chmod(0o600)
PY

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$AJ_RECOVERY_SSH_LOG"
arguments=" $* "
for required in '-o BatchMode=yes' '-o IdentitiesOnly=yes' '-o IdentityAgent=none' '-o StrictHostKeyChecking=yes' "-i $AJ_RECOVERY_IDENTITY" 'gemini@192.168.1.50'; do
	case "$arguments" in *" $required "*) ;; *) exit 91 ;; esac
done
last=${!#}
case "$last" in
'sudo -n -- /bin/sh -s')
	cat >>"$AJ_RECOVERY_REMOTE_STDIN"
	count=0; [[ ! -f "$AJ_RECOVERY_STATE_COUNT" ]] || read -r count <"$AJ_RECOVERY_STATE_COUNT"
	count=$((count + 1)); printf '%s\n' "$count" >"$AJ_RECOVERY_STATE_COUNT"
	if ((count <= 2)); then boot=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa; else boot=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb; fi
	printf 'kernel=3.18.41+\narchitecture=aarch64\nroot_source=/dev/mmcblk0p29\nboot_id=%s\npstore_directory=present\n' "$boot"
	;;
'sudo -n -- tar -C /sys/fs/pstore -cf - .')
	count=0; [[ ! -f "$AJ_RECOVERY_TAR_COUNT" ]] || read -r count <"$AJ_RECOVERY_TAR_COUNT"
	count=$((count + 1)); printf '%s\n' "$count" >"$AJ_RECOVERY_TAR_COUNT"
	case "$count" in 1) cat "$AJ_RECOVERY_PRE_TAR" ;; 2) cat "$AJ_RECOVERY_POST_TAR" ;; *) exit 92 ;; esac
	;;
true)
	count=0; [[ ! -f "$AJ_RECOVERY_TRUE_COUNT" ]] || read -r count <"$AJ_RECOVERY_TRUE_COUNT"
	count=$((count + 1)); printf '%s\n' "$count" >"$AJ_RECOVERY_TRUE_COUNT"
	if ((count == 2)) && [[ "${AJ_RECOVERY_CREATE_INVALID:-no}" == yes ]]; then
		cp "$AJ_RECOVERY_INVALID_FIXTURE" "$AJ_RECOVERY_PLANNED_RUNTIME"
		chmod 0600 "$AJ_RECOVERY_PLANNED_RUNTIME"
	fi
	exit 255
	;;
*) exit 93 ;;
esac
EOF
chmod 0700 "$fake_bin"/*

export AJ_RECOVERY_SSH_LOG="$control/ssh.log"
export AJ_RECOVERY_REMOTE_STDIN="$control/remote-stdin.log"
export AJ_RECOVERY_STATE_COUNT="$control/state.count"
export AJ_RECOVERY_TAR_COUNT="$control/tar.count"
export AJ_RECOVERY_TRUE_COUNT="$control/true.count"
export AJ_RECOVERY_PRE_TAR="$control/pre.tar"
export AJ_RECOVERY_POST_TAR="$control/post.tar"
export AJ_RECOVERY_IDENTITY="$repo_root/artifacts/credentials/gemini_ed25519"
export AJ_RECOVERY_INVALID_FIXTURE="$control/invalid-runtime.txt"
installed=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257

PATH="$fake_bin:$PATH" bash "$collector" --output "$output" \
	--installed-full-sha256 "$installed" --runtime-capture "$runtime_dir/runtime.txt" \
	--native-reboot-capture "$runtime_dir/native-reboot.txt" --wait-seconds 1200 \
	>"$control/stdout" 2>"$control/stderr" || { cat "$control/stderr" >&2; die 'mocked recovery collection failed'; }

[[ -d "$output" && ! -L "$output" ]] || die 'recovery collector did not publish evidence'
grep -qx 'runtime_companion_status=absent' "$output/derived.env" || die 'missing runtime was not preserved as absent'
grep -qx 'native_reboot_companion_status=absent' "$output/derived.env" || die 'missing native companion was not preserved as absent'
grep -qx 'classification=ATTRIBUTED_PARTIAL' "$output/derived.env" || die 'unique exact AJ pstore triplet was not partially attributed'
grep -qx 'candidate_aj_attribution=unique-exact-aj-pstore-signatures' "$output/derived.env" || die 'partial attribution basis changed'
grep -qx 'collector_reboot_command_issued=no' "$output/cycle.env" || die 'collector no-reboot boundary changed'
grep -qx 'device_partition_reads=none' "$output/cycle.env" || die 'collector partition-read boundary changed'
[[ "$(<"$AJ_RECOVERY_STATE_COUNT")" == 5 && "$(<"$AJ_RECOVERY_TAR_COUNT")" == 2 && "$(<"$AJ_RECOVERY_TRUE_COUNT")" == 2 ]] || die 'recovery observation cardinality changed'
if grep -Eiq '(reboot|shutdown|poweroff|/dev/mmc|/dev/watchdog|\bdd\b|rm .*/sys/fs/pstore)' "$AJ_RECOVERY_SSH_LOG" "$AJ_RECOVERY_REMOTE_STDIN"; then
	die 'collector mocked remote stream gained reboot or storage mutation access'
fi

rm -- "$AJ_RECOVERY_STATE_COUNT" "$AJ_RECOVERY_TAR_COUNT" "$AJ_RECOVERY_TRUE_COUNT"
export AJ_RECOVERY_CREATE_INVALID=yes
export AJ_RECOVERY_PLANNED_RUNTIME="$invalid_runtime_dir/runtime.txt"
PATH="$fake_bin:$PATH" bash "$collector" --output "$invalid_output" \
	--installed-full-sha256 "$installed" --runtime-capture "$invalid_runtime_dir/runtime.txt" \
	--native-reboot-capture "$invalid_runtime_dir/native-reboot.txt" --wait-seconds 1200 \
	>"$control/invalid.stdout" 2>"$control/invalid.stderr" || { cat "$control/invalid.stderr" >&2; die 'safe-invalid recovery collection failed instead of publishing'; }
[[ -d "$invalid_output" && ! -L "$invalid_output" ]] || die 'safe-invalid recovery evidence was not published'
grep -qx 'runtime_companion_status=invalid' "$invalid_output/derived.env" || die 'invalid runtime status was not retained'
grep -qx 'runtime_companion_preserved=yes' "$invalid_output/cycle.env" || die 'safe invalid runtime was not preserved'
grep -qx 'classification=ATTRIBUTED_PARTIAL' "$invalid_output/derived.env" || die 'invalid runtime destroyed exact pstore partial attribution'
[[ -f "$invalid_output/candidate-aj-runtime.txt" && "$(stat -f '%Lp' "$invalid_output/candidate-aj-runtime.txt" 2>/dev/null || stat -c '%a' "$invalid_output/candidate-aj-runtime.txt")" == 600 ]] || die 'preserved invalid runtime is absent or not mode 0600'
unset AJ_RECOVERY_CREATE_INVALID AJ_RECOVERY_PLANNED_RUNTIME

printf 'validation=candidate-aj-recovery-collector-mocked\n'
printf 'missing_runtime_evidence_published=yes\nmissing_native_evidence_published=yes\n'
printf 'invalid_runtime_evidence_preserved_and_published=yes\n'
printf 'classification=ATTRIBUTED_PARTIAL\ncollector_reboot_command_issued=no\n'
printf 'device_partition_reads=none\ndevice_write_operations=none\ndevice_access=none\n'
