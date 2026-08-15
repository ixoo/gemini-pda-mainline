#!/usr/bin/env bash

# Wait for the Gemini USB gadget and stream the exact read-only observer probe
# into its netcat shell. Private raw capture remains below ignored artifacts/.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly WAIT_SECONDS=900
readonly PROBE_SHA256=024986cf035866bbc5a865b162aec469484c69ef0ab67b45495c3f65dc6c4e56
readonly CANDIDATE_SHA256=7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --output artifacts/runtime-captures/da921x-readonly-observer-attempt-N/runtime.txt\n' "$0" >&2
}

output=
while (($#)); do
	case "$1" in
	--output)
		(($# >= 2)) || die '--output requires a value'
		[[ -z "$output" ]] || die 'duplicate --output'
		output=$2
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$output" ]] || { usage; exit 2; }

for command in awk base64 basename chmod dirname git grep ifconfig mkdir mktemp \
	nc python3 rm route sha256sum sleep tr; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
probe="$script_dir/remote-runtime-probe.sh"
validator="$script_dir/validate-runtime.py"
[[ -f "$probe" && ! -L "$probe" && -f "$validator" && ! -L "$validator" ]] ||
	die 'runtime probe or validator is missing or unsafe'
[[ "$(sha256sum "$probe" | awk '{print $1}')" == "$PROBE_SHA256" ]] ||
	die 'runtime probe identity changed'

private_root="$repo_root/artifacts/runtime-captures"
[[ -d "$private_root" && ! -L "$private_root" ]] ||
	die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
capture_dir="$(dirname -- "$output")"
[[ "$(dirname -- "$capture_dir")" == "$private_root" &&
	"$(basename -- "$capture_dir")" == da921x-readonly-observer-attempt-* &&
	"$(basename -- "$output")" == runtime.txt ]] ||
	die 'output must be runtime.txt in one new da921x-readonly-observer-attempt-* private child'
[[ ! -e "$capture_dir" && ! -L "$capture_dir" ]] ||
	die 'capture directory already exists'
git -C "$repo_root" check-ignore -q "$capture_dir" ||
	die 'capture directory is not ignored by Git'

command_file="$(mktemp "${TMPDIR:-/tmp}/.da921x-observer-runtime.XXXXXXXX")"
# shellcheck disable=SC2329 # Invoked by the EXIT/HUP/INT/TERM trap.
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT HUP INT TERM
payload="$(base64 <"$probe" | tr -d '\n')"
[[ "$payload" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'probe base64 encoding is malformed'
printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
	"$payload" >"$command_file"
chmod 0600 "$command_file"

interface=
mac=
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
	# ifconfig -l emits a space-separated interface inventory on macOS.
	# shellcheck disable=SC2046
	for candidate in $(ifconfig -l); do
		candidate_mac="$(ifconfig "$candidate" 2>/dev/null |
			awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
		case "$candidate_mac" in
		42:00:15:19:82:00|42:00:15:19:84:00) ;;
		*) continue ;;
		esac
		if ! ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" \
			'$1 == "inet" && $2 == address {found++} END {exit found != 1}'; then
			continue
		fi
		route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null |
			awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')" || true
		[[ "$route_interface" == "$candidate" ]] || continue
		interface=$candidate
		mac=$candidate_mac
		break 2
	done
	sleep 1
done
[[ -n "$interface" ]] || die "exact Gemini USB interface did not become ready within $WAIT_SECONDS seconds"

mkdir -m 0700 "$capture_dir"
output="$capture_dir/runtime.txt"
{
	printf '__DA921X_OBSERVER_HOST_BEGIN__\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' "$interface" "$mac" "$HOST_ADDRESS"
	printf 'device_endpoint=%s:%s\nroute_interface=%s\n' "$DEVICE_ADDRESS" "$DEVICE_PORT" "$interface"
	printf 'installed_full_sha256=%s\n' "$CANDIDATE_SHA256"
	printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
	printf 'runtime_probe_transport=stdin-pipe-no-device-file\nreboot_request=none\n'
	printf '__DA921X_OBSERVER_HOST_END__\n'
} >"$output"
chmod 0600 "$output"

set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 45 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "$nc_status" >>"$output"

set +e
classification="$(python3 "$validator" "$output")"
classification_status=$?
set -e
printf '%s\n' "$classification" | grep -E \
	'^(runtime_classification|runtime_reason|provider_observation|cpu8_cpu9_admission|claim_scope)=' \
	>"$capture_dir/classification.txt" || die 'validator output is malformed'
chmod 0600 "$capture_dir/classification.txt"
(
	cd "$capture_dir"
	sha256sum runtime.txt classification.txt >SHA256SUMS
)
chmod 0600 "$capture_dir/SHA256SUMS"

printf '%s\n' "$classification"
printf 'capture=%s\nnc_exit_status=%s\n' "$output" "$nc_status"
exit "$classification_status"
