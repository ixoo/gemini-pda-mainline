#!/usr/bin/env bash

# Install the exact validated pre-init recovery container to inactive boot2.
# The live GPT is authoritative. No partition backup is created. A successful
# full readback is followed by a clean shutdown, never a reboot.
set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_TARGET=gemini@192.168.1.50
readonly BOOT2_SIZE=16777216
readonly CANDIDATE_SHA256=99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7
readonly ARTIFACT_MANIFEST_SHA256=ac4432bf07785b653473e2b3acf89e4fc1f48dbe952f54e3695349239a8bc596
readonly ARTIFACT_NAME=gemian-runtime-provenance-preinit-455a85907827

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	cat <<'EOF'
usage: install-preinit-boot2.sh \
  --target gemini@192.168.1.50 \
  --candidate-dir DIR \
  --evidence-dir artifacts/device-install-evidence/provenance-preinit-deployment-N

Resolve inactive boot2 from the live GPT, record its predecessor checksum,
write and fully read back the exact candidate when needed, then shut down.
No fresh partition backup is made.
EOF
}

target=
candidate_dir=
evidence_dir=
while (($#)); do
	case "$1" in
	--target|--candidate-dir|--evidence-dir)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--target) [[ -z "$target" ]] || die 'duplicate --target'; target=$2 ;;
		--candidate-dir) [[ -z "$candidate_dir" ]] || die 'duplicate --candidate-dir'; candidate_dir=$2 ;;
		--evidence-dir) [[ -z "$evidence_dir" ]] || die 'duplicate --evidence-dir'; evidence_dir=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage >&2; die "unknown argument: $1" ;;
	esac
done
[[ "$target" == "$EXPECTED_TARGET" && -n "$candidate_dir" && -n "$evidence_dir" ]] ||
	{ usage >&2; die 'all exact arguments are required'; }

for command in awk basename chmod cmp dirname git mkdir mktemp rm sha256sum \
	sleep ssh stat sync tr wc; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
identity="$repo_root/artifacts/credentials/gemini_ed25519"
evidence_root="$repo_root/artifacts/device-install-evidence"

[[ -d "$candidate_dir" && ! -L "$candidate_dir" ]] || die 'candidate directory is missing or unsafe'
candidate_dir="$(cd -- "$candidate_dir" && pwd -P)"
[[ "$(basename -- "$candidate_dir")" == "$ARTIFACT_NAME" ]] || die 'candidate artifact name changed'
candidate="$candidate_dir/boot2-padded.img"
manifest="$candidate_dir/SHA256SUMS"
[[ -f "$candidate" && ! -L "$candidate" && -f "$manifest" && ! -L "$manifest" ]] ||
	die 'candidate or manifest is missing or unsafe'
size="$(stat -f '%z' "$candidate" 2>/dev/null || stat -c '%s' "$candidate")"
[[ "$size" == "$BOOT2_SIZE" ]] || die 'candidate size changed'
[[ "$(sha256sum "$candidate" | awk '{print $1}')" == "$CANDIDATE_SHA256" ]] ||
	die 'candidate checksum changed'
[[ "$(sha256sum "$manifest" | awk '{print $1}')" == "$ARTIFACT_MANIFEST_SHA256" ]] ||
	die 'candidate manifest checksum changed'
(cd "$candidate_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'candidate manifest validation failed'

[[ -f "$identity" && ! -L "$identity" ]] || die 'Gemini SSH identity is missing'
identity_mode="$(stat -f '%Lp' "$identity" 2>/dev/null || stat -c '%a' "$identity")"
[[ "$identity_mode" == 600 ]] || die 'Gemini SSH identity mode is not 0600'
[[ -d "$evidence_root" && ! -L "$evidence_root" ]] || die 'device-install evidence root is unsafe'
evidence_root="$(cd -- "$evidence_root" && pwd -P)"
case "$evidence_dir" in /*) ;; *) evidence_dir="$repo_root/${evidence_dir#./}" ;; esac
[[ "$(dirname -- "$evidence_dir")" == "$evidence_root" &&
	"$(basename -- "$evidence_dir")" == provenance-preinit-deployment-* ]] ||
	die 'evidence directory must be one new provenance-preinit-deployment-* child'
[[ ! -e "$evidence_dir" && ! -L "$evidence_dir" ]] || die 'evidence directory already exists'
git -C "$repo_root" check-ignore -q "$evidence_dir" || die 'evidence directory is not ignored by Git'

ssh_command=(
	ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5
	-o ServerAliveCountMax=6 -o IdentitiesOnly=yes -o IdentityAgent=none
	-o StrictHostKeyChecking=yes -i "$identity"
)
"${ssh_command[@]}" "$target" 'command -v systemctl >/dev/null && sudo -n true' ||
	die 'SSH, passwordless sudo, or systemctl is unavailable'
initial_boot_id="$("${ssh_command[@]}" "$target" 'sudo -n cat /proc/sys/kernel/random/boot_id')"
initial_boot_id=${initial_boot_id//$'\r'/}
[[ "$initial_boot_id" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'

remote_gate() {
	local gate_mode=$1 expected_predecessor=$2 expected_stage=$3
	"${ssh_command[@]}" "$target" \
		"sudo -n env GATE_MODE='$gate_mode' EXPECTED_BOOT_ID='$initial_boot_id' EXPECTED_SIZE='$BOOT2_SIZE' EXPECTED_PREDECESSOR='$expected_predecessor' EXPECTED_CANDIDATE='$CANDIDATE_SHA256' EXPECTED_STAGE='$expected_stage' /bin/bash -s" <<'REMOTE'
set -euo pipefail
export LC_ALL=C
fail() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk blockdev cat dd find findmnt id lsblk readlink sha256sum sleep \
	stat swapon sync uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == 3.18.41+ ]] ||
	fail 'remote is not exact known-good Gemian'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed'

rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" {print}')"
[[ "$(printf '%s\n' "$rows" | awk 'NF {n++} END {print n+0}')" == 1 ]] ||
	fail 'live GPT does not have exactly one boot2 row'
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && "$label" == boot2 &&
	"$type" == part && "$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]] ||
	fail 'boot2 identity, type, size, or writable state changed'
[[ -z "${mountpoint:-}" && -z "${extra:-}" && -b "$target" ]] || fail 'boot2 is mounted or invalid'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] || fail 'by-partlabel disagrees with GPT'
[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 ]] || fail 'boot2 parent changed'
[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" && "$(blockdev --getro "$target")" == 0 ]] ||
	fail 'blockdev gate failed'

root="$(readlink -f "$(findmnt -n -o SOURCE /)")"
[[ "$root" == /dev/mmcblk0p29 && "$root" != "$target" ]] || fail 'active root changed or equals boot2'
majmin="$(lsblk -dnro MAJ:MIN "$target")"
[[ -z "$(awk -v mm="$majmin" '$3 == mm {print}' /proc/self/mountinfo)" ]] || fail 'boot2 is mounted'
[[ -z "$(find "/sys/class/block/${target##*/}/holders" -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
	fail 'boot2 has holders'
while IFS= read -r swap; do
	[[ -z "$swap" || "$(readlink -f "$swap")" != "$target" ]] || fail 'boot2 is active swap'
done <<<"$(swapon --noheadings --raw --show=NAME)"

power_sample() {
	local present capacity health external online
	present="$(cat /sys/class/power_supply/battery/present)"
	capacity="$(cat /sys/class/power_supply/battery/capacity)"
	health="$(cat /sys/class/power_supply/battery/health)"
	external=0
	for online in /sys/class/power_supply/ac/online /sys/class/power_supply/usb/online \
		/sys/class/power_supply/wireless/online; do
		[[ ! -r "$online" ]] || external=$((external + $(cat "$online")))
	done
	[[ "$present" == 1 && "$capacity" =~ ^[0-9]+$ && "$health" == Good ]] || return 1
	(( capacity >= 80 || (capacity >= 40 && external >= 1) )) || return 1
	printf '%s|%s|%s|%s\n' "$present" "$capacity" "$health" "$external"
}
power_first="$(power_sample)" || fail 'power gate failed'
sleep 2
power_second="$(power_sample)" || fail 'second power gate failed'
[[ "$power_first" == "$power_second" ]] || fail 'power state changed between samples'
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed during gate'

target_sha256="$(sha256sum "$target" | awk '{print $1}')"
[[ "$target_sha256" =~ ^[0-9a-f]{64}$ ]] || fail 'malformed predecessor checksum'
case "$GATE_MODE" in
probe)
	[[ "$EXPECTED_PREDECESSOR" == none && "$EXPECTED_STAGE" == none ]] || fail 'unsafe probe arguments'
	[[ "$target_sha256" == "$EXPECTED_CANDIDATE" ]] && already_current=yes || already_current=no
	;;
write)
	[[ "$target_sha256" == "$EXPECTED_PREDECESSOR" ]] || fail 'boot2 changed before write'
	[[ "$EXPECTED_STAGE" =~ ^/home/gemini/\.gemini-provenance-preinit\.[A-Za-z0-9]+$ ]] ||
		fail 'unsafe staging path'
	[[ -f "$EXPECTED_STAGE" && ! -L "$EXPECTED_STAGE" ]] || fail 'staging file is unsafe'
	read -r owner mode stage_size <<<"$(stat -c '%U %a %s' "$EXPECTED_STAGE")"
	[[ "$owner" == gemini && "$mode" == 600 && "$stage_size" == "$EXPECTED_SIZE" ]] ||
		fail 'staging identity changed'
	[[ "$(sha256sum "$EXPECTED_STAGE" | awk '{print $1}')" == "$EXPECTED_CANDIDATE" ]] ||
		fail 'staging checksum changed'
	dd if="$EXPECTED_STAGE" of="$target" bs=4M iflag=fullblock count=4 conv=fsync,notrunc status=none
	sync
	blockdev --flushbufs "$target"
	sync
	[[ "$(sha256sum "$target" | awk '{print $1}')" == "$EXPECTED_CANDIDATE" ]] ||
		fail 'post-flush full-partition checksum mismatch'
	target_sha256=$EXPECTED_CANDIDATE
	already_current=yes
	;;
post)
	[[ "$EXPECTED_PREDECESSOR" =~ ^[0-9a-f]{64}$ && "$EXPECTED_STAGE" == none ]] ||
		fail 'unsafe post arguments'
	[[ "$target_sha256" == "$EXPECTED_CANDIDATE" ]] || fail 'post-write boot2 checksum mismatch'
	already_current=yes
	;;
*) fail 'invalid gate mode' ;;
esac

printf 'gate=passed\nmode=%s\ntarget=%s\nroot=%s\n' "$GATE_MODE" "$target" "$root"
printf 'boot_id=%s\npower=%s\ntarget_sha256=%s\nalready_current=%s\n' \
	"$EXPECTED_BOOT_ID" "$power_second" "$target_sha256" "$already_current"
REMOTE
}

single_value() {
	local key=$1 data=$2
	printf '%s\n' "$data" | awk -F= -v key="$key" '$1 == key {value=$2; count++} END {if (count != 1) exit 2; print value}'
}

probe_output="$(remote_gate probe none none)" || die 'initial boot2 gate failed'
printf '%s\n' "$probe_output"
predecessor_sha256="$(single_value target_sha256 "$probe_output")" || die 'invalid predecessor evidence'
already_current="$(single_value already_current "$probe_output")" || die 'invalid current-state evidence'
live_target="$(single_value target "$probe_output")" || die 'invalid target evidence'
power="$(single_value power "$probe_output")" || die 'invalid power evidence'
[[ "$predecessor_sha256" =~ ^[0-9a-f]{64}$ && "$live_target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] ||
	die 'unsafe probe result'

mkdir -m 0700 "$evidence_dir"
evidence_dir="$(cd -- "$evidence_dir" && pwd -P)"
stage=
cleanup_stage() {
	[[ -z "${stage:-}" ]] || "${ssh_command[@]}" "$target" \
		"test ! -e '$stage' || rm -f -- '$stage'" >/dev/null 2>&1 || true
}
trap cleanup_stage EXIT HUP INT TERM

result=skipped-already-matching
if [[ "$already_current" == no ]]; then
	stage="$("${ssh_command[@]}" "$target" 'umask 077; mktemp /home/gemini/.gemini-provenance-preinit.XXXXXXXX')"
	stage=${stage//$'\r'/}
	[[ "$stage" =~ ^/home/gemini/\.gemini-provenance-preinit\.[A-Za-z0-9]+$ ]] ||
		die 'remote returned unsafe staging path'
	"${ssh_command[@]}" "$target" \
		"test -f '$stage' && test ! -L '$stage' && cat >'$stage' && chmod 600 '$stage'" \
		<"$candidate" || die 'candidate upload failed'
	write_output="$(remote_gate write "$predecessor_sha256" "$stage")" || die 'bounded boot2 write failed'
	printf '%s\n' "$write_output"
	"${ssh_command[@]}" "$target" "rm -f -- '$stage'"
	stage=
	result=write-synced-flushed-full-readback-verified
fi

post_output="$(remote_gate post "$predecessor_sha256" none)" || die 'final boot2 gate failed'
printf '%s\n' "$post_output"
readback_tmp="$evidence_dir/.boot2-readback.partial"
"${ssh_command[@]}" "$target" \
	"sudo -n dd if='$live_target' bs=4M iflag=fullblock count=4 status=none" \
	>"$readback_tmp" || die 'independent full readback stream failed'
[[ "$(wc -c <"$readback_tmp" | tr -d ' ')" == "$BOOT2_SIZE" ]] || die 'readback length mismatch'
readback_sha256="$(sha256sum "$readback_tmp" | awk '{print $1}')"
[[ "$readback_sha256" == "$CANDIDATE_SHA256" ]] || die 'independent readback checksum mismatch'
cmp -s "$candidate" "$readback_tmp" || die 'independent readback byte mismatch'
rm -f -- "$readback_tmp"

summary="$evidence_dir/deployment-summary.txt"
{
	printf 'experiment=2026-08-14-mt6797-runtime-provenance-observer\n'
	printf 'derivative=preinit-recovery-changed-kernel\n'
	printf 'result=%s\ntarget_logical_name=boot2\ntarget=%s\nroot=/dev/mmcblk0p29\n' "$result" "$live_target"
	printf 'predecessor_sha256=%s\nfresh_predecessor_backup=no\n' "$predecessor_sha256"
	printf 'candidate_sha256=%s\nreadback_sha256=%s\n' "$CANDIDATE_SHA256" "$readback_sha256"
	printf 'boot_id=%s\npower=%s\ntemporary_readback_removed=yes\n' "$initial_boot_id" "$power"
	printf 'shutdown=requested-after-evidence-flush\n'
} >"$summary"
chmod 0600 "$summary"
(cd "$evidence_dir" && sha256sum deployment-summary.txt >SHA256SUMS)
chmod 0600 "$evidence_dir/SHA256SUMS"
sync

set +e
"${ssh_command[@]}" "$target" 'sudo -n systemctl poweroff'
poweroff_rc=$?
set -e
unreachable=no
for _ in {1..20}; do
	if ! "${ssh_command[@]}" "$target" true >/dev/null 2>&1; then
		unreachable=yes
		break
	fi
	sleep 2
done
[[ "$unreachable" == yes ]] || die 'boot2 is verified but clean shutdown was not confirmed'
{
	printf 'poweroff_ssh_rc=%s\npost_shutdown_reachability=unreachable\n' "$poweroff_rc"
	printf 'reboot=no\nnext_action=owner-physically-selects-boot2\n'
} >>"$summary"
(cd "$evidence_dir" && sha256sum deployment-summary.txt >SHA256SUMS)
sync
trap - EXIT HUP INT TERM

printf 'result=%s\ncandidate_sha256=%s\nreadback_sha256=%s\n' "$result" "$CANDIDATE_SHA256" "$readback_sha256"
printf 'fresh_predecessor_backup=no\nshutdown=confirmed-unreachable\n'
printf 'evidence_dir=%s\n' "$evidence_dir"
