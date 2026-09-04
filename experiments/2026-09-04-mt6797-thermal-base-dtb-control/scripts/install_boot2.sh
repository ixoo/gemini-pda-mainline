#!/usr/bin/env bash

# Install the exact base-DT control to guarded inactive boot2 and power off.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

readonly TARGET=gemini@192.168.1.50
readonly EXPECTED_ORIGIN=https://github.com/ixoo/gemini-pda-mainline.git
readonly BUILD_COMMIT=b66b03c722cd67584fb8fb15de493ebb084954b4
readonly CANDIDATE_DIR=candidate-mt6797-thermal-base-dtb-control-fb660f34
readonly CANDIDATE_SHA256=ec26245757291c4d7761683b7afc8042cc8bf98fd34a4c977946cf23a5147db5
readonly CANDIDATE_SIZE=16777216

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
output=
while (($#)); do
	case "$1" in
	--output) (($# >= 2)) || die '--output requires a directory'; output=$2; shift 2 ;;
	*) die "usage: $0 --output artifacts/device-deployments/thermal-base-dtb-control-attempt-1" ;;
	esac
done
[[ -n "$output" ]] || die '--output is required'
for command in awk basename chmod date dirname git mkdir mktemp nc rm sha256sum sleep ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
identity="$repo_root/artifacts/credentials/gemini_ed25519"
package="$repo_root/artifacts/buildbox/$BUILD_COMMIT/linux-7.1.3-gemini-mt6797-thermal-stage-ledger-593cac61-f213e5f0"
ramdisk_source="$repo_root/artifacts/mt6797-pwrap-reset-serviceability/candidate-mt6797-pwrap-reset-305230b1"
candidate_dir="$repo_root/artifacts/mt6797-thermal-base-dtb-control/$CANDIDATE_DIR"
candidate="$candidate_dir/boot2-padded.img"
readonly script_dir repo_root identity package ramdisk_source candidate_dir candidate

[[ "$(git -C "$repo_root" remote get-url origin)" == "$EXPECTED_ORIGIN" ]] || die 'origin URL changed'
git -C "$repo_root" merge-base --is-ancestor "$BUILD_COMMIT" origin/main || die 'Buildbox commit is not published'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$(git -C "$repo_root" rev-parse origin/main)" ]] || die 'experiment revision is not published at origin/main'
git -C "$repo_root" diff --quiet || die 'tracked worktree is not clean'
git -C "$repo_root" diff --cached --quiet || die 'index is not clean'
[[ -f "$identity" && ! -L "$identity" && "$(stat -f '%Lp' "$identity")" == 600 ]] || die 'private Gemini key is absent or unsafe'
[[ -f "$candidate" && ! -L "$candidate" ]] || die 'candidate is absent or unsafe'
[[ "$(stat -f '%z' "$candidate")" == "$CANDIDATE_SIZE" ]] || die 'candidate size changed'
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$CANDIDATE_SHA256" ]] || die 'candidate checksum changed'
python3 "$script_dir/validate_candidate.py" --repository "$repo_root" --package "$package" \
	--initramfs-source "$ramdisk_source" --candidate "$candidate_dir" >/dev/null

case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
private_root="$repo_root/artifacts/device-deployments"
[[ -d "$private_root" ]] || mkdir -m 0700 "$private_root"
[[ -d "$private_root" && ! -L "$private_root" && "$(stat -f '%Lp' "$private_root")" == 700 ]] || die 'private deployment root is unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ "$(dirname -- "$output")" == "$private_root" ]] || die '--output must be one direct child of artifacts/device-deployments/'
[[ "$(basename -- "$output")" == thermal-base-dtb-control-attempt-1 ]] || die 'output directory identity changed'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored by Git'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite deployment evidence'
mkdir -m 0700 "$output"
output=$(cd -- "$output" && pwd -P)
evidence="$output/deployment.txt"
readonly private_root output evidence

ssh_options=(
	-o BatchMode=yes -o ConnectTimeout=5 -o ConnectionAttempts=1
	-o ServerAliveInterval=2 -o ServerAliveCountMax=2 -o IdentitiesOnly=yes
	-o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no
	-i "$identity"
)
ssh -n "${ssh_options[@]}" "$TARGET" true >/dev/null || die 'known-good Gemian SSH is unavailable'
remote_identity=$(ssh -n "${ssh_options[@]}" "$TARGET" 'printf "%s|%s|%s\n" "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"')
[[ "$remote_identity" =~ ^3\.18\.41\+\|aarch64\|([0-9a-f-]{36})$ ]] || die 'remote system is not exact known-good Gemian'
recovery_boot_id=${BASH_REMATCH[1]}
ssh -n "${ssh_options[@]}" "$TARGET" 'sudo -n true' >/dev/null 2>&1 || die 'Gemian passwordless sudo is unavailable'

remote_candidate=/tmp/gemini-thermal-base-dtb-control-ec262457.img
ssh "${ssh_options[@]}" "$TARGET" 'umask 077; rm -f /tmp/gemini-thermal-base-dtb-control-ec262457.img; cat >/tmp/gemini-thermal-base-dtb-control-ec262457.img' <"$candidate"
remote_script=$(mktemp "${TMPDIR:-/tmp}/.gemini-thermal-base-dtb-install.XXXXXXXX")
cleanup() {
	rm -f -- "${remote_script:-}"
	ssh -n "${ssh_options[@]}" "$TARGET" "rm -f $remote_candidate" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM
cat >"$remote_script" <<'REMOTE'
set -eu
export LC_ALL=C
candidate=/tmp/gemini-thermal-base-dtb-control-ec262457.img
expected_sha=ec26245757291c4d7761683b7afc8042cc8bf98fd34a4c977946cf23a5147db5
expected_size=16777216
die() { printf 'error: %s\n' "$*" >&2; exit 2; }

[ "$(uname -r)" = 3.18.41+ ] && [ "$(uname -m)" = aarch64 ] || die 'not known-good Gemian'
boot_id_before=$(cat /proc/sys/kernel/random/boot_id)
[ -f "$candidate" ] && [ ! -L "$candidate" ] || die 'staged candidate is unsafe'
[ "$(stat -c '%s' "$candidate")" = "$expected_size" ] || die 'staged candidate size mismatch'
[ "$(sha256sum "$candidate" | awk '{print $1}')" = "$expected_sha" ] || die 'staged candidate checksum mismatch'

target_count=0
target=
target_sysfs=
for uevent in /sys/class/block/mmcblk*p*/uevent; do
	[ -r "$uevent" ] || continue
	devname= devtype= partname=
	while IFS='=' read -r key value; do
		case "$key" in DEVNAME) devname=$value ;; DEVTYPE) devtype=$value ;; PARTNAME) partname=$value ;; esac
	done <"$uevent"
	[ "$devtype" = partition ] && [ "$partname" = boot2 ] || continue
	target_count=$((target_count + 1))
	target=/dev/$devname
	target_sysfs=${uevent%/uevent}
done
[ "$target_count" = 1 ] || die 'live GPT did not resolve exactly one boot2'
[ -b "$target" ] || die 'boot2 is not a block device'
[ "$(cat "$target_sysfs/size")" = 32768 ] || die 'boot2 size is not 16 MiB'
[ "$(cat "$target_sysfs/ro")" = 0 ] || die 'boot2 is read-only'
for holder in "$target_sysfs"/holders/*; do [ ! -e "$holder" ] || die 'boot2 has a holder'; done
root_source=unknown
while read -r source mountpoint rest; do
	[ "$source" != "$target" ] || die 'boot2 is mounted'
	[ "$mountpoint" != / ] || root_source=$source
done </proc/mounts
[ "$root_source" != "$target" ] || die 'boot2 is the active root'

power_ok=0
battery_capacity=unknown
external_online=0
for item in /sys/class/power_supply/*/capacity; do
	[ -r "$item" ] || continue
	value=$(cat "$item")
	case "$value" in *[!0-9]*|'') ;; *) battery_capacity=$value; [ "$value" -ge 25 ] && power_ok=1 ;; esac
done
for item in /sys/class/power_supply/*/online; do
	[ -r "$item" ] || continue
	value=$(cat "$item")
	[ "$value" = 1 ] && external_online=1 && power_ok=1
done
[ "$power_ok" = 1 ] || die 'power stability gate failed'
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id_before" ] || die 'boot identity changed during gates'

predecessor_sha=$(sha256sum "$target" | awk '{print $1}')
write_performed=yes
if [ "$predecessor_sha" = "$expected_sha" ]; then
	write_performed=no-already-current
else
	dd if="$candidate" of="$target" bs=4194304 count=4 conv=fsync status=none || die 'boot2 write failed'
	sync
	blockdev --flushbufs "$target" || die 'boot2 flush failed'
fi
readback_sha=$(sha256sum "$target" | awk '{print $1}')
[ "$readback_sha" = "$expected_sha" ] || die 'full boot2 readback mismatch'
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id_before" ] || die 'boot identity changed before shutdown'

printf '%s\n' __GEMINI_THERMAL_BASE_DTB_DEPLOYMENT_BEGIN__
printf 'kernel_release=%s\narchitecture=%s\nrecovery_boot_id=%s\n' "$(uname -r)" "$(uname -m)" "$boot_id_before"
printf 'boot2_target=%s\nboot2_size=%s\nboot2_read_only=0\n' "$target" "$expected_size"
printf 'active_root=%s\nboot2_mounted=no\nboot2_holders=none\n' "$root_source"
printf 'battery_capacity=%s\nexternal_power_online=%s\npower_stable=yes\n' "$battery_capacity" "$external_online"
printf 'candidate_sha256=%s\npredecessor_sha256=%s\nwrite_performed=%s\n' "$expected_sha" "$predecessor_sha" "$write_performed"
printf 'sync=yes\nblock_flush=yes\nfull_readback_sha256=%s\nfull_readback_match=yes\n' "$readback_sha"
printf 'partition_backup_created=no\nbackup_policy=project-wide-starting-backup\n'
printf 'target_scope=live-GPT-logical-boot2-only\nother_partition_writes=none\n'
printf 'shutdown_requested=yes-after-verified-readback\n'
printf '%s\n' __GEMINI_THERMAL_BASE_DTB_DEPLOYMENT_END__
rm -f "$candidate"
sync
poweroff
REMOTE
chmod 0600 "$remote_script"

printf 'experiment=2026-09-04-mt6797-thermal-base-dtb-control\n' >"$evidence"
printf 'repository_build_commit=%s\nrepository_install_commit=%s\ncandidate_sha256=%s\ncandidate_size=%s\n' \
	"$BUILD_COMMIT" "$(git -C "$repo_root" rev-parse HEAD)" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE" >>"$evidence"
printf 'recovery_boot_id_preflight=%s\ndeployment_started_utc=%s\n' "$recovery_boot_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$evidence"
set +e
ssh "${ssh_options[@]}" "$TARGET" 'sudo -n /bin/sh -s' <"$remote_script" >>"$evidence" 2>&1
ssh_rc=$?
set -e
grep -Fq __GEMINI_THERMAL_BASE_DTB_DEPLOYMENT_BEGIN__ "$evidence" || die "deployment did not begin rc=$ssh_rc"
grep -Fq __GEMINI_THERMAL_BASE_DTB_DEPLOYMENT_END__ "$evidence" || die "deployment did not complete rc=$ssh_rc"
grep -Fqx "full_readback_sha256=$CANDIDATE_SHA256" "$evidence" || die 'deployment readback identity missing'
grep -Fqx 'full_readback_match=yes' "$evidence" || die 'deployment readback did not pass'
grep -Fqx 'shutdown_requested=yes-after-verified-readback' "$evidence" || die 'shutdown request missing'

closed_samples=0
for _ in {1..30}; do
	if nc -G 1 -z 192.168.1.50 22 >/dev/null 2>&1; then
		closed_samples=0
	else
		closed_samples=$((closed_samples + 1))
		((closed_samples >= 3)) && break
	fi
	sleep 1
done
((closed_samples >= 3)) || die 'Gemian TCP/22 remained open after shutdown request'
printf 'ssh_exit_status=%s\nshutdown_tcp22_closed_samples=3\nshutdown_disconnect_observed=yes\ndeployment_completed_utc=%s\n' "$ssh_rc" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$evidence"
sha256sum "$evidence" >"$output/SHA256SUMS"
chmod 0600 "$output"/*
trap - EXIT HUP INT TERM
rm -f -- "$remote_script"
printf 'result=boot2-readback-verified-device-shutdown\nrecovery_boot_id=%s\noutput=%s\n' "$recovery_boot_id" "$output"
