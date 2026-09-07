#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One read-only live-GPT boot2 identity check on the already observed Gemian boot.
set -euo pipefail
export LC_ALL=C
umask 077

readonly TARGET=gemini@192.168.1.50
readonly EXPECTED_BOOT_ID=2b2a317f-94ff-43b3-a51f-2fa6c5ba0bf9
readonly EXPECTED_SHA256=a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821
readonly EXPECTED_SECTORS=32768

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --output ]] || die 'usage: inspect-gemian-boot2.sh --output artifacts/device-runtime-evidence/keyboard-boot2-preflight-20260907'

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
identity="$repo_root/artifacts/credentials/gemini_ed25519"
known_hosts="$repo_root/artifacts/credentials/a53-recovery-known_hosts"
output=$2
case "$output" in /*) ;; *) output="$repo_root/${output#./}" ;; esac
readonly script_dir repo_root identity known_hosts output

for command in awk chmod dirname git mkdir sed sha256sum ssh stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f $identity && ! -L $identity && $(stat -f '%Lp' "$identity") == 600 ]] || die 'identity is absent or unsafe'
[[ -f $known_hosts && ! -L $known_hosts && $(stat -f '%Lp' "$known_hosts") == 600 ]] || die 'known-host file is absent or unsafe'
private_root="$repo_root/artifacts/device-runtime-evidence"
[[ -d $private_root && ! -L $private_root ]] || die 'private evidence root is absent or unsafe'
private_root=$(cd -- "$private_root" && pwd -P)
[[ $(dirname -- "$output") == "$private_root" ]] || die 'output must be one direct child of the private evidence root'
[[ $(basename -- "$output") == keyboard-boot2-preflight-20260907 ]] || die 'output identity changed'
git -C "$repo_root" check-ignore -q -- "$output" || die 'output is not ignored'
[[ ! -e $output && ! -L $output ]] || die 'refusing to overwrite evidence'
mkdir -m 0700 "$output"
raw="$output/raw.txt"
readonly private_root raw

ssh_options=(
	-F /dev/null -T -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityAgent=none
	-o PreferredAuthentications=publickey -o PasswordAuthentication=no
	-o KbdInteractiveAuthentication=no -o NumberOfPasswordPrompts=0
	-o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known_hosts"
	-o GlobalKnownHostsFile=/dev/null -o UpdateHostKeys=no -o VerifyHostKeyDNS=no
	-o CanonicalizeHostname=no -o ProxyCommand=none -o ProxyJump=none
	-o ControlMaster=no -o ControlPath=none -o ControlPersist=no
	-o ClearAllForwardings=yes -o ForwardAgent=no -o ForwardX11=no
	-o ConnectionAttempts=1 -o ConnectTimeout=8 -o ServerAliveInterval=5
	-o ServerAliveCountMax=3 -o LogLevel=ERROR -o EscapeChar=none -i "$identity"
)

ssh "${ssh_options[@]}" "$TARGET" 'sudo -n /bin/sh -s' >"$raw" <<'REMOTE'
set -eu
export LC_ALL=C
expected_boot=2b2a317f-94ff-43b3-a51f-2fa6c5ba0bf9
[ "$(uname -r)" = 3.18.41+ ] && [ "$(uname -m)" = aarch64 ]
boot_before=$(cat /proc/sys/kernel/random/boot_id)
[ "$boot_before" = "$expected_boot" ]

count=0
target=
target_sysfs=
for uevent in /sys/class/block/mmcblk*p*/uevent; do
	[ -r "$uevent" ] || continue
	devname=; devtype=; partname=
	while IFS='=' read -r key value; do
		case "$key" in
		DEVNAME) devname=$value ;;
		DEVTYPE) devtype=$value ;;
		PARTNAME) partname=$value ;;
		esac
	done <"$uevent"
	[ "$devtype" = partition ] && [ "$partname" = boot2 ] || continue
	count=$((count+1)); target=/dev/$devname; target_sysfs=${uevent%/uevent}
done
[ "$count" = 1 ] && [ -b "$target" ]
[ "$(cat "$target_sysfs/size")" = 32768 ]
[ "$(cat "$target_sysfs/ro")" = 0 ]
for holder in "$target_sysfs"/holders/*; do [ ! -e "$holder" ]; done
root_source=unknown
while read -r source mountpoint rest; do
	[ "$source" != "$target" ]
	[ "$mountpoint" != / ] || root_source=$source
done </proc/mounts
[ "$root_source" != "$target" ]

power_ok=0; battery=unknown; external=0
for item in /sys/class/power_supply/*/capacity; do
	[ -r "$item" ] || continue
	value=$(cat "$item")
	case "$value" in ''|*[!0-9]*) ;; *) battery=$value; [ "$value" -lt 25 ] || power_ok=1 ;; esac
done
for item in /sys/class/power_supply/*/online; do
	[ -r "$item" ] || continue
	value=$(cat "$item"); [ "$value" != 1 ] || { external=1; power_ok=1; }
done
[ "$power_ok" = 1 ]
checksum=$(sha256sum "$target" | awk '{print $1}')
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_before" ]

printf '%s\n' __KEYBOARD_BOOT2_PREFLIGHT_BEGIN__
printf 'kernel_release=3.18.41+\narchitecture=aarch64\nboot_id=%s\n' "$boot_before"
printf 'boot2_target=%s\nboot2_sectors=32768\nboot2_read_only=0\n' "$target"
printf 'active_root=%s\nboot2_mounted=no\nboot2_holders=none\n' "$root_source"
printf 'battery_capacity=%s\nexternal_power_online=%s\npower_stable=yes\n' "$battery" "$external"
printf 'boot2_sha256=%s\npartition_reads=1\npartition_writes=0\n' "$checksum"
printf '%s\n' __KEYBOARD_BOOT2_PREFLIGHT_END__
REMOTE

chmod 0600 "$raw"
[[ $(sed -n '1p' "$raw") == __KEYBOARD_BOOT2_PREFLIGHT_BEGIN__ ]] || die 'begin marker missing'
[[ $(sed -n '$p' "$raw") == __KEYBOARD_BOOT2_PREFLIGHT_END__ ]] || die 'end marker missing'
[[ $(awk -F= '$1 == "boot_id" {print $2}' "$raw") == "$EXPECTED_BOOT_ID" ]] || die 'boot changed'
[[ $(awk -F= '$1 == "boot2_sectors" {print $2}' "$raw") == "$EXPECTED_SECTORS" ]] || die 'boot2 size mismatch'
actual=$(awk -F= '$1 == "boot2_sha256" {print $2}' "$raw")
[[ $actual =~ ^[0-9a-f]{64}$ ]] || die 'checksum framing invalid'
result=unexpected-candidate
[[ $actual != "$EXPECTED_SHA256" ]] || result=exact-baseline-candidate
printf 'classification=%s\nexpected_sha256=%s\nactual_sha256=%s\noutput=%s\n' \
	"$result" "$EXPECTED_SHA256" "$actual" "$output"
