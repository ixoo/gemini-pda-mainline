#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
collector="$script_dir/collect-one-way-recovery.sh"
control="$(mktemp -d /tmp/candidate-aj-one-way.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
test_repo="$control/repo"
test_scripts="$test_repo/experiments/2026-07-22-a72-reject-cpu8-request/scripts"
fake_bin="$control/bin"
fake_home="$control/home"
runtime_dir="$test_repo/artifacts/runtime-captures/attempt"
output="$test_repo/artifacts/device-pstore/result"

cleanup() { [[ ! -d "$control" ]] || rm -r -- "$control"; }
trap cleanup EXIT

mkdir -m 0700 -p "$test_scripts" "$fake_bin" "$fake_home/.ssh" \
	"$test_repo/artifacts/credentials" "$runtime_dir" \
	"$test_repo/artifacts/device-pstore" "$control/pstore"
chmod 0700 "$test_repo/artifacts" "$test_repo/artifacts/runtime-captures" \
	"$test_repo/artifacts/device-pstore" "$runtime_dir"
cp "$collector" "$script_dir/candidate_aj.py" "$script_dir/validate-runtime.py" \
	"$script_dir/validate-native-reboot.py" "$script_dir/test-runtime-validator.py" \
	"$script_dir/test-native-reboot-validator.py" "$test_scripts/"
printf 'test-private-key\n' >"$test_repo/artifacts/credentials/gemini_ed25519"
printf 'test-known-host\n' >"$fake_home/.ssh/known_hosts"
chmod 0600 "$test_repo/artifacts/credentials/gemini_ed25519" "$fake_home/.ssh/known_hosts"

python3 - "$test_scripts" "$runtime_dir/runtime.txt" "$runtime_dir/native-reboot.txt" <<'PY'
import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])

def load(name, module_name):
    path = root / name
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

runtime = load("validate-runtime.py", "one_way_runtime")
runtime_tests = load("test-runtime-validator.py", "one_way_runtime_fixture")
native = load("validate-native-reboot.py", "one_way_native")
native_tests = load("test-native-reboot-validator.py", "one_way_native_fixture")
runtime_text = runtime_tests.fixture(runtime)
boot_id = native.runtime_boot_id(runtime_text, native.AJ.PADDED_SHA256)
native_text = native_tests.fixture(native, runtime_text, boot_id)
path = pathlib.Path(sys.argv[2]); path.write_bytes(runtime_text.encode()); path.chmod(0o600)
path = pathlib.Path(sys.argv[3]); path.write_bytes(native_text.encode()); path.chmod(0o600)
PY

printf 'Candidate AJ pstore fixture\n' >"$control/pstore/console-ramoops"
tar -C "$control/pstore" -cf "$control/pstore.tar" .

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/date" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
count=0
[[ ! -f "$AJ_ONE_WAY_DATE_COUNT" ]] || read -r count <"$AJ_ONE_WAY_DATE_COUNT"
if [[ "${1:-}" == +%s ]]; then
	count=$((count + 1)); printf '%s\n' "$count" >"$AJ_ONE_WAY_DATE_COUNT"
	printf '%s\n' "$((2000000000 + count))"
elif [[ "${1:-}" == -u && "${2:-}" == +%Y-%m-%dT%H:%M:%SZ ]]; then
	printf '2033-05-18T03:33:20Z\n'
else
	exit 91
fi
EOF
cat >"$fake_bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
count=0
[[ ! -f "$AJ_ONE_WAY_IFCONFIG_COUNT" ]] || read -r count <"$AJ_ONE_WAY_IFCONFIG_COUNT"
case "${1:-}" in
-l)
	count=$((count + 1)); printf '%s\n' "$count" >"$AJ_ONE_WAY_IFCONFIG_COUNT"
	if ((count <= 4)); then printf 'en0 en7\n'; else printf 'en0\n'; fi
	;;
en0) printf 'en0: flags=8863\n\tether 02:00:00:00:00:01\n' ;;
en7)
	printf 'en7: flags=8863\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
*) exit 92 ;;
esac
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
count=0
[[ ! -f "$AJ_ONE_WAY_IFCONFIG_COUNT" ]] || read -r count <"$AJ_ONE_WAY_IFCONFIG_COUNT"
((count <= 4)) || exit 1
printf '   route to: 10.15.19.82\n'
printf 'destination: 10.15.19.82\n'
printf '  interface: en7\n'
EOF
cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$AJ_ONE_WAY_SSH_LOG"
last=${!#}
case "$last" in
true) exit 255 ;;
'sudo -n -- /bin/sh -s')
	cat >/dev/null
	printf 'kernel=3.18.41+\narchitecture=aarch64\nroot_source=/dev/mmcblk0p29\n'
	printf 'boot_id=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb\n'
	printf 'pstore_directory=present\n'
	;;
'sudo -n -- tar -C /sys/fs/pstore -cf - .') cat "$AJ_ONE_WAY_PSTORE_TAR" ;;
*) exit 93 ;;
esac
EOF
chmod 0700 "$fake_bin"/*

export AJ_ONE_WAY_DATE_COUNT="$control/date.count"
export AJ_ONE_WAY_IFCONFIG_COUNT="$control/ifconfig.count"
export AJ_ONE_WAY_SSH_LOG="$control/ssh.log"
export AJ_ONE_WAY_PSTORE_TAR="$control/pstore.tar"

HOME="$fake_home" PATH="$fake_bin:$PATH" bash "$test_scripts/collect-one-way-recovery.sh" \
	--output "$output" \
	--installed-full-sha256 8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257 \
	--runtime-capture "$runtime_dir/runtime.txt" \
	--native-reboot-capture "$runtime_dir/native-reboot.txt" \
	--wait-seconds 1200 >"$control/stdout" 2>"$control/stderr" || {
	cat "$control/stderr" >&2
	die 'mocked one-way recovery observation failed'
}

[[ -d "$output" && ! -L "$output" ]] || die 'one-way evidence was not published'
grep -qx 'runtime_companion_status=valid' "$output/cycle.env" || die 'runtime binding failed'
grep -qx 'native_reboot_companion_status=valid' "$output/cycle.env" || die 'native binding failed'
grep -qx 'native_reboot_transition_binding=valid-but-outside-observer-window' \
	"$output/cycle.env" || die 'preexisting native evidence was overstated'
grep -qx 'returned_boot_id_differs_from_known_pre_cycle=yes' "$output/cycle.env" || \
	die 'changed recovery boot gate was lost'
grep -qx 'boot_id_sha256=57b0e587fbbd72e6e16ede259df5d3598f79dbb3cd91acfeb13ab28f8914e3b8' \
	"$output/recovery/state.env" || die 'returned boot ID was not recorded only by digest'
grep -qx 'collector_reboot_command_issued=no' "$output/cycle.env" || die 'no-reboot boundary changed'
grep -qx 'device_partition_reads=none' "$output/cycle.env" || die 'partition-read boundary changed'
grep -qx 'pstore_access=read-only' "$output/cycle.env" || die 'pstore boundary changed'
if grep -Eq '(reboot|shutdown|poweroff|/dev/mmc|/dev/watchdog|\bdd\b)' "$AJ_ONE_WAY_SSH_LOG"; then
	die 'observer remote command surface gained a reboot or storage path'
fi
(
	cd "$output"
	shasum -a 256 -c SHA256SUMS >/dev/null
) || die 'published one-way checksum inventory failed'

printf 'validation=candidate-aj-one-way-recovery-mocked\n'
printf 'source_usb_present=yes\nsource_gemian_ssh_unreachable=yes\n'
printf 'usb_disappearance=two-exact-absence-observations\n'
printf 'changed_exact_gemian_return=yes\npstore_access=read-only\n'
printf 'preexisting_native_companion=valid-not-overstated\n'
printf 'device_access=none\n'
