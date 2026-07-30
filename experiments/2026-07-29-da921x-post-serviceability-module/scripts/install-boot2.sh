#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly BOOT2_SIZE=16777216
readonly EXPECTED_PREDECESSOR_SHA256=b726b1d86ed5fa68b221a7f3ea25ed068a455f143a97098b15c26552e6713baa
readonly CANDIDATE_SHA256=86b0efaa2beafa97bd6382ec457508d0b516dab813d6ebbe8b1b7de1f4f88f17
readonly ARTIFACT_MANIFEST_SHA256=de2e73daee85a8741489c74b1e8b05771ddda9d6c56c92163825aa23987831f5
readonly ARTIFACT_NAME=candidate-Gate3-da921x-module-b57766ab

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	cat <<'EOF'
usage: install-boot2.sh --target gemini@192.168.1.50 \
  --candidate-dir DIR --evidence-dir DIR

Install the exact post-serviceability-module candidate to live-GPT-resolved
boot2. No new partition backup is created. A full post-write readback is
required, its temporary copy is removed, and the device is shut down after
verified success.
EOF
}

target=
candidate_dir=
evidence_dir=
while (($#)); do
	case "$1" in
	--target) target=${2:-}; shift 2 ;;
	--candidate-dir) candidate_dir=${2:-}; shift 2 ;;
	--evidence-dir) evidence_dir=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ "$target" == "$EXPECTED_TARGET" && -n "$candidate_dir" &&
	-n "$evidence_dir" ]] || { usage >&2; die 'all exact arguments are required'; }
for command in awk basename chmod cmp dirname git mkdir mktemp readlink rm \
	sha256sum sleep ssh stat sync tr wc; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
evidence_root="$repo_root/artifacts/device-install-evidence"
[[ -d "$candidate_dir" && ! -L "$candidate_dir" ]] ||
	die 'candidate directory is missing or unsafe'
candidate_dir="$(cd -- "$candidate_dir" && pwd -P)"
[[ "$(basename -- "$candidate_dir")" == "$ARTIFACT_NAME" ]] ||
	die 'candidate artifact name changed'
candidate="$candidate_dir/boot2-padded.img"
manifest="$candidate_dir/SHA256SUMS"
[[ -f "$candidate" && ! -L "$candidate" && -f "$manifest" && ! -L "$manifest" ]] ||
	die 'candidate or manifest is missing or unsafe'
[[ "$(stat -f '%z' "$candidate" 2>/dev/null || stat -c '%s' "$candidate")" == \
	"$BOOT2_SIZE" ]] || die 'candidate size changed'
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$CANDIDATE_SHA256" ]] ||
	die 'candidate checksum changed'
[[ "$(sha256sum "$manifest" | awk '{print $1}')" == \
	"$ARTIFACT_MANIFEST_SHA256" ]] || die 'candidate manifest changed'
(cd "$candidate_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'candidate manifest validation failed'
[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini identity is missing'
[[ "$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")" == 600 ]] ||
	die 'Gemini identity mode is not 0600'

[[ -d "$evidence_root" && ! -L "$evidence_root" ]] ||
	die 'device-install evidence root is missing or unsafe'
evidence_root="$(cd -- "$evidence_root" && pwd -P)"
case "$evidence_dir" in
/*) ;;
*) evidence_dir="$repo_root/$evidence_dir" ;;
esac
[[ "$(dirname -- "$evidence_dir")" == "$evidence_root" ]] ||
	die 'evidence directory must be one direct child of device-install-evidence'
[[ ! -e "$evidence_dir" && ! -L "$evidence_dir" ]] ||
	die 'evidence directory already exists'
git -C "$repo_root" check-ignore -q "$evidence_dir" ||
	die 'evidence directory is not ignored by Git'
mkdir -m 0700 "$evidence_dir"
evidence_dir="$(cd -- "$evidence_dir" && pwd -P)"

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
"${ssh_command[@]}" "$target" \
	'command -v systemctl >/dev/null && sudo -n true' ||
	die 'known-good Gemian access, passwordless sudo, or systemctl is unavailable'
boot_id="$("${ssh_command[@]}" "$target" \
	'sudo -n cat /proc/sys/kernel/random/boot_id')"
boot_id=${boot_id//$'\r'/}
[[ "$boot_id" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed boot ID'

remote_gate() {
	local mode=$1
	local stage=$2
	"${ssh_command[@]}" "$target" \
		"sudo -n env MODE='$mode' EXPECTED_BOOT_ID='$boot_id' EXPECTED_SIZE='$BOOT2_SIZE' EXPECTED_PREDECESSOR_SHA256='$EXPECTED_PREDECESSOR_SHA256' EXPECTED_CANDIDATE_SHA256='$CANDIDATE_SHA256' EXPECTED_STAGE='$stage' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk blockdev cat dd find findmnt id lsblk readlink sha256sum \
	sleep stat swapon sync uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] ||
	fail 'boot ID changed'
rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT |
	awk '$2 == "boot2" {print}')"
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2'
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && "$label" == boot2 &&
	"$type" == part && "$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]] ||
	fail 'boot2 identity, size, or writable state changed'
[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]] ||
	fail 'boot2 is mounted or not a block device'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] ||
	fail 'by-partlabel disagrees with live GPT'
[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 ]] ||
	fail 'boot2 parent changed'
[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" &&
	"$(blockdev --getro "$target")" == 0 ]] || fail 'blockdev gate failed'
root="$(readlink -f "$(findmnt -n -o SOURCE /)")"
[[ "$root" == /dev/mmcblk0p29 && "$root" != "$target" ]] ||
	fail 'active root changed or equals boot2'
majmin="$(lsblk -dnro MAJ:MIN "$target")"
[[ -z "$(awk -v mm="$majmin" '$3 == mm {print}' /proc/self/mountinfo)" ]] ||
	fail 'boot2 is mounted'
[[ -z "$(find "/sys/class/block/${target##*/}/holders" -mindepth 1 \
	-maxdepth 1 -print -quit)" ]] || fail 'boot2 has holders'
while IFS= read -r swap; do
	[[ -z "$swap" || "$(readlink -f "$swap")" != "$target" ]] ||
		fail 'boot2 is active swap'
done <<<"$(swapon --noheadings --raw --show=NAME)"
present="$(cat /sys/class/power_supply/battery/present)"
capacity="$(cat /sys/class/power_supply/battery/capacity)"
health="$(cat /sys/class/power_supply/battery/health)"
[[ "$present" == 1 && "$capacity" =~ ^[0-9]+$ && "$health" == Good ]] ||
	fail 'battery identity or health gate failed'
(( capacity >= 81 && capacity <= 100 )) ||
	fail 'battery capacity is not above 80 percent'
sleep 2
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] ||
	fail 'boot ID changed during power gate'
current="$(sha256sum "$target" | awk '{print $1}')"
case "$MODE" in
probe)
	case "$current" in
	"$EXPECTED_PREDECESSOR_SHA256") already_current=no ;;
	"$EXPECTED_CANDIDATE_SHA256") already_current=yes ;;
	*) fail "unexpected boot2 predecessor: $current" ;;
	esac
	;;
write)
	[[ "$current" == "$EXPECTED_PREDECESSOR_SHA256" ]] ||
		fail 'boot2 changed before write'
	[[ "$EXPECTED_STAGE" =~ ^/home/gemini/\.gemini-da921x-module\.[A-Za-z0-9]+$ &&
		-f "$EXPECTED_STAGE" && ! -L "$EXPECTED_STAGE" ]] ||
		fail 'unsafe staging file'
	read -r owner mode stage_size <<<"$(stat -c '%U %a %s' "$EXPECTED_STAGE")"
	[[ "$owner" == gemini && "$mode" == 600 && "$stage_size" == "$EXPECTED_SIZE" ]] ||
		fail 'staging identity changed'
	[[ "$(sha256sum "$EXPECTED_STAGE" | awk '{print $1}')" == \
		"$EXPECTED_CANDIDATE_SHA256" ]] || fail 'staging checksum changed'
	dd if="$EXPECTED_STAGE" of="$target" bs=4M iflag=fullblock count=4 \
		conv=fsync,notrunc status=none
	sync
	blockdev --flushbufs "$target"
	sync
	[[ "$(sha256sum "$target" | awk '{print $1}')" == \
		"$EXPECTED_CANDIDATE_SHA256" ]] || fail 'post-flush checksum mismatch'
	current=$EXPECTED_CANDIDATE_SHA256
	already_current=yes
	;;
post)
	[[ "$current" == "$EXPECTED_CANDIDATE_SHA256" ]] ||
		fail 'post-write boot2 checksum mismatch'
	already_current=yes
	;;
*) fail 'invalid gate mode' ;;
esac
printf 'gate=passed\nmode=%s\ntarget=%s\nroot=%s\n' "$MODE" "$target" "$root"
printf 'boot_id=%s\npower=%s|%s|%s\n' "$EXPECTED_BOOT_ID" "$present" "$capacity" "$health"
printf 'target_sha256=%s\nalready_current=%s\n' "$current" "$already_current"
REMOTE
}

probe_output="$(remote_gate probe none)" || die 'initial boot2 gate failed'
printf '%s\n' "$probe_output"
already_current="$(printf '%s\n' "$probe_output" |
	awk -F= '$1=="already_current" {print $2}')"
live_target="$(printf '%s\n' "$probe_output" |
	awk -F= '$1=="target" {print $2}')"
power="$(printf '%s\n' "$probe_output" | awk -F= '$1=="power" {print $2}')"
[[ "$live_target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] ||
	die 'probe returned unsafe target'

stage=
# ShellCheck cannot infer that this function is invoked by the EXIT trap.
# shellcheck disable=SC2317
cleanup() {
	[[ -z "${stage:-}" ]] || "${ssh_command[@]}" "$target" \
		"test ! -e '$stage' || rm -f -- '$stage'" >/dev/null 2>&1 || true
}
trap cleanup EXIT
result=skipped-already-matching
if [[ "$already_current" == no ]]; then
	stage="$("${ssh_command[@]}" "$target" \
		'umask 077; mktemp /home/gemini/.gemini-da921x-module.XXXXXXXX')"
	stage=${stage//$'\r'/}
	[[ "$stage" =~ ^/home/gemini/\.gemini-da921x-module\.[A-Za-z0-9]+$ ]] ||
		die 'remote returned unsafe staging path'
	"${ssh_command[@]}" "$target" \
		"test -f '$stage' && test ! -L '$stage' && cat >'$stage' && chmod 600 '$stage'" \
		<"$candidate" || die 'candidate upload failed'
	write_output="$(remote_gate write "$stage")" || die 'bounded boot2 write failed'
	printf '%s\n' "$write_output"
	"${ssh_command[@]}" "$target" "rm -f -- '$stage'"
	stage=
	result=write-synced-flushed-full-readback-verified
fi
post_output="$(remote_gate post none)" || die 'final boot2 gate failed'
printf '%s\n' "$post_output"
readback="$evidence_dir/.boot2-readback.partial"
"${ssh_command[@]}" "$target" \
	"sudo -n dd if='$live_target' bs=4M iflag=fullblock count=4 status=none" \
	>"$readback" || die 'independent full readback stream failed'
[[ "$(wc -c <"$readback" | tr -d ' ')" == "$BOOT2_SIZE" ]] ||
	die 'independent readback length mismatch'
[[ "$(sha256sum "$readback" | awk '{print $1}')" == "$CANDIDATE_SHA256" ]] ||
	die 'independent readback checksum mismatch'
cmp -s "$candidate" "$readback" || die 'independent readback byte mismatch'
rm -f -- "$readback"

{
	printf 'experiment=2026-07-29-da921x-post-serviceability-module\n'
	printf 'target=%s\nboot_id=%s\npower=%s\n' "$live_target" "$boot_id" "$power"
	printf 'predecessor_sha256=%s\ncandidate_sha256=%s\n' \
		"$EXPECTED_PREDECESSOR_SHA256" "$CANDIDATE_SHA256"
	printf 'result=%s\nbackup=not-created-project-wide-backup-relied-upon\n' "$result"
	printf 'full_readback=matching-and-temporary-copy-removed\n'
	printf 'shutdown=requested-after-verified-success\n'
} >"$evidence_dir/deployment-summary.txt"
chmod 0600 "$evidence_dir/deployment-summary.txt"
sync
"${ssh_command[@]}" "$target" 'sudo -n systemctl poweroff' || true
for _ in {1..20}; do
	if ! "${ssh_command[@]}" "$target" true >/dev/null 2>&1; then
		printf 'shutdown=confirmed-disconnected\n'
		printf 'evidence=%s\n' "$evidence_dir/deployment-summary.txt"
		trap - EXIT
		exit 0
	fi
	sleep 1
done
die 'write verified, but device shutdown was not confirmed'
