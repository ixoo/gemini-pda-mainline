#!/usr/bin/env bash

# Issue exactly one inherited native reboot only after a source-pinned AL
# runtime capture validates and the same live boot ID remains on exact USB.

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7
readonly RUNTIME_VALIDATOR_SHA256=7fb5beb2ca4ba48fb7de6650ad0e810c5ce58f5bc8ad19beb9f476dbea2c87e0

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --runtime-capture FILE --output NEW_FILE --installed-full-sha256 SHA256\n' "$0" >&2
}

runtime_capture=
output=
installed_full_sha256=
while (($#)); do
	case "$1" in
	--runtime-capture|--output|--installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--runtime-capture) [[ -z "$runtime_capture" ]] || die '--runtime-capture duplicated'; runtime_capture=$2 ;;
		--output) [[ -z "$output" ]] || die '--output duplicated'; output=$2 ;;
		--installed-full-sha256) [[ -z "$installed_full_sha256" ]] || die '--installed-full-sha256 duplicated'; installed_full_sha256=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown option: $1" ;;
	esac
done
[[ -n "$runtime_capture" && -n "$output" ]] || { usage >&2; exit 2; }
[[ "$runtime_capture$output" != *$'\n'* ]] || die 'paths must be single-line values'
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'installed checksum must be one lowercase SHA-256 value'
[[ "$RUNTIME_VALIDATOR_SHA256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'runtime validator production identity remains unresolved'
for command in awk basename cat chmod date dirname git grep ifconfig mktemp nc \
	ping python3 rm route shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$script_dir/candidate_al.py"
validator="$script_dir/validate-runtime.py"
for input in "$identity" "$validator"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "native reboot input missing or unsafe: $input"
done
[[ "$(shasum -a 256 "$validator" | awk '{ print $1 }')" == \
	"$RUNTIME_VALIDATOR_SHA256" ]] || die 'Candidate AL runtime validator changed'
pinned_full_sha256="$(python3 - "$identity" <<'PY'
import importlib.util
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_al_reboot_pins", path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Candidate AL identity")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.require_artifact_pins()
print(module.PADDED_SHA256)
PY
)" || die 'Candidate AL production artifact pins are unresolved or invalid'
[[ "$installed_full_sha256" == "$pinned_full_sha256" ]] || \
	die 'installed full-partition checksum is not Candidate AL'

file_mode() { stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"; }
private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" && "$(file_mode "$private_root")" == 700 ]] || \
	die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$runtime_capture" in /*) ;; *) runtime_capture="$repo_root/${runtime_capture#./}" ;; esac
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$runtime_capture")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" && \
	"$(basename -- "$capture_dir")" == candidate-al-* ]] || \
	die 'runtime capture is not one Candidate AL private child'
[[ "$(basename -- "$runtime_capture")" == runtime.txt ]] || \
	die 'runtime capture must be that Candidate AL child runtime.txt'
[[ "$(dirname -- "$output")" == "$capture_dir" && \
	"$(basename -- "$output")" == native-reboot.txt ]] || \
	die 'output must be that Candidate AL child native-reboot.txt'
[[ -d "$capture_dir" && ! -L "$capture_dir" && "$(file_mode "$capture_dir")" == 700 ]] || \
	die 'Candidate AL runtime directory is unsafe'
capture_dir="$(cd -- "$capture_dir" && pwd -P)"
runtime_capture="$capture_dir/runtime.txt"
output="$capture_dir/native-reboot.txt"
[[ -f "$runtime_capture" && ! -L "$runtime_capture" && \
	"$(file_mode "$runtime_capture")" == 600 ]] || die 'runtime capture is absent or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite native reboot evidence'
git -C "$repo_root" check-ignore -q -- "$runtime_capture" || \
	die 'runtime capture is not private under Git ignore policy'
git -C "$repo_root" check-ignore -q -- "$output" || \
	die 'native reboot evidence is not private under Git ignore policy'

validation="$(python3 "$validator" --capture "$runtime_capture" \
	--expected-installed-full-sha256 "$installed_full_sha256")" || \
	die 'runtime capture did not pass exact Candidate AL validation'
printf '%s\n' "$validation" | grep -qx \
	'validation=candidate-al-da9214-resource-only-runtime' || \
	die 'Candidate AL runtime validation label changed'
candidate_boot_id="$(awk '
	{
		line=$0; sub(/\r$/, "", line)
		while (sub(/^GEMINI-AC-USB# /, "", line)) {}
		if (line == "__AL_IDENTITY_BEGIN__") inside=1
		else if (line == "__AL_IDENTITY_END__") inside=0
		else if (inside && line ~ /^boot_id=/) {
			print substr(line, 9); count++
		}
	}
	END { exit count != 1 }
' "$runtime_capture")" || die 'validated Candidate AL boot ID is absent or duplicated'
[[ "$candidate_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || \
	die 'validated Candidate AL boot ID is malformed'
interface="$(awk '
	$0 == "__AL_HOST_BEGIN__" { inside=1; next }
	$0 == "__AL_HOST_END__" { inside=0 }
	inside && /^interface=/ { print substr($0, 11); count++ }
	END { exit count != 1 }
' "$runtime_capture")" || die 'validated runtime interface is absent or duplicated'
[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || die 'validated interface is malformed'

mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); count++ } END { exit count != 1 }')"
[[ "$mac" == "$HOST_MAC" ]] || die 'validated interface no longer has the exact Gemini MAC'
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found++ } END { exit found != 1 }' || \
	die 'exact host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not exact USB'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded exact-USB ping failed'

command_file="$(mktemp /tmp/candidate-al-native-reboot.XXXXXX)"
cleanup() { [[ ! -f "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<EOF
live_boot_id=\$(/bin/busybox cat /proc/sys/kernel/random/boot_id) || exit 91
live_reboot_sha256=\$(/bin/busybox sha256sum /bin/reboot | /bin/busybox awk '{ print \$1 }') || exit 92
printf '__AL_NATIVE_REQUEST_BEGIN__\\n'
printf 'candidate_boot_id=%s\\n' '$candidate_boot_id'
printf 'live_boot_id=%s\\n' "\$live_boot_id"
printf 'reboot_sha256=%s\\n' "\$live_reboot_sha256"
printf 'reboot_dispatch=/bin/reboot\\n'
printf 'request_count=1\\n'
printf 'storage_access=none\\n'
printf 'watchdog_userspace=none\\n'
if [ "\$live_boot_id" = '$candidate_boot_id' ] && [ "\$live_reboot_sha256" = '$REBOOT_SHA256' ]; then
	printf 'request_authorized=yes\\n'
else
	printf 'request_authorized=no\\n'
fi
printf '__AL_NATIVE_REQUEST_END__\\n'
if [ "\$live_boot_id" != '$candidate_boot_id' ] || [ "\$live_reboot_sha256" != '$REBOOT_SHA256' ]; then
	exit 93
fi
/bin/reboot
printf '__AL_NATIVE_REBOOT_RETURNED__\\n'
exit 94
EOF

{
	printf '__AL_NATIVE_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'runtime_capture_sha256=%s\n' "$(shasum -a 256 "$runtime_capture" | awk '{ print $1 }')"
	printf 'candidate_boot_id=%s\ninterface=%s\nmac=%s\n' \
		"$candidate_boot_id" "$interface" "$mac"
	printf 'host_address=%s/24\nroute_interface=%s\n' "$HOST_ADDRESS" "$route_interface"
	printf 'device_endpoint=%s:%s\nstorage_access=none\n' "$DEVICE_ADDRESS" "$DEVICE_PORT"
	printf '__AL_NATIVE_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
grep -q '__AL_NATIVE_REBOOT_RETURNED__' "$output" && \
	die 'native reboot wrapper returned unexpectedly'
grep -Eq '^(GEMINI-AC-USB# )*request_authorized=yes\r?$' "$output" || \
	die 'live boot ID/reboot hash gate did not authorize the request'

mac_present() {
	ifconfig -a | awk -v wanted="$HOST_MAC" \
		'/^[[:space:]]*ether / && tolower($2) == wanted { found=1 } END { exit !found }'
}
deadline=$(( $(date +%s) + 30 ))
while mac_present && (( $(date +%s) < deadline )); do sleep 1; done
mac_present && die 'exact Gemini USB MAC did not disappear after reboot request'
sleep 1
mac_present && die 'exact Gemini USB MAC absence was not stable'
{
	printf '__AL_NATIVE_RESULT_BEGIN__\n'
	printf 'nc_exit_status=%s\nconnection_closed_after_request=yes\n' "$nc_status"
	printf 'mac_absence_observation_1=absent\nmac_absence_observation_2=absent\n'
	printf 'disconnect_confirmed=yes\nrequestor_reboot_command_issued=yes\n'
	printf 'device_partition_reads=none\ndevice_write_operations=none\n'
	printf '__AL_NATIVE_RESULT_END__\n'
} >>"$output"
printf 'validation=candidate-al-native-reboot-request\n'
printf 'capture=%s\ncandidate_boot_id=%s\ndisconnect_confirmed=yes\n' \
	"$output" "$candidate_boot_id"
