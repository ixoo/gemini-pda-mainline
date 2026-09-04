#!/usr/bin/env bash

# Return a successfully classified thermal candidate to Gemian through its
# exact inherited /bin/reboot wrapper, with no partition access.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly RELEASE=7.1.3-gemini-mt6797-thermal-serviceability
readonly INSTALLED_FULL_SHA256=6f3d8d6e94ff1ce587f0189a0c44db2abc7a29f487f1ec33e66e9db5e3505801
readonly REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7
readonly CLASSIFIER_SHA256=ad13cd7efe9ffaafab444fdadb417f8f67ca47924ba050aafc60fd5dbc7cfdbe

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
capture_dir=
while (($#)); do
	case "$1" in
	--capture-dir)
		(($# >= 2)) || die '--capture-dir requires a directory'
		capture_dir=$2
		shift 2
		;;
	*) die "usage: $0 --capture-dir artifacts/runtime-captures/thermal-serviceability-attempt-1" ;;
	esac
done
[[ -n "$capture_dir" ]] || die '--capture-dir is required'
for command in awk basename cat chmod cmp date dirname git grep ifconfig mktemp nc \
	netstat python3 rm route sed sha256sum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
classifier="$script_dir/classify_observation.py"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly script_dir repo_root classifier identity
[[ -f "$classifier" && ! -L "$classifier" ]] || die 'classifier is absent or unsafe'
[[ "$(sha256sum "$classifier" | awk '{print $1}')" == "$CLASSIFIER_SHA256" ]] || die 'classifier source changed'
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'private Gemini key is absent or unsafe'

case "$capture_dir" in /*) ;; *) capture_dir="$repo_root/${capture_dir#./}" ;; esac
private_root="$repo_root/artifacts/runtime-captures"
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || die 'capture must be one direct private child'
[[ "$(basename -- "$capture_dir")" == thermal-serviceability-attempt-1 ]] || die 'capture identity changed'
[[ -d "$capture_dir" && ! -L "$capture_dir" && "$(stat -f '%Lp' "$capture_dir")" == 700 ]] || die 'capture directory is unsafe'
git -C "$repo_root" check-ignore -q -- "$capture_dir" || die 'capture is not ignored by Git'
frame="$capture_dir/observation.txt"
events="$capture_dir/observer-events.txt"
classification="$capture_dir/classification.txt"
output="$capture_dir/native-reboot.txt"
for path in "$frame" "$events" "$classification"; do
	[[ -f "$path" && ! -L "$path" && "$(stat -f '%Lp' "$path")" == 600 ]] || die "capture member is unsafe: $path"
done
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite reboot evidence'
recovery_boot_id=$(awk -F= '$1 == "recovery_boot_id" {print $2; count++} END {exit count != 1}' "$events")
installed_full_sha256=$(awk -F= '$1 == "installed_full_sha256" {print $2; count++} END {exit count != 1}' "$events")
[[ "$installed_full_sha256" == "$INSTALLED_FULL_SHA256" ]] || die 'capture installed identity changed'
python3 "$classifier" "$frame" --recovery-boot-id "$recovery_boot_id" >"$capture_dir/.reclassification.txt"
cmp -s "$capture_dir/.reclassification.txt" "$classification" || {
	rm -f "$capture_dir/.reclassification.txt"
	die 'runtime reclassification changed'
}
rm -f "$capture_dir/.reclassification.txt"
mainline_boot_id=$(awk -F= '$1 == "boot_id" {print $2; count++} END {exit count != 1}' "$classification")

interface=
mac=
# shellcheck disable=SC2046
for candidate in $(ifconfig -l); do
	candidate_mac=$(ifconfig "$candidate" 2>/dev/null | awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}') || true
	case "$candidate_mac" in "$HOST_MAC_82"|"$HOST_MAC_84") ;; *) continue ;; esac
	ifconfig "$candidate" | awk -v address="$HOST_ADDRESS" '$1 == "inet" && $2 == address {count++} END {exit count != 1}' || continue
	route_interface=$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | awk '$1 == "interface:" {print $2; count++} END {exit count != 1}') || true
	if [[ -z "$route_interface" ]]; then
		route_interface=$(netstat -rn -f inet 2>/dev/null | awk -v interface="$candidate" '$1 == "10.15.19/24" && $4 == interface {print $4; count++} END {exit count != 1}') || true
	fi
	[[ "$route_interface" == "$candidate" ]] || continue
	interface=$candidate
	mac=$candidate_mac
	break
done
[[ -n "$interface" ]] || die 'exact Gemini USB interface is absent'

command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-thermal-reboot.XXXXXXXX")
cleanup() { rm -f -- "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
cat >"$command_file" <<REMOTE
live_release=\$(/bin/busybox uname -r) || exit 90
live_boot_id=\$(/bin/busybox cat /proc/sys/kernel/random/boot_id) || exit 91
live_reboot_sha=\$(/bin/busybox sha256sum /bin/reboot | /bin/busybox awk '{print \$1}') || exit 92
/bin/busybox printf '%s\n' __GEMINI_THERMAL_NATIVE_REBOOT_BEGIN__
/bin/busybox printf 'live_release=%s\nlive_boot_id=%s\nreboot_sha256=%s\n' "\$live_release" "\$live_boot_id" "\$live_reboot_sha"
if [ "\$live_release" = '$RELEASE' ] && [ "\$live_boot_id" = '$mainline_boot_id' ] && [ "\$live_reboot_sha" = '$REBOOT_SHA256' ]; then
	/bin/busybox printf '%s\n' request_authorized=yes
else
	/bin/busybox printf '%s\n' request_authorized=no
fi
/bin/busybox printf '%s\n' device_partition_reads=none device_storage_writes=none sync_requested=no request_count=1
/bin/busybox printf '%s\n' __GEMINI_THERMAL_NATIVE_REBOOT_END__
[ "\$live_release" = '$RELEASE' ] && [ "\$live_boot_id" = '$mainline_boot_id' ] && [ "\$live_reboot_sha" = '$REBOOT_SHA256' ] || exit 93
/bin/reboot
exit 94
REMOTE
chmod 0600 "$command_file"
printf 'expected_release=%s\nexpected_mainline_boot_id=%s\nrecovery_boot_id_before_attempt=%s\n' \
	"$RELEASE" "$mainline_boot_id" "$recovery_boot_id" >"$output"
printf 'installed_full_sha256=%s\ninterface=%s\nmac=%s\nrequest_utc=%s\n' \
	"$INSTALLED_FULL_SHA256" "$interface" "$mac" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$output"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 "$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_rc=$?
set -e
grep -Fq __GEMINI_THERMAL_NATIVE_REBOOT_BEGIN__ "$output" || die "native request did not begin rc=$nc_rc"
grep -Fq __GEMINI_THERMAL_NATIVE_REBOOT_END__ "$output" || die "native request did not complete rc=$nc_rc"
awk '
	/__GEMINI_THERMAL_NATIVE_REBOOT_BEGIN__/ {inside=1; next}
	/__GEMINI_THERMAL_NATIVE_REBOOT_END__/ {inside=0}
	inside {
		line=$0
		sub(/\r$/, "", line)
		if (line ~ /request_authorized=yes$/) yes++
		if (line ~ /request_authorized=no$/) no++
	}
	END {exit yes != 1 || no != 0}
' "$output" || die 'live reboot identity gate refused the request'

ssh_options=(ssh -o BatchMode=yes -o ConnectTimeout=3 -o IdentitiesOnly=yes \
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity")
changed_gemian_boot_id=
for _ in {1..90}; do
	# shellcheck disable=SC2016
	gemian=$("${ssh_options[@]}" gemini@"$GEMIAN_ADDRESS" 'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' 2>/dev/null || true)
	if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ && "${BASH_REMATCH[1]}" != "$recovery_boot_id" && "${BASH_REMATCH[1]}" != "$mainline_boot_id" ]]; then
		changed_gemian_boot_id=${BASH_REMATCH[1]}
		break
	fi
	sleep 2
done
[[ -n "$changed_gemian_boot_id" ]] || die 'changed-ID Gemian did not return after native reboot'
printf 'nc_exit_status=%s\nnative_reboot_requested=yes\npartition_access=none\n' "$nc_rc" >>"$output"
printf 'changed_gemian_boot_id=%s\nrecovery_result=changed-ID-Gemian\nrecovery_utc=%s\n' \
	"$changed_gemian_boot_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$output"
sha256sum "$classification" "$events" "$frame" "$output" >"$capture_dir/SHA256SUMS"
chmod 0600 "$capture_dir"/*
printf 'result=changed-ID-Gemian\nboot_id=%s\noutput=%s\n' "$changed_gemian_boot_id" "$output"
