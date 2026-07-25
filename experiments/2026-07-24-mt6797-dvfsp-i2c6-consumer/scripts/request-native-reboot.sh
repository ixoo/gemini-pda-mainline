#!/usr/bin/env bash

# Invoke AP's inherited /bin/reboot exactly once, but only after the final,
# source-pinned AP runtime validator proves the explicitly selected PASS or
# fail-closed FAIL capture whose boot ID is linked to the final source-pinned
# private live-FDT identity.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7
readonly INSTALLED_FULL_SHA256=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9

# Calibrated together after the AP identity, runtime validator/collector, and
# private-live-FDT validator became final. The syntax gate still precedes
# source, capture, host, and device probes.
readonly CANDIDATE_AP_SHA256=c17ceffbd015f1ed7dca2e6d170839a2c4f0df38c921ee87f8806643c3132914
readonly RUNTIME_VALIDATOR_SHA256=ea426aadb4a7bc9b47d3d11baa71a5f61545ebf803eeb51cf078753b62ef2ffe
readonly LIVE_FDT_VALIDATOR_SHA256=b8511f4543b2b683971ea60f84fa1f1d064b9c151eead7f9fc0c4d5921776a4a
readonly NATIVE_VALIDATOR_SHA256=d8f0e148bab6e8b51b151099b6dadcd264ae6a4d2d2f505e19bb6e83eccc452c

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --runtime-capture PATH --output NEW_FILE --installed-full-sha256 SHA256 --expected-runtime-outcome PASS|FAIL\n' "$0" >&2
}
is_sha256() { [[ "$1" =~ ^[0-9a-f]{64}$ ]]; }

runtime_capture=
output=
installed_full_sha256=
expected_runtime_outcome=
while (($#)); do
	case "$1" in
	--runtime-capture|--output|--installed-full-sha256|--expected-runtime-outcome)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--runtime-capture)
			[[ -z "$runtime_capture" ]] || die '--runtime-capture was provided more than once'
			runtime_capture=$2
			;;
		--output)
			[[ -z "$output" ]] || die '--output was provided more than once'
			output=$2
			;;
		--installed-full-sha256)
			[[ -z "$installed_full_sha256" ]] || die '--installed-full-sha256 was provided more than once'
			installed_full_sha256=$2
			;;
		--expected-runtime-outcome)
			[[ -z "$expected_runtime_outcome" ]] || \
				die '--expected-runtime-outcome was provided more than once'
			expected_runtime_outcome=$2
			;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ -n "$runtime_capture" && -n "$output" && -n "$installed_full_sha256" && \
	-n "$expected_runtime_outcome" ]] || {
	usage
	exit 2
}
[[ "$expected_runtime_outcome" == PASS || \
	"$expected_runtime_outcome" == FAIL ]] || \
	die 'expected runtime outcome must be PASS or FAIL'
[[ "$runtime_capture" != *$'\n'* && "$output" != *$'\n'* ]] || \
	die 'paths must be single-line values'
for pin in "$CANDIDATE_AP_SHA256" "$RUNTIME_VALIDATOR_SHA256" \
	"$LIVE_FDT_VALIDATOR_SHA256" "$NATIVE_VALIDATOR_SHA256"; do
	is_sha256 "$pin" || \
		die 'Candidate AP native-reboot production source pins remain unresolved'
done
is_sha256 "$installed_full_sha256" || \
	die 'installed checksum must be one lowercase SHA-256 value'
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || \
	die 'installed checksum is not Candidate AP'

for command in awk basename cat chmod date dirname git grep ifconfig mktemp nc \
	ping python3 rm route shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
candidate_identity="$script_dir/candidate_ap.py"
runtime_validator="$script_dir/validate-runtime.py"
live_fdt_validator="$script_dir/validate-live-fdt-delta.py"
native_validator="$script_dir/validate-native-reboot.py"
readonly script_dir repo_root candidate_identity runtime_validator
readonly live_fdt_validator native_validator

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }
require_source() {
	local path=$1
	local expected=$2
	local label=$3
	[[ -f "$path" && ! -L "$path" ]] || die "$label is absent or unsafe"
	[[ "$(file_sha256 "$path")" == "$expected" ]] || die "$label source changed"
}

# Bottom-up source pins precede evidence-path inspection and every host/device
# probe. There is no testing override in this production requester.
require_source "$candidate_identity" "$CANDIDATE_AP_SHA256" \
	'Candidate AP identity'
require_source "$runtime_validator" "$RUNTIME_VALIDATOR_SHA256" \
	'runtime validator'
require_source "$live_fdt_validator" "$LIVE_FDT_VALIDATOR_SHA256" \
	'live-FDT validator'
require_source "$native_validator" "$NATIVE_VALIDATOR_SHA256" \
	'native reboot validator'

pinned_config_sha256="$(python3 - "$candidate_identity" "$INSTALLED_FULL_SHA256" <<'PY'
import importlib.util
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("ap_native_request_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AP identity module")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
if module.PADDED_SHA256 != sys.argv[2]:
    raise RuntimeError("Candidate AP padded identity changed")
if module.PADDED_SHA256 == module.AO_PADDED_SHA256:
    raise RuntimeError("Candidate AP padded identity equals Candidate AO")
if re.fullmatch(r"[0-9a-f]{64}", module.CONFIG_SHA256) is None:
    raise RuntimeError("Candidate AP configuration identity is malformed")
print(module.CONFIG_SHA256)
PY
)" || die 'Candidate AP production artifact pins are unresolved or invalid'
is_sha256 "$pinned_config_sha256" || die 'Candidate AP configuration pin changed'

artifacts_root="$repo_root/artifacts"
[[ -d "$artifacts_root" && ! -L "$artifacts_root" ]] || \
	die 'artifacts root is absent or unsafe'
[[ "$(file_mode "$artifacts_root")" == 700 ]] || \
	die 'artifacts root mode is not 0700'
artifacts_root="$(cd -- "$artifacts_root" && pwd -P)"
[[ "$artifacts_root" == "$repo_root/artifacts" ]] || \
	die 'artifacts root contains an intermediate symlink'
private_root="$artifacts_root/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || \
	die 'private runtime-capture root is absent or unsafe'
[[ "$(file_mode "$private_root")" == 700 ]] || \
	die 'private runtime-capture root mode is not 0700'
private_root="$(cd -- "$private_root" && pwd -P)"

case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || \
	die '--runtime-capture filename must be runtime.txt'
capture_dir="$(dirname -- "$runtime_capture")"
[[ "$(basename -- "$capture_dir")" == candidate-ap-* ]] || \
	die 'runtime capture directory is not Candidate AP'
[[ "$(basename -- "$output")" == native-reboot.txt && \
	"$(dirname -- "$output")" == "$capture_dir" ]] || \
	die '--output must be native-reboot.txt beside the runtime capture'
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || \
	die 'runtime capture is not in one direct private child'
[[ -d "$capture_dir" && ! -L "$capture_dir" ]] || \
	die 'runtime capture directory is unsafe'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
[[ "$(dirname -- "$capture_dir")" == "$private_root" && \
	"$(file_mode "$capture_dir")" == 700 ]] || \
	die 'runtime capture directory escaped or is not mode 0700'
runtime_capture="$capture_dir/runtime.txt"
output="$capture_dir/native-reboot.txt"
[[ -f "$runtime_capture" && ! -L "$runtime_capture" && \
	"$(file_mode "$runtime_capture")" == 600 ]] || \
	die 'runtime capture is absent or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite native reboot evidence'
git -C "$repo_root" check-ignore -q -- "$runtime_capture" || \
	die 'runtime capture is not private under Git ignore policy'
git -C "$repo_root" check-ignore -q -- "$output" || \
	die 'native reboot evidence is not private under Git ignore policy'

native_preflight="$(python3 "$native_validator" --preflight-runtime \
	--runtime-capture "$runtime_capture" \
	--expected-installed-full-sha256 "$installed_full_sha256" \
	--expected-runtime-outcome "$expected_runtime_outcome")" || \
	die 'native reboot validator preflight rejected the exact AP runtime'
preflight_keys="$(printf '%s\n' "$native_preflight" | \
	awk -F= '{ if (NR > 1) printf ","; printf "%s", $1 } END { print "" }')"
expected_preflight_keys='validation,candidate_boot_id,runtime_capture_sha256,interface,live_fdt_sha256,live_fdt_size,candidate_identity_source_sha256,runtime_validator_source_sha256,live_fdt_validator_source_sha256,runtime_outcome,exact_runtime_boot_id_and_live_fdt_binding,device_access'
[[ "$preflight_keys" == "$expected_preflight_keys" ]] || \
	die 'native reboot preflight output inventory changed'
preflight_value() {
	printf '%s\n' "$native_preflight" | awk -F= -v key="$1" '
		$1 == key { print substr($0, length($1) + 2); count++ }
		END { exit count != 1 }
	'
}
[[ "$(preflight_value validation)" == candidate-ap-native-reboot-preflight ]] || \
	die 'native reboot preflight label changed'
candidate_boot_id="$(preflight_value candidate_boot_id)" || \
	die 'native reboot preflight boot ID is absent or duplicated'
runtime_sha256="$(preflight_value runtime_capture_sha256)" || \
	die 'native reboot preflight runtime hash is absent or duplicated'
interface="$(preflight_value interface)" || \
	die 'native reboot preflight interface is absent or duplicated'
live_fdt_sha256="$(preflight_value live_fdt_sha256)" || \
	die 'native reboot preflight live-FDT hash is absent or duplicated'
live_fdt_size="$(preflight_value live_fdt_size)" || \
	die 'native reboot preflight live-FDT size is absent or duplicated'
[[ "$candidate_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]] || \
	die 'validated runtime boot ID is malformed'
[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || \
	die 'validated runtime interface is malformed'
[[ "$runtime_sha256" == "$(file_sha256 "$runtime_capture")" ]] || \
	die 'native reboot preflight runtime hash differs from the capture'
[[ "$(preflight_value candidate_identity_source_sha256)" == \
	"$CANDIDATE_AP_SHA256" ]] || die 'preflight Candidate AP source pin changed'
[[ "$(preflight_value runtime_validator_source_sha256)" == \
	"$RUNTIME_VALIDATOR_SHA256" ]] || die 'preflight runtime source pin changed'
[[ "$(preflight_value live_fdt_validator_source_sha256)" == \
	"$LIVE_FDT_VALIDATOR_SHA256" ]] || die 'preflight live-FDT source pin changed'
[[ "$(preflight_value runtime_outcome)" == "$expected_runtime_outcome" ]] || \
	die 'native reboot preflight runtime outcome differs from the requested result'
[[ "$(preflight_value exact_runtime_boot_id_and_live_fdt_binding)" == passed ]] || \
	die 'native reboot preflight did not bind runtime to live FDT'
[[ "$(preflight_value device_access)" == none ]] || \
	die 'native reboot preflight unexpectedly accessed the device'
is_sha256 "$live_fdt_sha256" || die 'preflight live-FDT hash is malformed'
[[ "$live_fdt_size" =~ ^[1-9][0-9]*$ ]] || \
	die 'preflight live-FDT size is malformed'

mac="$(ifconfig "$interface" | \
	awk '/^[[:space:]]*ether / { print tolower($2); count++ } END { exit count != 1 }')"
[[ "$mac" == "$HOST_MAC" ]] || \
	die 'validated runtime interface no longer has the exact Gemini MAC'
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found++ } END { exit found != 1 }' || \
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || \
	die 'device route is not the validated USB interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded direct-USB ping failed'

command_file="$(mktemp /tmp/candidate-ap-native-reboot-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<EOF
live_boot_id=\$(/bin/busybox cat /proc/sys/kernel/random/boot_id) || exit 91
live_reboot_sha256=\$(/bin/busybox sha256sum /bin/reboot | /bin/busybox awk '{ print \$1 }') || exit 92
printf '__AP_NATIVE_REQUEST_BEGIN__\\n'
printf 'candidate_boot_id=%s\\n' '$candidate_boot_id'
printf 'live_boot_id=%s\\n' "\$live_boot_id"
printf 'reboot_sha256=%s\\n' "\$live_reboot_sha256"
printf 'reboot_dispatch=/bin/reboot\\n'
printf 'reboot_method=/bin/busybox reboot -n -f\\n'
if [ "\$live_boot_id" = '$candidate_boot_id' ] && [ "\$live_reboot_sha256" = '$REBOOT_SHA256' ]; then
	printf 'request_authorized=yes\\n'
else
	printf 'request_authorized=no\\n'
fi
printf 'storage_access=none\\n'
printf 'device_partition_reads=none\\n'
printf 'watchdog_access=none\\n'
printf 'i2c_access=none\\n'
printf 'regulator_access=none\\n'
printf 'cpu_control_access=none\\n'
printf 'power_state_access=none\\n'
printf 'sync_requested=no\\n'
printf 'request_count=1\\n'
printf '__AP_NATIVE_REQUEST_END__\\n'
if [ "\$live_boot_id" != '$candidate_boot_id' ] || [ "\$live_reboot_sha256" != '$REBOOT_SHA256' ]; then
	exit 93
fi
/bin/reboot
printf '__AP_NATIVE_REBOOT_RETURNED__\\n'
exit 94
EOF

{
	printf '__AP_NATIVE_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'installed_full_hash_reverified_during_request=no\n'
	printf 'device_partition_read_during_request=no\n'
	printf 'runtime_capture_sha256=%s\n' "$runtime_sha256"
	printf 'runtime_validation=candidate-ap-mt6797-dvfsp-i2c6-consumer-runtime\n'
	printf 'runtime_outcome=%s\n' "$expected_runtime_outcome"
	printf 'runtime_boot_id=%s\n' "$candidate_boot_id"
	printf 'candidate_identity_source_sha256=%s\n' "$CANDIDATE_AP_SHA256"
	printf 'runtime_validator_source_sha256=%s\n' "$RUNTIME_VALIDATOR_SHA256"
	printf 'live_fdt_validator_source_sha256=%s\n' "$LIVE_FDT_VALIDATOR_SHA256"
	printf 'live_fdt_sha256=%s\n' "$live_fdt_sha256"
	printf 'live_fdt_size=%s\n' "$live_fdt_size"
	printf 'native_runtime_preflight=candidate-ap-native-reboot-preflight\n'
	printf 'direct_usb_binding=yes\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' \
		"$interface" "$mac" "$HOST_ADDRESS"
	printf 'route_interface=%s\ndevice_endpoint=%s:%s\n' \
		"$route_interface" "$DEVICE_ADDRESS" "$DEVICE_PORT"
	printf 'storage_access=none\nwatchdog_access=none\ni2c_access=none\n'
	printf 'regulator_access=none\ncpu_control_access=none\n'
	printf 'power_state_access=none\n__AP_NATIVE_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_exit_status=$?
set -e
grep -q '__AP_NATIVE_REBOOT_RETURNED__' "$output" && \
	die 'native reboot wrapper returned unexpectedly'
grep -Eq '^(GEMINI-AC-USB# )*request_authorized=no\r?$' "$output" && \
	die 'live boot ID or reboot wrapper hash gate refused the request'

mac_present() {
	local inventory
	inventory="$(ifconfig -a)" || \
		die 'host interface enumeration failed during disconnect observation'
	printf '%s\n' "$inventory" | awk -v wanted="$HOST_MAC" '
		/^[[:space:]]*ether / && tolower($2) == wanted { found=1 }
		END { exit !found }
	'
}
deadline=$(( $(date +%s) + 30 ))
while mac_present && (( $(date +%s) < deadline )); do sleep 1; done
mac_present && \
	die 'exact Gemini USB MAC did not disappear after native reboot request'
sleep 1
mac_present && \
	die 'exact Gemini USB MAC absence was not stable across two observations'
{
	printf '__AP_NATIVE_RESULT_BEGIN__\n'
	printf 'nc_exit_status=%s\n' "$nc_exit_status"
	printf 'connection_closed_after_request=yes\n'
	printf 'return_marker_observed=no\n'
	printf 'mac_absence_observation_1=absent\n'
	printf 'mac_absence_observation_2=absent\n'
	printf 'disconnect_confirmed=yes\n'
	printf 'requestor_reboot_command_issued=yes\n'
	printf 'device_partition_reads=none\n'
	printf 'device_write_operations=none\n'
	printf 'watchdog_access=none\ni2c_access=none\nregulator_access=none\n'
	printf 'cpu_control_access=none\npower_state_access=none\n'
	printf '__AP_NATIVE_RESULT_END__\n'
} >>"$output"

python3 "$native_validator" --capture "$output" \
	--runtime-capture "$runtime_capture" \
	--expected-installed-full-sha256 "$installed_full_sha256" \
	--expected-runtime-outcome "$expected_runtime_outcome"
printf 'capture=%s\n' "$output"
