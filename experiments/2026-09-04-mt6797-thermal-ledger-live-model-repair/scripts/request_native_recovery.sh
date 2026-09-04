#!/usr/bin/env bash

# Return the exact successful live candidate to Gemian through its pinned reboot
# wrapper. This follows the completed read-only frame and accesses no partition.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly GEMIAN_ADDRESS=192.168.1.50
readonly HOST_MAC_82=42:00:15:19:82:00
readonly HOST_MAC_84=42:00:15:19:84:00
readonly RELEASE=7.1.3-gemini-mt6797-thermal-stage-ledger
readonly MAINLINE_BOOT_ID=95597a8b-501c-4a76-afb0-5b5286bf55d8
readonly RECOVERY_BOOT_ID=2f3a9a08-499f-4c25-8435-f30019a1ab0f
readonly INSTALLED_FULL_SHA256=93a78b490a9ffbf32eb60c5c875f508fd05b43b726220b3ccdbe9277792752a4
readonly FRAME_SHA256=638d40bb9e46a2acf5ac7755dc91efb9e3b75a5f84e83a86b5741b10f6369802
readonly EVENTS_SHA256=0d33ca0f368afd7a2f5999be863986b6780050bc0d94f58d0b17c52d0ff47ea5
readonly CLASSIFICATION_SHA256=a5f781a512f70579133bee5368c80ea8c7bec9a3fd9728d18b190d9b738eb231
readonly REBOOT_SHA256=3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
capture_dir=
while (($#)); do
	case "$1" in
	--capture-dir)
		(($# >= 2)) || die '--capture-dir requires a directory'
		capture_dir=$2
		shift 2
		;;
	*) die "usage: $0 --capture-dir artifacts/runtime-captures/thermal-ledger-live-model-repair-attempt-1" ;;
	esac
done
[[ -n "$capture_dir" ]] || die '--capture-dir is required'
for command in awk basename chmod date dirname git grep ifconfig mktemp nc netstat rm route sha256sum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly script_dir repo_root identity
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'private Gemini key is absent or unsafe'

case "$capture_dir" in /*) ;; *) capture_dir="$repo_root/${capture_dir#./}" ;; esac
private_root="$repo_root/artifacts/runtime-captures"
[[ "$(dirname -- "$capture_dir")" == "$private_root" ]] || die 'capture must be one direct private child'
[[ "$(basename -- "$capture_dir")" == thermal-ledger-live-model-repair-attempt-1 ]] || die 'capture identity changed'
[[ -d "$capture_dir" && ! -L "$capture_dir" && "$(stat -f '%Lp' "$capture_dir")" == 700 ]] || die 'capture directory is unsafe'
git -C "$repo_root" check-ignore -q -- "$capture_dir" || die 'capture is not ignored by Git'
frame="$capture_dir/observation.txt"
events="$capture_dir/observer-events.txt"
classification="$capture_dir/classification.txt"
output="$capture_dir/native-recovery.txt"
for path in "$frame" "$events" "$classification"; do
	[[ -f "$path" && ! -L "$path" && "$(stat -f '%Lp' "$path")" == 600 ]] || die "capture member is unsafe: $path"
done
[[ "$(sha256sum "$frame" | awk '{print $1}')" == "$FRAME_SHA256" ]] || die 'runtime frame identity changed'
[[ "$(sha256sum "$events" | awk '{print $1}')" == "$EVENTS_SHA256" ]] || die 'observer events identity changed'
[[ "$(sha256sum "$classification" | awk '{print $1}')" == "$CLASSIFICATION_SHA256" ]] || die 'classification identity changed'
grep -Fqx "kernel_release=$RELEASE" "$frame" || die 'captured release changed'
grep -Fqx "boot_id=$MAINLINE_BOOT_ID" "$frame" || die 'captured boot identity changed'
grep -Fqx 'dt_model=MT6797X' "$frame" || die 'captured live model changed'
grep -Fqx 'thermal_driver=mtk-thermal' "$frame" || die 'captured thermal driver changed'
grep -Fqx 'thermal_bind_count=1' "$frame" || die 'captured thermal bind count changed'
grep -Fqx 'thermal_zone_count=1' "$frame" || die 'captured zone count changed'
grep -Fqx 'classification=mt6797-thermal-ledger-live-model-repair-pass' "$classification" || die 'classification is not the exact pass'
grep -Fqx "recovery_boot_id=$RECOVERY_BOOT_ID" "$events" || die 'captured recovery boot identity changed'
grep -Fqx "installed_full_sha256=$INSTALLED_FULL_SHA256" "$events" || die 'captured installed identity changed'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite recovery evidence'

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

command_file=$(mktemp "${TMPDIR:-/tmp}/.gemini-thermal-ledger-live-model-recovery.XXXXXXXX")
cleanup() { rm -f -- "${command_file:-}"; }
trap cleanup EXIT HUP INT TERM
cat >"$command_file" <<REMOTE
live_release=\$(/bin/busybox uname -r) || exit 90
live_boot_id=\$(/bin/busybox cat /proc/sys/kernel/random/boot_id) || exit 91
live_reboot_sha=\$(/bin/busybox sha256sum /bin/reboot | /bin/busybox awk '{print \$1}') || exit 92
/bin/busybox printf '%s\n' __GEMINI_THERMAL_LEDGER_LIVE_MODEL_RECOVERY_BEGIN__
/bin/busybox printf 'live_release=%s\nlive_boot_id=%s\nreboot_sha256=%s\n' "\$live_release" "\$live_boot_id" "\$live_reboot_sha"
if [ "\$live_release" = '$RELEASE' ] && [ "\$live_boot_id" = '$MAINLINE_BOOT_ID' ] && [ "\$live_reboot_sha" = '$REBOOT_SHA256' ]; then
	/bin/busybox printf '%s\n' request_authorized=yes
else
	/bin/busybox printf '%s\n' request_authorized=no
fi
/bin/busybox printf '%s\n' device_partition_reads=none device_storage_writes=none sync_requested=no request_count=1
/bin/busybox printf '%s\n' __GEMINI_THERMAL_LEDGER_LIVE_MODEL_RECOVERY_END__
[ "\$live_release" = '$RELEASE' ] && [ "\$live_boot_id" = '$MAINLINE_BOOT_ID' ] && [ "\$live_reboot_sha" = '$REBOOT_SHA256' ] || exit 93
/bin/reboot
exit 94
REMOTE
chmod 0600 "$command_file"
printf 'expected_release=%s\nexpected_mainline_boot_id=%s\nrecovery_boot_id_before_attempt=%s\n' \
	"$RELEASE" "$MAINLINE_BOOT_ID" "$RECOVERY_BOOT_ID" >"$output"
printf 'installed_full_sha256=%s\ninterface=%s\nmac=%s\nrequest_utc=%s\n' \
	"$INSTALLED_FULL_SHA256" "$interface" "$mac" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$output"
set +e
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 30 "$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >>"$output" 2>&1
nc_rc=$?
set -e
grep -Fq __GEMINI_THERMAL_LEDGER_LIVE_MODEL_RECOVERY_BEGIN__ "$output" || die "native recovery did not begin rc=$nc_rc"
grep -Fq __GEMINI_THERMAL_LEDGER_LIVE_MODEL_RECOVERY_END__ "$output" || die "native recovery did not complete rc=$nc_rc"
grep -Fq 'request_authorized=yes' "$output" || die 'live recovery identity gate refused the request'
if grep -Fq 'request_authorized=no' "$output"; then die 'live recovery identity gate reported refusal'; fi

ssh_options=(ssh -o BatchMode=yes -o ConnectTimeout=3 -o ConnectionAttempts=1 \
	-o ServerAliveInterval=2 -o ServerAliveCountMax=2 -o IdentitiesOnly=yes \
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity")
changed_gemian_boot_id=
for _ in {1..90}; do
	# shellcheck disable=SC2016
	gemian=$("${ssh_options[@]}" gemini@"$GEMIAN_ADDRESS" 'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"' 2>/dev/null || true)
	if [[ "$gemian" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ && "${BASH_REMATCH[1]}" != "$RECOVERY_BOOT_ID" && "${BASH_REMATCH[1]}" != "$MAINLINE_BOOT_ID" ]]; then
		changed_gemian_boot_id=${BASH_REMATCH[1]}
		break
	fi
	sleep 2
done
[[ -n "$changed_gemian_boot_id" ]] || die 'changed-ID Gemian did not return after native recovery'
printf 'nc_exit_status=%s\nnative_reboot_requested=yes\npartition_access=none\n' "$nc_rc" >>"$output"
printf 'changed_gemian_boot_id=%s\nrecovery_result=changed-ID-Gemian\nrecovery_utc=%s\n' \
	"$changed_gemian_boot_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$output"
sha256sum "$capture_dir"/*.txt >"$capture_dir/SHA256SUMS"
chmod 0600 "$capture_dir"/*
printf 'result=changed-ID-Gemian\nboot_id=%s\noutput=%s\n' "$changed_gemian_boot_id" "$output"
