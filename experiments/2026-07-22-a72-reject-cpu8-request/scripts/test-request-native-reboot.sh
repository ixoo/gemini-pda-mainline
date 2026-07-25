#!/usr/bin/env bash

# All transport and interface commands are mocked. No device or network is used.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
requester="$script_dir/request-native-reboot.sh"
runtime_root="$repo_root/artifacts/runtime-captures"
control="$(mktemp -d /tmp/candidate-aj-native-request.XXXXXX)"
fake_bin="$control/bin"
valid_dir="$runtime_root/aj-native-request-selftest-$$-$RANDOM"
invalid_dir="$runtime_root/aj-native-request-invalid-selftest-$$-$RANDOM"
gate_dir="$runtime_root/aj-native-request-gate-selftest-$$-$RANDOM"
interface_dir="$runtime_root/aj-native-request-interface-selftest-$$-$RANDOM"
iferror_dir="$runtime_root/aj-native-request-iferror-selftest-$$-$RANDOM"
mkdir -m 0700 "$fake_bin" "$valid_dir" "$invalid_dir" "$gate_dir" "$interface_dir" "$iferror_dir"

cleanup() {
	local directory
	for directory in "$valid_dir" "$invalid_dir" "$gate_dir" "$interface_dir" "$iferror_dir"; do
		if [[ -d "$directory" && ! -L "$directory" && "$(dirname -- "$directory")" == "$runtime_root" ]]; then
			case "$(basename -- "$directory")" in aj-native-request-*-$$-*) rm -rf -- "$directory" ;; esac
		fi
	done
	[[ ! -d "$control" ]] || rm -rf -- "$control"
}
trap cleanup EXIT

python3 - "$script_dir" "$valid_dir/runtime.txt" <<'PY'
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
validator = load("validate-runtime.py", "aj_request_test_runtime")
tests = load("test-runtime-validator.py", "aj_request_test_fixture")
path = pathlib.Path(sys.argv[2])
path.write_text(tests.fixture(validator).replace("\r\n", "\n"), encoding="utf-8")
path.chmod(0o600)
PY
cp "$valid_dir/runtime.txt" "$invalid_dir/runtime.txt"
cp "$valid_dir/runtime.txt" "$gate_dir/runtime.txt"
cp "$valid_dir/runtime.txt" "$interface_dir/runtime.txt"
cp "$valid_dir/runtime.txt" "$iferror_dir/runtime.txt"
chmod 0600 "$invalid_dir/runtime.txt" "$gate_dir/runtime.txt" "$interface_dir/runtime.txt" "$iferror_dir/runtime.txt"
python3 - "$invalid_dir/runtime.txt" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
text = text.replace("64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb", "0" * 64, 1)
path.write_text(text)
path.chmod(0o600)
PY

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
set -eu
if [ "$1" = -a ]; then
	if [ "${AJ_REQUEST_IFCONFIG_ERROR:-no}" = yes ]; then exit 17; fi
	if [ ! -e "$AJ_REQUEST_DISCONNECTED" ]; then
		printf 'en7: flags\n\tether 42:00:15:19:82:00\n\tinet 10.15.19.1 netmask 0xffffff00\n'
	fi
	exit 0
fi
test "$1" = en7
if [ "${AJ_REQUEST_BAD_MAC:-no}" = yes ]; then
	printf 'en7: flags\n\tether 00:00:00:00:00:00\n\tinet 10.15.19.1 netmask 0xffffff00\n'
	exit 0
fi
printf 'en7: flags\n\tether 42:00:15:19:82:00\n\tinet 10.15.19.1 netmask 0xffffff00\n'
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
printf 'interface: en7\n'
EOF
cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
set -eu
count=0
[ ! -f "$AJ_REQUEST_NC_COUNT" ] || read -r count <"$AJ_REQUEST_NC_COUNT"
count=$((count + 1)); printf '%s\n' "$count" >"$AJ_REQUEST_NC_COUNT"
printf '%s\n' "$*" >>"$AJ_REQUEST_NC_ARGS"
cat >"$AJ_REQUEST_REMOTE_COMMAND"
grep -qx '/bin/reboot' "$AJ_REQUEST_REMOTE_COMMAND"
test "$(grep -c '^/bin/reboot$' "$AJ_REQUEST_REMOTE_COMMAND")" = 1
grep -q '\[ "$live_boot_id" != '\''01234567-89ab-cdef-0123-456789abcdef'\'' \] ||' "$AJ_REQUEST_REMOTE_COMMAND"
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC\n'
printf 'GEMINI-AC-USB# __AJ_NATIVE_REQUEST_BEGIN__\n'
printf 'GEMINI-AC-USB# candidate_boot_id=01234567-89ab-cdef-0123-456789abcdef\n'
if [ "${AJ_REQUEST_GATE_REFUSE:-no}" = yes ]; then
	printf 'GEMINI-AC-USB# live_boot_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa\n'
	printf 'GEMINI-AC-USB# reboot_sha256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7\n'
	printf 'GEMINI-AC-USB# reboot_dispatch=/bin/reboot\nGEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n'
	printf 'GEMINI-AC-USB# request_authorized=no\n'
	printf 'GEMINI-AC-USB# storage_access=none\nGEMINI-AC-USB# sync_requested=no\nGEMINI-AC-USB# watchdog_userspace=none\nGEMINI-AC-USB# request_count=1\nGEMINI-AC-USB# __AJ_NATIVE_REQUEST_END__\n'
	exit 93
fi
printf 'GEMINI-AC-USB# live_boot_id=01234567-89ab-cdef-0123-456789abcdef\n'
printf 'GEMINI-AC-USB# reboot_sha256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7\n'
printf 'GEMINI-AC-USB# reboot_dispatch=/bin/reboot\nGEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n'
printf 'GEMINI-AC-USB# > > > > request_authorized=yes\nGEMINI-AC-USB# storage_access=none\nGEMINI-AC-USB# sync_requested=no\nGEMINI-AC-USB# watchdog_userspace=none\nGEMINI-AC-USB# request_count=1\nGEMINI-AC-USB# __AJ_NATIVE_REQUEST_END__\n'
printf 'GEMINI-AC-USB# Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
: >"$AJ_REQUEST_DISCONNECTED"
exit 0
EOF
chmod 0700 "$fake_bin"/*

export AJ_REQUEST_DISCONNECTED="$control/disconnected"
export AJ_REQUEST_NC_COUNT="$control/nc-count"
export AJ_REQUEST_NC_ARGS="$control/nc-args"
export AJ_REQUEST_REMOTE_COMMAND="$control/remote-command"
installed=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257

set +e
PATH="$fake_bin:$PATH" bash "$requester" --runtime-capture "$invalid_dir/runtime.txt" \
	--output "$invalid_dir/native-reboot.txt" --installed-full-sha256 "$installed" \
	>"$control/invalid.stdout" 2>"$control/invalid.stderr"
invalid_rc=$?
set -e
((invalid_rc == 2)) || die "invalid runtime exit was $invalid_rc"
[[ ! -e "$AJ_REQUEST_NC_COUNT" ]] || die 'invalid runtime reached nc'

export AJ_REQUEST_BAD_MAC=yes
set +e
PATH="$fake_bin:$PATH" bash "$requester" --runtime-capture "$interface_dir/runtime.txt" \
	--output "$interface_dir/native-reboot.txt" --installed-full-sha256 "$installed" \
	>"$control/interface.stdout" 2>"$control/interface.stderr"
interface_rc=$?
set -e
((interface_rc == 2)) || die "invalid host interface exit was $interface_rc"
[[ ! -e "$AJ_REQUEST_NC_COUNT" ]] || die 'invalid host interface reached nc'
unset AJ_REQUEST_BAD_MAC

export AJ_REQUEST_GATE_REFUSE=yes
set +e
PATH="$fake_bin:$PATH" bash "$requester" --runtime-capture "$gate_dir/runtime.txt" \
	--output "$gate_dir/native-reboot.txt" --installed-full-sha256 "$installed" \
	>"$control/gate.stdout" 2>"$control/gate.stderr"
gate_rc=$?
set -e
((gate_rc == 2)) || die "refused live gate exit was $gate_rc"
grep -q 'gate refused the request' "$control/gate.stderr" || die 'live gate refusal reason changed'
[[ ! -e "$AJ_REQUEST_DISCONNECTED" ]] || die 'refused live gate simulated a reboot'
unset AJ_REQUEST_GATE_REFUSE

export AJ_REQUEST_IFCONFIG_ERROR=yes
set +e
PATH="$fake_bin:$PATH" bash "$requester" --runtime-capture "$iferror_dir/runtime.txt" \
	--output "$iferror_dir/native-reboot.txt" --installed-full-sha256 "$installed" \
	>"$control/iferror.stdout" 2>"$control/iferror.stderr"
iferror_rc=$?
set -e
((iferror_rc == 2)) || die "interface enumeration failure exit was $iferror_rc"
grep -q 'host interface enumeration failed' "$control/iferror.stderr" || die 'interface enumeration failure was mistaken for MAC absence'
unset AJ_REQUEST_IFCONFIG_ERROR
rm -- "$AJ_REQUEST_DISCONNECTED"

PATH="$fake_bin:$PATH" bash "$requester" --runtime-capture "$valid_dir/runtime.txt" \
	--output "$valid_dir/native-reboot.txt" --installed-full-sha256 "$installed" \
	>"$control/valid.stdout" 2>"$control/valid.stderr" || { cat "$control/valid.stderr" >&2; die 'valid mocked request failed'; }
[[ -f "$valid_dir/native-reboot.txt" && "$(stat -f '%Lp' "$valid_dir/native-reboot.txt" 2>/dev/null || stat -c '%a' "$valid_dir/native-reboot.txt")" == 600 ]] || die 'valid native reboot evidence is absent or not mode 0600'
[[ "$(<"$AJ_REQUEST_NC_COUNT")" == 3 ]] || die 'nc invocation count changed across refused, enumeration-error, and valid requests'
grep -q -- '-4 -b en7 -s 10.15.19.1' "$AJ_REQUEST_NC_ARGS" || die 'nc was not interface/source bound'
if grep -Eq '(/dev/mmc|\bdd\b|flash|mkfs|mount |/dev/watchdog|sync$)' "$AJ_REQUEST_REMOTE_COMMAND"; then
	die 'native reboot remote command gained storage or watchdog access'
fi

printf 'validation=candidate-aj-native-reboot-request-mocked\n'
printf 'invalid_runtime_reached_nc=no\ninvalid_interface_reached_nc=no\nlive_gate_refusal_rebooted=no\n'
printf 'ifconfig_error_counted_as_absence=no\nvalid_exact_reboot_dispatches=1\ntransport=mocked\n'
printf 'device_partition_reads=none\ndevice_write_operations=none\ndevice_access=none\n'
