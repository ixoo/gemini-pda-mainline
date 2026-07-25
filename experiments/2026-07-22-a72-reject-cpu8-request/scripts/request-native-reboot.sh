#!/usr/bin/env bash

# Invoke AJ's inherited /bin/reboot exactly once, but only when a separately
# validated runtime capture names the boot ID currently served over USB.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly INSTALLED_FULL_SHA256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
readonly REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7
readonly CANDIDATE_AJ_SHA256=77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1
readonly RUNTIME_VALIDATOR_SHA256=e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089
readonly NATIVE_VALIDATOR_SHA256=c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --runtime-capture PATH --output NEW_FILE --installed-full-sha256 SHA256\n' "$0" >&2
}

runtime_capture=
output=
installed_full_sha256=
while (($#)); do
	case "$1" in
	--runtime-capture|--output|--installed-full-sha256)
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
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ -n "$runtime_capture" && -n "$output" ]] || { usage; exit 2; }
[[ "$runtime_capture" != *$'\n'* && "$output" != *$'\n'* ]] || die 'paths must be single-line values'
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || die 'installed checksum must be one lowercase SHA-256 value'
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'installed checksum is not Candidate AJ'
for command in awk basename cat chmod date dirname git grep ifconfig mktemp nc ping \
	python3 rm route shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
candidate_identity="$script_dir/candidate_aj.py"
runtime_validator="$script_dir/validate-runtime.py"
native_validator="$script_dir/validate-native-reboot.py"
readonly script_dir repo_root candidate_identity runtime_validator native_validator

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
file_sha256() { shasum -a 256 "$1" | awk '{ print $1 }'; }

# Bottom-up source pins precede evidence-path inspection and all host/device probes.
[[ -f "$candidate_identity" && ! -L "$candidate_identity" ]] || die 'Candidate AJ identity source is absent or unsafe'
[[ "$(file_sha256 "$candidate_identity")" == "$CANDIDATE_AJ_SHA256" ]] || die 'Candidate AJ identity source changed'
[[ -f "$runtime_validator" && ! -L "$runtime_validator" ]] || die 'runtime validator is absent or unsafe'
[[ "$(file_sha256 "$runtime_validator")" == "$RUNTIME_VALIDATOR_SHA256" ]] || die 'runtime validator source changed'
[[ -f "$native_validator" && ! -L "$native_validator" ]] || die 'native reboot validator is absent or unsafe'
[[ "$(file_sha256 "$native_validator")" == "$NATIVE_VALIDATOR_SHA256" ]] || die 'native reboot validator source changed'

pinned_full_sha256="$(python3 - "$candidate_identity" <<'PY'
import importlib.util
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("aj_native_request_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AJ identity module")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
if (
    module.RAW_SHA256 != "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
    or module.RAW_SIZE != "7380992"
    or module.ARTIFACT_MANIFEST_SHA256 != "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
    or module.PADDED_SHA256 != "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
    or module.AI_PADDED_SHA256 != "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
):
    raise RuntimeError("Candidate AJ/AI artifact identities changed")
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AJ production artifact pins are unresolved or invalid'
[[ "$pinned_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'Candidate AJ padded identity changed'

artifacts_root="$repo_root/artifacts"
[[ -d "$artifacts_root" && ! -L "$artifacts_root" ]] || die 'artifacts root is absent or unsafe'
[[ "$(file_mode "$artifacts_root")" == 700 ]] || die 'artifacts root mode is not 0700'
artifacts_root="$(cd -- "$artifacts_root" && pwd -P)"
[[ "$artifacts_root" == "$repo_root/artifacts" ]] || die 'artifacts root contains an intermediate symlink'
private_root="$artifacts_root/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private runtime-capture root is absent or unsafe'
[[ "$(file_mode "$private_root")" == 700 ]] || die 'private runtime-capture root mode is not 0700'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || die '--runtime-capture filename must be runtime.txt'
capture_dir="$(dirname -- "$runtime_capture")"
[[ "$(basename -- "$output")" == native-reboot.txt && "$(dirname -- "$output")" == "$capture_dir" ]] || die '--output must be native-reboot.txt beside the runtime capture'
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || die 'runtime capture is not in one direct private child'
[[ -d "$capture_dir" && ! -L "$capture_dir" ]] || die 'runtime capture directory is unsafe'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
[[ "$(dirname -- "$capture_dir")" == "$private_root" && "$(file_mode "$capture_dir")" == 700 ]] || die 'runtime capture directory escaped or is not mode 0700'
runtime_capture="$capture_dir/runtime.txt"
output="$capture_dir/native-reboot.txt"
[[ -f "$runtime_capture" && ! -L "$runtime_capture" && "$(file_mode "$runtime_capture")" == 600 ]] || die 'runtime capture is absent or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite native reboot evidence'
git -C "$repo_root" check-ignore -q -- "$runtime_capture" || die 'runtime capture is not private under Git ignore policy'
git -C "$repo_root" check-ignore -q -- "$output" || die 'native reboot evidence is not private under Git ignore policy'

runtime_validation="$(python3 "$runtime_validator" --capture "$runtime_capture" \
	--expected-installed-full-sha256 "$installed_full_sha256")" || die 'runtime capture did not pass exact AJ validation'
printf '%s\n' "$runtime_validation" | grep -qx 'validation=candidate-aj-usb-cpu-runtime-subgate' || die 'runtime validation label changed'
candidate_boot_id="$(awk '
	{
		line=$0; sub(/\r$/, "", line)
		while (sub(/^GEMINI-AC-USB# /, "", line)) {}
		if (line ~ /^boot_id=/) { print substr(line, 9); count++ }
	}
	END { exit count != 1 }
' "$runtime_capture")" || die 'validated runtime boot ID is absent or duplicated'
[[ "$candidate_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || die 'validated runtime boot ID is malformed'
interface="$(awk '
	$0 == "__AJ_HOST_BEGIN__" { inside=1; next }
	$0 == "__AJ_HOST_END__" { inside=0 }
	inside && /^interface=/ { print substr($0, 11); count++ }
	END { exit count != 1 }
' "$runtime_capture")" || die 'validated runtime interface is absent or duplicated'
[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || die 'validated runtime interface is malformed'
runtime_sha256="$(file_sha256 "$runtime_capture")"

mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); count++ } END { exit count != 1 }')"
[[ "$mac" == "$HOST_MAC" ]] || die 'validated runtime interface no longer has the exact Gemini MAC'
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address { found++ } END { exit found != 1 }' || die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the validated USB interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-aj-native-reboot-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<EOF
live_boot_id=\$(/bin/busybox cat /proc/sys/kernel/random/boot_id) || exit 91
live_reboot_sha256=\$(/bin/busybox sha256sum /bin/reboot | /bin/busybox awk '{ print \$1 }') || exit 92
printf '__AJ_NATIVE_REQUEST_BEGIN__\\n'
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
printf 'sync_requested=no\\n'
printf 'watchdog_userspace=none\\n'
printf 'request_count=1\\n'
printf '__AJ_NATIVE_REQUEST_END__\\n'
if [ "\$live_boot_id" != '$candidate_boot_id' ] || [ "\$live_reboot_sha256" != '$REBOOT_SHA256' ]; then
	exit 93
fi
/bin/reboot
printf '__AJ_NATIVE_REBOOT_RETURNED__\\n'
exit 94
EOF

{
	printf '__AJ_NATIVE_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'installed_full_hash_reverified_during_request=no\n'
	printf 'device_partition_read_during_request=no\n'
	printf 'runtime_capture_sha256=%s\n' "$runtime_sha256"
	printf 'runtime_validation=candidate-aj-usb-cpu-runtime-subgate\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$mac" "$HOST_ADDRESS"
	printf 'route_interface=%s\ndevice_endpoint=%s:%s\n' "$route_interface" "$DEVICE_ADDRESS" "$DEVICE_PORT"
	printf 'storage_access=none\n__AJ_NATIVE_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 "$DEVICE_ADDRESS" "$DEVICE_PORT" \
	<"$command_file" >>"$output" 2>&1
nc_exit_status=$?
set -e
grep -q '__AJ_NATIVE_REBOOT_RETURNED__' "$output" && die 'native reboot wrapper returned unexpectedly'
grep -Eq '^(GEMINI-AC-USB# )*request_authorized=no\r?$' "$output" && \
	die 'live boot ID or reboot wrapper hash gate refused the request'

mac_present() {
	local inventory
	inventory="$(ifconfig -a)" || die 'host interface enumeration failed during disconnect observation'
	printf '%s\n' "$inventory" | awk -v wanted="$HOST_MAC" '
		/^[[:space:]]*ether / && tolower($2) == wanted { found=1 }
		END { exit !found }
	'
}
deadline=$(( $(date +%s) + 30 ))
while mac_present && (( $(date +%s) < deadline )); do sleep 1; done
mac_present && die 'exact Gemini USB MAC did not disappear after native reboot request'
sleep 1
mac_present && die 'exact Gemini USB MAC absence was not stable across two observations'
{
	printf '__AJ_NATIVE_RESULT_BEGIN__\n'
	printf 'nc_exit_status=%s\n' "$nc_exit_status"
	printf 'connection_closed_after_request=yes\n'
	printf 'mac_absence_observation_1=absent\nmac_absence_observation_2=absent\n'
	printf 'disconnect_confirmed=yes\nrequestor_reboot_command_issued=yes\n'
	printf 'device_partition_reads=none\ndevice_write_operations=none\n'
	printf '__AJ_NATIVE_RESULT_END__\n'
} >>"$output"

python3 "$native_validator" --capture "$output" --runtime-capture "$runtime_capture" \
	--expected-installed-full-sha256 "$installed_full_sha256"
printf 'capture=%s\n' "$output"
