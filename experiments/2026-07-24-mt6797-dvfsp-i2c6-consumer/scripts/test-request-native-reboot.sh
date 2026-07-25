#!/usr/bin/env bash

# Prove the checked-in requester refuses before transport, then exercise a
# source-calibrated temporary mirror with mocked host/network/device commands.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
requester="$script_dir/request-native-reboot.sh"
validator="$script_dir/validate-native-reboot.py"
control="$(mktemp -d /tmp/candidate-ap-native-request.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
mirror="$control/repo"
mirror_scripts="$mirror/experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/scripts"
runtime_root="$mirror/artifacts/runtime-captures"
capture_dir="$runtime_root/candidate-ap-runtime-selftest"
fake_bin="$control/bin"
padded=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9
config=3333333333333333333333333333333333333333333333333333333333333333
live_fdt=4444444444444444444444444444444444444444444444444444444444444444
boot_id=01234567-89ab-4def-8123-456789abcdef

cleanup() { [[ ! -d "$control" ]] || rm -rf -- "$control"; }
trap cleanup EXIT
mkdir -p "$mirror_scripts" "$capture_dir" "$fake_bin"
chmod 0700 "$mirror_scripts" "$capture_dir" "$fake_bin"
chmod 0700 "$mirror/artifacts" "$runtime_root"

export AP_REQUEST_DISCONNECTED="$control/disconnected"
export AP_REQUEST_NC_ARGS="$control/nc-args"
export AP_REQUEST_REMOTE_COMMAND="$control/remote-command"
cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
set -eu
: >"$AP_REQUEST_NC_ARGS"
exit 99
EOF
chmod 0700 "$fake_bin/nc"

# The checked-in production requester must stop at its explicit unresolved
# source-pin gate even when given AP's real padded identity. It must not inspect
# a capture, host interface, route, or mocked transport.
set +e
PATH="$fake_bin:$PATH" bash "$requester" \
	--runtime-capture "$control/nonexistent/runtime.txt" \
	--output "$control/nonexistent/native-reboot.txt" \
	--installed-full-sha256 "$padded" \
	--expected-runtime-outcome PASS \
	>"$control/unresolved.stdout" 2>"$control/unresolved.stderr"
unresolved_rc=$?
set -e
((unresolved_rc == 2)) || die "unresolved production exit was $unresolved_rc"
if grep -q 'TO_PIN_AFTER_' "$requester"; then
	grep -q 'Candidate AP native-reboot production source pins remain unresolved' \
		"$control/unresolved.stderr" || \
		die 'unresolved production refusal changed'
	production_pins=unresolved
else
	grep -Eq \
		'runtime capture directory is not Candidate AP|runtime capture is not in one direct private child|runtime capture directory is unsafe|runtime capture is absent or unsafe' \
		"$control/unresolved.stderr" || \
		die 'calibrated production evidence refusal changed'
	production_pins=calibrated
fi
[[ ! -e "$AP_REQUEST_NC_ARGS" ]] || \
	die 'unresolved production requester reached nc'

cp "$requester" "$mirror_scripts/request-native-reboot.sh"
cp "$validator" "$mirror_scripts/validate-native-reboot.py"
cat >"$mirror_scripts/candidate_ap.py" <<'PY'
PADDED_SHA256 = "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
AO_PADDED_SHA256 = "2222222222222222222222222222222222222222222222222222222222222222"
CONFIG_SHA256 = "3333333333333333333333333333333333333333333333333333333333333333"
def require_artifact_pins():
    return None
PY
cat >"$mirror_scripts/collect-runtime.sh" <<'EOF'
#!/usr/bin/env bash
# fixture collector
EOF
cat >"$mirror_scripts/validate-runtime.py" <<'PY'
#!/usr/bin/env python3
from types import SimpleNamespace

PADDED = "602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9"
CONFIG = "3333333333333333333333333333333333333333333333333333333333333333"
LIVE = "4444444444444444444444444444444444444444444444444444444444444444"
BOOT = "01234567-89ab-4def-8123-456789abcdef"
FIXTURE = (
    "__AP_HOST_BEGIN__\n"
    "interface=en7\n"
    "route_interface=en7\n"
    "__AP_HOST_END__\n"
    "__AP_IDENTITY_BEGIN__\n"
    f"boot_id={BOOT}\n"
    "__AP_IDENTITY_END__\n"
    "__AP_STATE1_BEGIN__\n"
    "ac_ready_count=1\n"
    "__AP_STATE1_END__\n"
)

def normalize_capture(text):
    return text.replace("\r", "")

def validate_structure(text):
    for name in ("HOST", "IDENTITY"):
        if text.count(f"__AP_{name}_BEGIN__") != 1:
            raise ValueError("runtime begin marker changed")
        if text.count(f"__AP_{name}_END__") != 1:
            raise ValueError("runtime end marker changed")

def section(text, name):
    begin = f"__AP_{name}_BEGIN__\n"
    end = f"\n__AP_{name}_END__"
    return text.split(begin, 1)[1].split(end, 1)[0]

def key_values(text):
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in result:
            raise ValueError("runtime key/value changed")
        result[key] = value
    return result

def validate_collector_source(path):
    if path.read_text() != "#!/usr/bin/env bash\n# fixture collector\n":
        raise ValueError("fixture collector changed")

def validate(text, installed, config, live_fdt, boot_id):
    if (
        text != FIXTURE
        or installed != PADDED
        or config != CONFIG
        or live_fdt != LIVE
        or boot_id != BOOT
    ):
        raise ValueError("runtime fixture binding changed")
    return SimpleNamespace(outcome="PASS", boot_id=BOOT)
PY
cat >"$mirror_scripts/validate-live-fdt-delta.py" <<'PY'
EXPECTED_LIVE_FDT_SHA256 = "4444444444444444444444444444444444444444444444444444444444444444"
EXPECTED_LIVE_FDT_SIZE = "4096"
PY
cat >"$capture_dir/runtime.txt" <<EOF
__AP_HOST_BEGIN__
interface=en7
route_interface=en7
__AP_HOST_END__
__AP_IDENTITY_BEGIN__
boot_id=$boot_id
__AP_IDENTITY_END__
__AP_STATE1_BEGIN__
ac_ready_count=1
__AP_STATE1_END__
EOF
chmod 0600 "$capture_dir/runtime.txt"
chmod 0700 "$mirror_scripts/collect-runtime.sh"

candidate_sha="$(shasum -a 256 "$mirror_scripts/candidate_ap.py" | awk '{ print $1 }')"
runtime_sha="$(shasum -a 256 "$mirror_scripts/validate-runtime.py" | awk '{ print $1 }')"
live_fdt_validator_sha="$(
	shasum -a 256 "$mirror_scripts/validate-live-fdt-delta.py" | awk '{ print $1 }'
)"
python3 - "$mirror_scripts/validate-native-reboot.py" \
	"$candidate_sha" "$runtime_sha" "$live_fdt_validator_sha" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
for name, value in (
    ("CANDIDATE_AP_SHA256", sys.argv[2]),
    ("RUNTIME_VALIDATOR_SHA256", sys.argv[3]),
    ("LIVE_FDT_VALIDATOR_SHA256", sys.argv[4]),
):
    pattern = (
        rf'(?m)^{name} = (?:'
        rf'"[^"]+"|\(\n    "[^"]+"\n\))$'
    )
    text, count = re.subn(pattern, f'{name} = "{value}"', text)
    if count != 1:
        raise RuntimeError(f"unexpected native-validator assignment: {name}")
path.write_text(text)
PY
native_sha="$(
	shasum -a 256 "$mirror_scripts/validate-native-reboot.py" | awk '{ print $1 }'
)"
python3 - "$mirror_scripts/request-native-reboot.sh" \
	"$candidate_sha" "$runtime_sha" "$live_fdt_validator_sha" "$native_sha" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
for name, value in (
    ("CANDIDATE_AP_SHA256", sys.argv[2]),
    ("RUNTIME_VALIDATOR_SHA256", sys.argv[3]),
    ("LIVE_FDT_VALIDATOR_SHA256", sys.argv[4]),
    ("NATIVE_VALIDATOR_SHA256", sys.argv[5]),
):
    pattern = rf"(?m)^readonly {name}=\S+$"
    text, count = re.subn(pattern, f"readonly {name}={value}", text)
    if count != 1:
        raise RuntimeError(f"unexpected requester assignment: {name}")
path.write_text(text)
PY

cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
set -eu
if [ "$1" = -a ]; then
	if [ ! -e "$AP_REQUEST_DISCONNECTED" ]; then
		printf 'en7: flags\n\tether 42:00:15:19:82:00\n\tinet 10.15.19.1 netmask 0xffffff00\n'
	fi
	exit 0
fi
test "$1" = en7
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
printf '%s\n' "$*" >"$AP_REQUEST_NC_ARGS"
cat >"$AP_REQUEST_REMOTE_COMMAND"
test "$(grep -c '^/bin/reboot$' "$AP_REQUEST_REMOTE_COMMAND")" = 1
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC\n'
printf 'Direct USB link only: device 10.15.19.82/24, TCP port 2323.\n'
printf 'Security: unauthenticated and unencrypted root shell; trusted host only.\n'
printf 'Candidate AC status follows:\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC entry profile=usb-gadget-ethernet baseline=candidate-AB storage_access=none runtime_networking=usb0-static\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb0=present wait_seconds=0\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC services=launched usb_network=background worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 local_console=unchanged watchdog_userspace=none\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb0=configured address=10.15.19.82/24 operstate=up carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC service=nc status=listening address=10.15.19.82 port=2323 shell=/bin/usb-shell authentication=none encryption=none direct_link_only=yes\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=session-entry usb0_operstate=up usb0_carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=session-entry usb0_operstate=up usb0_carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes\n'
printf '\n\n'
printf 'BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1) built-in shell (ash)\n'
printf "Enter 'help' for a list of built-in commands.\n"
printf '\n'
printf 'GEMINI-AC-USB# __AP_NATIVE_REQUEST_BEGIN__\n'
printf 'GEMINI-AC-USB# candidate_boot_id=01234567-89ab-4def-8123-456789abcdef\n'
printf 'GEMINI-AC-USB# live_boot_id=01234567-89ab-4def-8123-456789abcdef\n'
printf 'GEMINI-AC-USB# reboot_sha256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7\n'
printf 'GEMINI-AC-USB# reboot_dispatch=/bin/reboot\n'
printf 'GEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n'
printf 'GEMINI-AC-USB# > > > request_authorized=yes\n'
printf 'GEMINI-AC-USB# storage_access=none\n'
printf 'GEMINI-AC-USB# device_partition_reads=none\n'
printf 'GEMINI-AC-USB# watchdog_access=none\n'
printf 'GEMINI-AC-USB# i2c_access=none\n'
printf 'GEMINI-AC-USB# regulator_access=none\n'
printf 'GEMINI-AC-USB# cpu_control_access=none\n'
printf 'GEMINI-AC-USB# power_state_access=none\n'
printf 'GEMINI-AC-USB# sync_requested=no\n'
printf 'GEMINI-AC-USB# request_count=1\n'
printf 'GEMINI-AC-USB# __AP_NATIVE_REQUEST_END__\n'
printf 'GEMINI-AC-USB# Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
: >"$AP_REQUEST_DISCONNECTED"
EOF
chmod 0700 "$fake_bin"/*

PATH="$fake_bin:$PATH" bash "$mirror_scripts/request-native-reboot.sh" \
	--runtime-capture "$capture_dir/runtime.txt" \
	--output "$capture_dir/native-reboot.txt" \
	--installed-full-sha256 "$padded" \
	--expected-runtime-outcome PASS \
	>"$control/calibrated.stdout" 2>"$control/calibrated.stderr" || {
		cat "$control/calibrated.stderr" >&2
		die 'calibrated mocked request failed'
	}

[[ -f "$capture_dir/native-reboot.txt" && \
	! -L "$capture_dir/native-reboot.txt" ]] || \
	die 'mocked native reboot evidence is absent'
mode="$(
	stat -f '%Lp' "$capture_dir/native-reboot.txt" 2>/dev/null || \
		stat -c '%a' "$capture_dir/native-reboot.txt"
)"
[[ "$mode" == 600 ]] || die "native reboot evidence mode is $mode"
grep -q -- '-4 -b en7 -s 10.15.19.1' "$AP_REQUEST_NC_ARGS" || \
	die 'nc was not bound to the validated USB interface/source'
[[ "$(grep -c '^/bin/reboot$' "$AP_REQUEST_REMOTE_COMMAND")" == 1 ]] || \
	die 'exact inherited /bin/reboot dispatch count changed'
grep -Fq '/proc/sys/kernel/random/boot_id' "$AP_REQUEST_REMOTE_COMMAND" || \
	die 'fresh runtime boot-ID gate disappeared'
grep -Fq 'sha256sum /bin/reboot' "$AP_REQUEST_REMOTE_COMMAND" || \
	die 'reboot wrapper hash gate disappeared'
grep -q '^native_runtime_preflight=candidate-ap-native-reboot-preflight$' \
	"$capture_dir/native-reboot.txt" || \
	die 'real native-validator preflight was not recorded'
grep -q '^connection_closed_after_request=yes$' \
	"$capture_dir/native-reboot.txt" || die 'closed-connection proof is absent'
grep -q '^mac_absence_observation_1=absent$' \
	"$capture_dir/native-reboot.txt" || die 'first MAC-absence proof is absent'
grep -q '^mac_absence_observation_2=absent$' \
	"$capture_dir/native-reboot.txt" || die 'second MAC-absence proof is absent'
if grep -q '__AP_NATIVE_REBOOT_RETURNED__' "$capture_dir/native-reboot.txt"; then
	die 'mocked evidence unexpectedly contains the return marker'
fi
if grep -Eq '(/dev/mmc|/dev/watchdog|/dev/i2c-|/dev/mem|/dev/port|/sys/power|/sys/class/regulator|/sys/devices/system/cpu|i2cget|i2cset|i2ctransfer|devmem|chcpu)' \
	"$AP_REQUEST_REMOTE_COMMAND"; then
	die 'native reboot remote command gained forbidden hardware access'
fi
grep -q '^validation=candidate-ap-native-reboot-request$' \
	"$control/calibrated.stdout" || \
	die 'calibrated mirror did not run final native validation'

printf 'validation=candidate-ap-native-reboot-request-mocked\n'
printf 'production_source_pins=%s\n' "$production_pins"
printf 'unresolved_production_reached_transport=no\n'
printf 'runtime_boot_id_and_live_fdt_preflight=passed\n'
printf 'valid_exact_bin_reboot_dispatches=1\n'
printf 'connection_closed_and_two_mac_absences=passed\n'
printf 'transport=mocked\n'
printf 'device_partition_reads=none\ndevice_write_operations=none\n'
printf 'watchdog_i2c_regulator_cpu_power_state_access=none\n'
printf 'device_access=none\n'
