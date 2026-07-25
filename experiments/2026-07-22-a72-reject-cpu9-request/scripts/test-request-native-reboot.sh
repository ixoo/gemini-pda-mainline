#!/usr/bin/env bash

# Exercise a calibrated temporary mirror with mocked transport, and prove the
# unresolved production requester stops before nc. No device or network is used.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
requester="$script_dir/request-native-reboot.sh"
control="$(mktemp -d /tmp/candidate-ak-native-request.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
mirror="$control/repo"
mirror_scripts="$mirror/experiments/2026-07-22-a72-reject-cpu9-request/scripts"
runtime_root="$mirror/artifacts/runtime-captures"
capture_dir="$runtime_root/candidate-ak-runtime-selftest"
bad_preflight_dir="$runtime_root/candidate-ak-runtime-bad-preflight-selftest"
fake_bin="$control/bin"
padded=1111111111111111111111111111111111111111111111111111111111111111
boot_id=01234567-89ab-cdef-0123-456789abcdef

cleanup() { [[ ! -d "$control" ]] || rm -rf -- "$control"; }
trap cleanup EXIT
mkdir -p "$mirror_scripts" "$capture_dir" "$bad_preflight_dir" "$fake_bin"
chmod 0700 "$mirror_scripts" "$capture_dir" "$bad_preflight_dir" "$fake_bin"
chmod 0700 "$mirror/artifacts" "$runtime_root"

cp "$requester" "$mirror_scripts/request-native-reboot.sh"
cat >"$mirror_scripts/candidate_ak.py" <<'PY'
PADDED_SHA256 = "1111111111111111111111111111111111111111111111111111111111111111"
AJ_PADDED_SHA256 = "2222222222222222222222222222222222222222222222222222222222222222"
def require_artifact_pins():
    return None
PY
cat >"$mirror_scripts/validate-runtime.py" <<'PY'
#!/usr/bin/env python3
import argparse
import re

PADDED = "1111111111111111111111111111111111111111111111111111111111111111"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def validate(text, expected_hash):
    if expected_hash != PADDED:
        raise ValueError("installed identity changed")
    if len(re.findall(r"(?m)^boot_id=", text)) != 1:
        raise ValueError("runtime boot ID changed")

def section(text, name):
    if name != "IDENTITY":
        raise ValueError("runtime section changed")
    match = re.search(r"(?m)^boot_id=(" + UUID.pattern + r")$", text)
    if match is None:
        raise ValueError("runtime boot ID is absent")
    return "boot_id=" + match.group(1)

def key_values(text, label):
    if label != "runtime identity" or not text.startswith("boot_id="):
        raise ValueError("runtime identity changed")
    return {"boot_id": text.removeprefix("boot_id=")}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    args = parser.parse_args()
    with open(args.capture, encoding="utf-8", newline="") as stream:
        validate(stream.read(), args.expected_installed_full_sha256)
    print("validation=candidate-ak-usb-cpu-runtime-subgate")
PY
cp "$script_dir/validate-native-reboot.py" "$mirror_scripts/validate-native-reboot.py"
cat >"$capture_dir/runtime.txt" <<EOF
__AK_HOST_BEGIN__
interface=en7
__AK_HOST_END__
boot_id=$boot_id
EOF
chmod 0600 "$capture_dir/runtime.txt"
cp "$capture_dir/runtime.txt" "$bad_preflight_dir/runtime.txt"
chmod 0600 "$bad_preflight_dir/runtime.txt"

candidate_sha="$(shasum -a 256 "$mirror_scripts/candidate_ak.py" | awk '{ print $1 }')"
runtime_sha="$(shasum -a 256 "$mirror_scripts/validate-runtime.py" | awk '{ print $1 }')"
python3 - "$mirror_scripts/validate-native-reboot.py" "$candidate_sha" "$runtime_sha" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
for name, value in (
    ("CANDIDATE_AK_SHA256", sys.argv[2]),
    ("RUNTIME_VALIDATOR_SHA256", sys.argv[3]),
):
    pattern = rf'(?m)^{name} = "[^"]+"$'
    text, count = re.subn(pattern, f'{name} = "{value}"', text)
    if count != 1:
        raise RuntimeError(f"unexpected native-validator assignment count: {name}")
path.write_text(text)
PY
native_sha="$(shasum -a 256 "$mirror_scripts/validate-native-reboot.py" | awk '{ print $1 }')"
python3 - "$mirror_scripts/request-native-reboot.sh" "$padded" "$candidate_sha" "$runtime_sha" "$native_sha" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
replacements = {
    "INSTALLED_FULL_SHA256": sys.argv[2],
    "CANDIDATE_AK_SHA256": sys.argv[3],
    "RUNTIME_VALIDATOR_SHA256": sys.argv[4],
    "NATIVE_VALIDATOR_SHA256": sys.argv[5],
}
for name, value in replacements.items():
    pattern = rf"(?m)^readonly {name}=\S+$"
    text, count = re.subn(pattern, f"readonly {name}={value}", text)
    if count != 1:
        raise RuntimeError(f"unexpected requester assignment count: {name}")
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
	if [ ! -e "$AK_REQUEST_DISCONNECTED" ]; then
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
printf '%s\n' "$*" >"$AK_REQUEST_NC_ARGS"
cat >"$AK_REQUEST_REMOTE_COMMAND"
test "$(grep -c '^/bin/reboot$' "$AK_REQUEST_REMOTE_COMMAND")" = 1
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC\n'
printf 'Direct USB link only: device 10.15.19.82/24, TCP port 2323.\n'
printf 'Security: unauthenticated and unencrypted root shell; trusted host only.\n'
printf 'Candidate AC status follows:\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC entry profile=usb-gadget-ethernet baseline=candidate-AB storage_access=none runtime_networking=usb0-static\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb0=present wait_seconds=0\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC services=launched usb_network=background worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 local_console=unchanged watchdog_userspace=none\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb0=configured address=10.15.19.82/24 operstate=down carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC service=nc status=listening address=10.15.19.82 port=2323 shell=/bin/usb-shell authentication=none encryption=none direct_link_only=yes\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=session-entry usb0_operstate=up usb0_carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=session-entry usb0_operstate=up usb0_carrier=1 udc=11271000.usb udc_state=configured\n'
printf 'GEMINI_USB_GADGET_ETHERNET_20260721_AC usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes\n'
printf '\n\n'
printf 'BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1) built-in shell (ash)\n'
printf "Enter 'help' for a list of built-in commands.\n"
printf '\n'
printf 'GEMINI-AC-USB# __AK_NATIVE_REQUEST_BEGIN__\n'
printf 'GEMINI-AC-USB# candidate_boot_id=01234567-89ab-cdef-0123-456789abcdef\n'
printf 'GEMINI-AC-USB# live_boot_id=01234567-89ab-cdef-0123-456789abcdef\n'
printf 'GEMINI-AC-USB# reboot_sha256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7\n'
printf 'GEMINI-AC-USB# reboot_dispatch=/bin/reboot\n'
printf 'GEMINI-AC-USB# reboot_method=/bin/busybox reboot -n -f\n'
printf 'GEMINI-AC-USB# > > > > request_authorized=yes\n'
printf 'GEMINI-AC-USB# storage_access=none\n'
printf 'GEMINI-AC-USB# sync_requested=no\n'
printf 'GEMINI-AC-USB# watchdog_userspace=none\n'
printf 'GEMINI-AC-USB# request_count=1\n'
printf 'GEMINI-AC-USB# __AK_NATIVE_REQUEST_END__\n'
printf 'GEMINI-AC-USB# Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
: >"$AK_REQUEST_DISCONNECTED"
EOF
chmod 0700 "$fake_bin"/*

export AK_REQUEST_DISCONNECTED="$control/disconnected"
export AK_REQUEST_NC_ARGS="$control/nc-args"
export AK_REQUEST_REMOTE_COMMAND="$control/remote-command"

# The checked-in production requester must reject this non-AK identity before
# even a mocked transport command. In the scaffold this is the unresolved-pin
# gate; after calibration it is the exact installed-identity gate.
set +e
PATH="$fake_bin:$PATH" bash "$requester" \
	--runtime-capture "$capture_dir/runtime.txt" \
	--output "$capture_dir/production-native-reboot.txt" \
	--installed-full-sha256 "$padded" \
	>"$control/unresolved.stdout" 2>"$control/unresolved.stderr"
unresolved_rc=$?
set -e
((unresolved_rc == 2)) || die "unresolved production exit was $unresolved_rc"
if grep -q 'TO_PIN_AFTER_' "$requester"; then
	grep -q 'production pins remain unresolved' "$control/unresolved.stderr" || die 'unresolved pin refusal changed'
	production_pins=unresolved
else
	grep -Eq 'installed checksum is not Candidate AK|production artifact pins are unresolved or invalid' "$control/unresolved.stderr" || die 'calibrated identity refusal changed'
	production_pins=calibrated
fi
[[ ! -e "$AK_REQUEST_NC_ARGS" ]] || die 'unresolved production requester reached nc'

# A source-pinned but internally wrong runtime dependency must be caught by the
# real native validator's preflight before nc consumes the hardware boot.
cp "$mirror_scripts/validate-native-reboot.py" "$control/native-validator-good.py"
cp "$mirror_scripts/request-native-reboot.sh" "$mirror_scripts/request-native-reboot-bad-preflight.sh"
python3 - "$mirror_scripts/validate-native-reboot.py" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
text, count = re.subn(
    r'(?m)^RUNTIME_VALIDATOR_SHA256 = "[0-9a-f]{64}"$',
    f'RUNTIME_VALIDATOR_SHA256 = "{"0" * 64}"',
    text,
)
if count != 1:
    raise RuntimeError("native-validator dependency assignment changed")
path.write_text(text)
PY
bad_native_sha="$(shasum -a 256 "$mirror_scripts/validate-native-reboot.py" | awk '{ print $1 }')"
python3 - "$mirror_scripts/request-native-reboot-bad-preflight.sh" "$bad_native_sha" <<'PY'
import pathlib
import re
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
text, count = re.subn(
    r"(?m)^readonly NATIVE_VALIDATOR_SHA256=\S+$",
    f"readonly NATIVE_VALIDATOR_SHA256={sys.argv[2]}",
    text,
)
if count != 1:
    raise RuntimeError("requester native-validator assignment changed")
path.write_text(text)
PY
set +e
PATH="$fake_bin:$PATH" bash "$mirror_scripts/request-native-reboot-bad-preflight.sh" \
	--runtime-capture "$bad_preflight_dir/runtime.txt" \
	--output "$bad_preflight_dir/native-reboot.txt" \
	--installed-full-sha256 "$padded" \
	>"$control/bad-preflight.stdout" 2>"$control/bad-preflight.stderr"
bad_preflight_rc=$?
set -e
((bad_preflight_rc == 2)) || die "bad native dependency preflight exit was $bad_preflight_rc"
grep -q 'native reboot validator preflight rejected' "$control/bad-preflight.stderr" || {
	cat "$control/bad-preflight.stderr" >&2
	die 'bad native dependency escaped preflight'
}
[[ ! -e "$AK_REQUEST_NC_ARGS" ]] || die 'bad native dependency reached nc'
[[ ! -e "$bad_preflight_dir/native-reboot.txt" ]] || die 'bad native dependency created reboot evidence'
cp "$control/native-validator-good.py" "$mirror_scripts/validate-native-reboot.py"

PATH="$fake_bin:$PATH" bash "$mirror_scripts/request-native-reboot.sh" \
	--runtime-capture "$capture_dir/runtime.txt" \
	--output "$capture_dir/native-reboot.txt" \
	--installed-full-sha256 "$padded" \
	>"$control/calibrated.stdout" 2>"$control/calibrated.stderr" || {
		cat "$control/calibrated.stderr" >&2
		die 'calibrated mocked request failed'
	}

[[ -f "$capture_dir/native-reboot.txt" && ! -L "$capture_dir/native-reboot.txt" ]] || die 'mocked native reboot evidence is absent'
mode="$(stat -f '%Lp' "$capture_dir/native-reboot.txt" 2>/dev/null || stat -c '%a' "$capture_dir/native-reboot.txt")"
[[ "$mode" == 600 ]] || die "native reboot evidence mode is $mode"
grep -q -- '-4 -b en7 -s 10.15.19.1' "$AK_REQUEST_NC_ARGS" || die 'nc was not interface/source bound'
[[ "$(grep -c '^/bin/reboot$' "$AK_REQUEST_REMOTE_COMMAND")" == 1 ]] || die 'exact reboot dispatch count changed'
grep -Fq "/proc/sys/kernel/random/boot_id" "$AK_REQUEST_REMOTE_COMMAND" || die 'fresh boot-ID gate disappeared'
grep -Fq "sha256sum /bin/reboot" "$AK_REQUEST_REMOTE_COMMAND" || die 'reboot wrapper hash gate disappeared'
grep -q '^native_runtime_preflight=candidate-ak-native-reboot-preflight$' "$capture_dir/native-reboot.txt" || die 'real native-validator preflight was not recorded'
if grep -Eq '(/dev/mmc|\bdd\b|flash|mkfs|mount |/dev/watchdog|sync$)' "$AK_REQUEST_REMOTE_COMMAND"; then
	die 'native reboot remote command gained storage or watchdog access'
fi

printf 'validation=candidate-ak-native-reboot-request-mocked\n'
printf 'production_pins=%s\nsynthetic_non_ak_request_reached_transport=no\n' "$production_pins"
printf 'bad_native_dependency_reached_transport=no\nreal_native_validator_preflight=passed\n'
printf 'fresh_runtime_boot_id_gate=passed\nvalid_exact_reboot_dispatches=1\n'
printf 'transport=mocked\ndevice_partition_reads=none\ndevice_write_operations=none\ndevice_access=none\n'
