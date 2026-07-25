#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

readonly BOOT2_SIZE=16777216
readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly X_RAW_SHA256=bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296
readonly X_RAW_SIZE=6864896
readonly X_PADDED_SHA256=e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855
readonly EXPECTED_CURRENT_W_PADDED_SHA256=0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608

usage() {
	cat <<'EOF'
usage: install-candidate-x-boot2.sh \
  --target USER@HOST \
  --candidate FILE \
  --backup-dir DIR

Install the calibrated, already validated Candidate X image to the live
GPT-resolved logical boot2 partition. The helper requires passwordless sudo
and the repository's mode-0600 Gemini SSH identity. It creates a private full
backup, pads the candidate to exactly 16 MiB, writes only boot2, syncs and
flushes, and requires matching full remote and local readbacks.

The candidate raw size/hash, padded hash, and exact current Candidate W
full-partition hash are source-pinned after final calibration; callers cannot
override them. The helper never accepts a password, never reboots, and never
selects boot2. DIR must be one new direct child of
artifacts/device-partitions/.
EOF
}

die() {
	printf 'error: %s\n' "$*" >&2
	exit 2
}

target=
candidate=
backup_dir=
while (($#)); do
	case "$1" in
	--target|--candidate|--backup-dir)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--target)
			[[ -z "$target" ]] || die '--target was provided more than once'
			target=$2
			;;
		--candidate)
			[[ -z "$candidate" ]] || die '--candidate was provided more than once'
			candidate=$2
			;;
		--backup-dir)
			[[ -z "$backup_dir" ]] || die '--backup-dir was provided more than once'
			backup_dir=$2
			;;
		esac
		shift 2
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage >&2
		die "unknown argument: $1"
		;;
	esac
done

[[ -n "$target" && -n "$candidate" && -n "$backup_dir" ]] || {
	usage >&2
	die 'all three explicit arguments are required'
}

calibration_values=(
	X_RAW_SHA256 X_RAW_SIZE X_PADDED_SHA256 EXPECTED_CURRENT_W_PADDED_SHA256
)
for name in "${calibration_values[@]}"; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in X_RAW_SHA256 X_PADDED_SHA256 EXPECTED_CURRENT_W_PADDED_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$X_RAW_SIZE" =~ ^[1-9][0-9]*$ ]] || die 'invalid calibrated X_RAW_SIZE'
((X_RAW_SIZE <= BOOT2_SIZE)) || \
	die 'calibrated Candidate X size exceeds logical boot2 capacity'
[[ "$X_PADDED_SHA256" != "$EXPECTED_CURRENT_W_PADDED_SHA256" ]] || \
	die 'Candidate X padded hash unexpectedly equals the Candidate W predecessor'

[[ "$target" =~ ^[A-Za-z_][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || \
	die 'target must be a simple USER@HOST value'
[[ "$candidate" != *$'\n'* && "$backup_dir" != *$'\n'* ]] || \
	die 'paths must be single-line values'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly script_dir
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
readonly experiment_dir
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
readonly repo_root
private_root="$repo_root/artifacts/device-partitions"
[[ -d "$private_root" && ! -L "$private_root" ]] || \
	die 'private device-partition artifact root is missing or unsafe'
private_root="$(cd -- "$private_root" && pwd -P)"
readonly private_root
identity="$repo_root/artifacts/credentials/gemini_ed25519"
readonly identity

for command in awk basename bash cat chmod cmp cp dd dirname git head mkdir mv od ssh stat \
	sync tail; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
	die 'required host SHA-256 command missing: sha256sum or shasum'
fi

file_size() {
	if stat -f '%z' "$1" >/dev/null 2>&1; then
		stat -f '%z' "$1"
	else
		stat -c '%s' "$1"
	fi
}

file_mode() {
	if stat -f '%Lp' "$1" >/dev/null 2>&1; then
		stat -f '%Lp' "$1"
	else
		stat -c '%a' "$1"
	fi
}

sha256_file() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | awk '{ print $1 }'
	else
		shasum -a 256 "$1" | awk '{ print $1 }'
	fi
}

checked_sha256_file() {
	local file=$1
	local hash
	hash="$(sha256_file "$file")" || die "cannot hash file: $file"
	[[ "$hash" =~ ^[0-9a-f]{64}$ ]] || die "malformed SHA-256 for file: $file"
	printf '%s\n' "$hash"
}

manifest_line() {
	local file=$1
	local hash
	local name
	hash="$(checked_sha256_file "$file")"
	name="$(basename -- "$file")" || die "cannot name manifest input: $file"
	printf '%s  %s\n' "$hash" "$name"
}

[[ -f "$identity" && ! -L "$identity" ]] || \
	die "missing regular Gemini identity: $identity"
[[ "$(file_mode "$identity")" == 600 ]] || die 'Gemini identity mode is not 0600'
[[ -f "$candidate" && ! -L "$candidate" ]] || \
	die 'candidate must be a regular non-symlink file'
candidate="$(cd -- "$(dirname -- "$candidate")" && pwd -P)/$(basename -- "$candidate")"
readonly candidate
candidate_dir="$(dirname -- "$candidate")"
candidate_name="$(basename -- "$candidate")"
candidate_manifest="$candidate_dir/SHA256SUMS"
readonly candidate_dir candidate_name candidate_manifest

[[ "$candidate_name" == gemini-keyboard-manual-reboot.boot.img ]] || \
	die 'candidate filename is not the exact Candidate X boot image name'
expected_artifact_name="candidate-X-keyboard-manual-reboot-final-${X_RAW_SHA256:0:8}"
[[ "$(basename -- "$candidate_dir")" == "$expected_artifact_name" ]] || \
	die "candidate directory is not the calibrated artifact: $expected_artifact_name"

candidate_size="$(file_size "$candidate")"
[[ "$candidate_size" == "$X_RAW_SIZE" ]] || die 'candidate raw size is not calibrated'
candidate_sha256="$(checked_sha256_file "$candidate")"
[[ "$candidate_sha256" == "$X_RAW_SHA256" ]] || \
	die 'candidate does not match the source-pinned Candidate X checksum'
[[ -f "$candidate_manifest" && ! -L "$candidate_manifest" ]] || \
	die 'candidate directory lacks a regular non-symlink SHA256SUMS manifest'
manifest_matches="$(awk -v name="$candidate_name" \
	'NF == 2 && ($2 == name || $2 == "./" name) { print $1 }' "$candidate_manifest")"
manifest_match_count="$(printf '%s\n' "$manifest_matches" | \
	awk 'NF { count++ } END { print count + 0 }')"
[[ "$manifest_match_count" == 1 && "$manifest_matches" == "$candidate_sha256" ]] || \
	die 'candidate SHA256SUMS entry is missing, duplicated, or mismatched'

case "$backup_dir" in
/*) ;;
*) backup_dir="$repo_root/$backup_dir" ;;
esac
[[ "$(dirname -- "$backup_dir")" == "$private_root" ]] || \
	die 'backup directory must be one direct child of artifacts/device-partitions/'
[[ "$backup_dir" != "$private_root" ]] || die 'refusing broad backup directory'
git -C "$repo_root" check-ignore -q "$backup_dir" || \
	die 'backup directory is not ignored by Git'
[[ ! -e "$backup_dir" && ! -L "$backup_dir" ]] || \
	die 'backup directory must not already exist'
mkdir -m 0700 "$backup_dir"
chmod 0700 "$backup_dir"
backup_dir="$(cd -- "$backup_dir" && pwd -P)"
[[ "$(dirname -- "$backup_dir")" == "$private_root" ]] || \
	die 'canonical backup directory escaped the private artifact root'
[[ "$(file_mode "$backup_dir")" == 700 ]] || die 'backup directory mode is not 0700'
readonly backup_dir

padded="$backup_dir/candidate-x-padded-boot2.img"
cp "$candidate" "$padded"
if ((X_RAW_SIZE < BOOT2_SIZE)); then
	dd if=/dev/zero of="$padded" bs=1 count=1 seek=$((BOOT2_SIZE - 1)) \
		conv=notrunc 2>/dev/null
fi
chmod 0600 "$padded"
[[ "$(file_size "$padded")" == "$BOOT2_SIZE" ]] || die 'padded candidate size mismatch'
head -c "$X_RAW_SIZE" "$padded" | cmp -s "$candidate" - || \
	die 'padded candidate prefix differs from raw candidate'
[[ "$(checked_sha256_file "$candidate")" == "$X_RAW_SHA256" ]] || \
	die 'raw candidate changed while its padded image was created'
tail_size=$((BOOT2_SIZE - X_RAW_SIZE))
if ((tail_size > 0)); then
	tail -c "$tail_size" "$padded" | od -An -v -tu1 | \
		awk '{ for (field = 1; field <= NF; field++) if ($field != 0) exit 1 }' || \
		die 'padded candidate tail is not all zero'
fi
padded_sha256="$(checked_sha256_file "$padded")"
[[ "$padded_sha256" == "$X_PADDED_SHA256" ]] || \
	die 'zero-padded Candidate X checksum is not calibrated'
sync
[[ "$(checked_sha256_file "$padded")" == "$X_PADDED_SHA256" ]] || \
	die 'padded Candidate X changed across initial sync'

target_user=${target%%@*}
remote_home="/home/$target_user"
remote_stage_prefix="$remote_home/.gemini-candidate-x."
readonly target_user remote_home remote_stage_prefix

valid_remote_stage() {
	local path=$1
	local suffix
	[[ "$path" == "$remote_stage_prefix"* ]] || return 1
	suffix=${path#"$remote_stage_prefix"}
	[[ "$suffix" =~ ^[A-Za-z0-9]+$ ]]
}

ssh_command=(
	ssh
	-o BatchMode=yes
	-o ConnectTimeout=10
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=60
	-o IdentitiesOnly=yes
	-o IdentityAgent=none
	-o StrictHostKeyChecking=yes
	-i "$identity"
)

result_field() {
	local name=$1
	local input=$2
	printf '%s\n' "$input" | awk -F= -v wanted="$name" \
		'$1 == wanted { print substr($0, length($1) + 2); found++ } END { exit found != 1 }'
}

"${ssh_command[@]}" "$target" \
	"for command in cat chmod mktemp readlink rm; do command -v \"\$command\" >/dev/null || exit 2; done; sudo -n -- true" || \
	die 'passwordless sudo, SSH authentication, or required remote user command is unavailable'

initial_state="$("${ssh_command[@]}" "$target" 'sudo -n -- /bin/bash -s' <<'REMOTE_INITIAL'
set -euo pipefail
export LC_ALL=C

for command in cat findmnt id lsblk readlink uname; do
	command -v "$command" >/dev/null 2>&1 || {
		printf 'error: initial remote command missing: %s\n' "$command" >&2
		exit 2
	}
done
[[ "$(id -u)" == 0 ]] || {
	printf 'error: initial remote state sampler is not root\n' >&2
	exit 2
}
[[ "$(uname -m)" == aarch64 ]] || {
	printf 'error: remote architecture is not aarch64\n' >&2
	exit 2
}

boot_id_before="$(cat /proc/sys/kernel/random/boot_id)"
root_source="$(findmnt -n -o SOURCE /)"
active_root="$(readlink -f "$root_source")"
[[ "$active_root" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && -b "$active_root" ]] || {
	printf 'error: active root is not one canonical MMC partition: %s\n' "$active_root" >&2
	exit 2
}
[[ "$(lsblk -dnro TYPE "$active_root")" == part && \
	"$(lsblk -dnro PKNAME "$active_root")" == mmcblk0 ]] || {
	printf 'error: active root is not a partition of the expected internal MMC\n' >&2
	exit 2
}
boot_id_after="$(cat /proc/sys/kernel/random/boot_id)"
[[ "$boot_id_before" == "$boot_id_after" ]] || {
	printf 'error: boot ID changed while sampling active root\n' >&2
	exit 2
}

printf 'boot_id=%s\n' "$boot_id_after"
printf 'root=%s\n' "$active_root"
REMOTE_INITIAL
)" || die 'failed to sample a stable canonical active root and boot ID'

initial_boot_id="$(result_field boot_id "$initial_state")" || \
	die 'initial state omitted a unique boot ID'
initial_root="$(result_field root "$initial_state")" || \
	die 'initial state omitted a unique canonical active root'
[[ "$initial_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || \
	die 'remote boot ID is malformed'
[[ "$initial_root" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] || \
	die 'remote canonical active root is malformed'
readonly initial_boot_id initial_root

remote_gate() {
	local mode=$1
	local expected_target=$2
	local expected_stage=$3
	"${ssh_command[@]}" "$target" \
		"sudo -n -- env GATE_MODE=$mode EXPECTED_BOOT_ID=$initial_boot_id EXPECTED_TARGET=$expected_target EXPECTED_STAGE=$expected_stage EXPECTED_OWNER=$target_user EXPECTED_ROOT=$initial_root EXPECTED_SIZE=$BOOT2_SIZE EXPECTED_CURRENT_SHA256=$EXPECTED_CURRENT_W_PADDED_SHA256 EXPECTED_CANDIDATE_SHA256=$X_PADDED_SHA256 /bin/bash -s" <<'REMOTE_GATE'
set -euo pipefail
export LC_ALL=C
umask 077

fail() {
	printf 'error: %s\n' "$*" >&2
	exit 2
}

[[ "$(id -u)" == 0 ]] || fail 'remote gate is not root'
[[ "$(uname -m)" == aarch64 ]] || fail 'remote architecture is not aarch64'
for command in awk blockdev cat chmod dd find findmnt id lsblk mktemp readlink rm rmdir \
	sha256sum sleep stat swapon sync uname; do
	command -v "$command" >/dev/null 2>&1 || fail "remote command missing: $command"
done

resolve_boot2() {
	local rows row_count
	rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | \
		awk '$2 == "boot2" { print }')"
	row_count="$(printf '%s\n' "$rows" | awk 'NF { count++ } END { print count + 0 }')"
	[[ "$row_count" == 1 ]] || fail "live GPT has $row_count exact boot2 rows"
	read -r target label type size ro mountpoint extra <<<"$rows"
	[[ "$target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] || fail "unsafe boot2 target: $target"
	[[ "$label" == boot2 && "$type" == part && "$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]] || \
		fail "boot2 identity mismatch: label=$label type=$type size=$size ro=$ro"
	[[ -z "${mountpoint:-}" && -z "${extra:-}" ]] || fail 'boot2 has a mountpoint'
	[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] || \
		fail 'boot2 by-partlabel disagrees with the live GPT row'
	[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 ]] || fail 'boot2 parent is not mmcblk0'
	[[ -b "$target" ]] || fail 'boot2 is not a block device'
	[[ -r "$target" && -w "$target" ]] || fail 'boot2 is not root-readable and writable'
	[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" ]] || \
		fail 'blockdev size mismatch'
	[[ "$(blockdev --getro "$target")" == 0 ]] || fail 'blockdev reports read-only'
	[[ "$(cat "/sys/class/block/${target##*/}/ro")" == 0 ]] || fail 'sysfs reports read-only'
	partition_number="$(cat "/sys/class/block/${target##*/}/partition")"
	[[ "$partition_number" =~ ^[0-9]+$ ]] || fail 'sysfs partition number is invalid'
}

check_active_root() {
	active_root_source="$(findmnt -n -o SOURCE /)"
	active_root="$(readlink -f "$active_root_source")"
	[[ "$active_root" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && -b "$active_root" ]] || \
		fail "active root is not one canonical MMC partition: $active_root"
	[[ "$active_root" == "$EXPECTED_ROOT" ]] || \
		fail "active root changed: expected=$EXPECTED_ROOT actual=$active_root"
	[[ "$active_root" != "$target" ]] || fail 'boot2 is the active root'
}

check_target_not_in_use() {
	local holder_entries mount_matches swap_canonical swap_device swap_devices target_majmin
	target_majmin="$(lsblk -dnro MAJ:MIN "$target")"
	[[ "$target_majmin" =~ ^[0-9]+:[0-9]+$ ]] || \
		fail 'boot2 major:minor identity is invalid'
	if ! mount_matches="$(awk -v target_majmin="$target_majmin" \
		'$3 == target_majmin { print }' /proc/self/mountinfo)"; then
		fail 'boot2 mount enumeration failed'
	fi
	[[ -z "$mount_matches" ]] || fail 'boot2 is mounted'
	if ! swap_devices="$(swapon --noheadings --raw --show=NAME)"; then
		fail 'swap enumeration failed'
	fi
	while IFS= read -r swap_device; do
		[[ -n "$swap_device" ]] || continue
		if ! swap_canonical="$(readlink -f "$swap_device")"; then
			fail "cannot canonicalize active swap device: $swap_device"
		fi
		[[ "$swap_canonical" != "$target" ]] || fail 'boot2 is active swap'
	done <<<"$swap_devices"
	if ! holder_entries="$(find "/sys/class/block/${target##*/}/holders" \
		-mindepth 1 -maxdepth 1 -print -quit)"; then
		fail 'boot2 holder enumeration failed'
	fi
	[[ -z "$holder_entries" ]] || fail 'boot2 has holders'
}

power_sample() {
	for path in \
		/sys/class/power_supply/ac/online \
		/sys/class/power_supply/battery/present \
		/sys/class/power_supply/battery/status \
		/sys/class/power_supply/battery/capacity \
		/sys/class/power_supply/battery/health; do
		[[ -r "$path" ]] || fail "power attribute unavailable: $path"
	done
	printf '%s|%s|%s|%s|%s' \
		"$(cat /sys/class/power_supply/ac/online)" \
		"$(cat /sys/class/power_supply/battery/present)" \
		"$(cat /sys/class/power_supply/battery/status)" \
		"$(cat /sys/class/power_supply/battery/capacity)" \
		"$(cat /sys/class/power_supply/battery/health)"
}

check_power_and_boot_id() {
	local power_first
	power_first="$(power_sample)"
	sleep 2
	power_second="$(power_sample)"
	[[ "$power_first" == '1|1|Full|100|Good' && "$power_second" == "$power_first" ]] || \
		fail "power is not stable and exact: first=$power_first second=$power_second"
	[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \
		fail 'boot ID changed during the power check'
}

validate_stage() {
	local stage_mode stage_owner stage_prefix stage_sha256 stage_size stage_suffix
	stage_prefix="/home/$EXPECTED_OWNER/.gemini-candidate-x."
	[[ "$EXPECTED_STAGE" == "$stage_prefix"* ]] || \
		fail 'remote staging path is outside the exact user-owned namespace'
	stage_suffix=${EXPECTED_STAGE#"$stage_prefix"}
	[[ "$stage_suffix" =~ ^[A-Za-z0-9]+$ ]] || fail 'remote staging suffix is unsafe'
	[[ -f "$EXPECTED_STAGE" && ! -L "$EXPECTED_STAGE" ]] || \
		fail 'remote staging object is not a regular non-symlink file'
	[[ "$(readlink -f "$EXPECTED_STAGE")" == "$EXPECTED_STAGE" ]] || \
		fail 'remote staging canonical path changed'
	read -r stage_owner stage_mode stage_size <<<"$(stat -c '%U %a %s' "$EXPECTED_STAGE")"
	[[ "$stage_owner" == "$EXPECTED_OWNER" && "$stage_mode" == 600 && \
		"$stage_size" == "$EXPECTED_SIZE" ]] || \
		fail "remote staging identity mismatch: owner=$stage_owner mode=$stage_mode size=$stage_size"
	stage_sha256="$(sha256sum "$EXPECTED_STAGE" | awk '{ print $1 }')"
	[[ "$stage_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
		fail 'remote staging checksum mismatch'
}

root_stage_dir=
root_stage_file=

valid_root_stage_dir() {
	local prefix=/run/.gemini-candidate-x-root.
	local suffix
	[[ "$root_stage_dir" == "$prefix"* ]] || return 1
	suffix=${root_stage_dir#"$prefix"}
	[[ "$suffix" =~ ^[A-Za-z0-9]+$ ]]
}

cleanup_root_stage() {
	local entries metadata owner mode
	[[ -n "$root_stage_dir" ]] || return 0
	valid_root_stage_dir || return 2
	[[ "$root_stage_file" == "$root_stage_dir/candidate.img" ]] || return 2
	if [[ ! -e "$root_stage_dir" && ! -L "$root_stage_dir" ]]; then
		return 0
	fi
	[[ -d "$root_stage_dir" && ! -L "$root_stage_dir" ]] || return 2
	[[ "$(readlink -f "$root_stage_dir")" == "$root_stage_dir" ]] || return 2
	metadata="$(stat -c '%U %a' "$root_stage_dir")" || return 2
	read -r owner mode <<<"$metadata" || return 2
	[[ "$owner" == root && "$mode" == 700 ]] || return 2
	if [[ -e "$root_stage_file" || -L "$root_stage_file" ]]; then
		[[ -f "$root_stage_file" && ! -L "$root_stage_file" ]] || return 2
		[[ "$(readlink -f "$root_stage_file")" == "$root_stage_file" ]] || return 2
		metadata="$(stat -c '%U %a' "$root_stage_file")" || return 2
		read -r owner mode <<<"$metadata" || return 2
		[[ "$owner" == root && "$mode" == 400 ]] || return 2
		rm -f -- "$root_stage_file" || return 2
	fi
	entries="$(find "$root_stage_dir" -mindepth 1 -maxdepth 1 -print -quit)" || return 2
	[[ -z "$entries" ]] || return 2
	rmdir -- "$root_stage_dir"
}

cleanup_root_stage_on_exit() {
	if ! cleanup_root_stage; then
		printf 'warning: exact root-owned staging cleanup failed: %s\n' \
			"${root_stage_dir:-unset}" >&2
	fi
}
trap cleanup_root_stage_on_exit EXIT

create_root_stage() {
	local metadata owner mode root_stage_sha256 root_stage_size run_owner
	[[ -d /run && ! -L /run && "$(readlink -f /run)" == /run ]] || \
		fail '/run is not a canonical real directory'
	run_owner="$(stat -c '%U' /run)" || fail 'cannot inspect /run ownership'
	[[ "$run_owner" == root ]] || fail '/run is not root-owned'
	root_stage_dir="$(mktemp -d /run/.gemini-candidate-x-root.XXXXXXXX)" || \
		fail 'cannot create a root-only staging directory'
	root_stage_file="$root_stage_dir/candidate.img"
	chmod 0700 "$root_stage_dir"
	valid_root_stage_dir || fail 'root staging directory name is unsafe'
	[[ "$(readlink -f "$root_stage_dir")" == "$root_stage_dir" ]] || \
		fail 'root staging directory canonical path changed'
	metadata="$(stat -c '%U %a' "$root_stage_dir")" || \
		fail 'cannot inspect root staging directory'
	read -r owner mode <<<"$metadata" || fail 'cannot parse root staging directory identity'
	[[ "$owner" == root && "$mode" == 700 ]] || \
		fail "root staging directory identity mismatch: owner=$owner mode=$mode"
	dd if="$EXPECTED_STAGE" of="$root_stage_file" bs=4M iflag=fullblock count=4 \
		conv=fsync status=none
	chmod 0400 "$root_stage_file"
	[[ -f "$root_stage_file" && ! -L "$root_stage_file" ]] || \
		fail 'root staging image is not a regular non-symlink file'
	[[ "$(readlink -f "$root_stage_file")" == "$root_stage_file" ]] || \
		fail 'root staging image canonical path changed'
	metadata="$(stat -c '%U %a %s' "$root_stage_file")" || \
		fail 'cannot inspect root staging image'
	read -r owner mode root_stage_size <<<"$metadata" || \
		fail 'cannot parse root staging image identity'
	[[ "$owner" == root && "$mode" == 400 && "$root_stage_size" == "$EXPECTED_SIZE" ]] || \
		fail "root staging identity mismatch: owner=$owner mode=$mode size=$root_stage_size"
	root_stage_sha256="$(sha256sum "$root_stage_file" | awk '{ print $1 }')"
	[[ "$root_stage_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
		fail 'root-owned immutable staging checksum mismatch'
}

resolve_boot2
check_active_root
check_target_not_in_use
boot_id_before="$(cat /proc/sys/kernel/random/boot_id)"
[[ "$boot_id_before" == "$EXPECTED_BOOT_ID" ]] || fail "boot ID changed: $boot_id_before"
check_power_and_boot_id
target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"

case "$GATE_MODE" in
probe)
	case "$target_sha256" in
	"$EXPECTED_CANDIDATE_SHA256") already_current=yes ;;
	"$EXPECTED_CURRENT_SHA256") already_current=no ;;
	*) fail "boot2 has unexpected full checksum: $target_sha256" ;;
	esac
	;;
write)
	[[ "$EXPECTED_TARGET" != none && "$target" == "$EXPECTED_TARGET" ]] || \
		fail "live boot2 target changed before write: $target"
	[[ "$target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || \
		fail "boot2 changed before write: $target_sha256"
	validate_stage
	create_root_stage
	resolve_boot2
	[[ "$target" == "$EXPECTED_TARGET" ]] || \
		fail "live boot2 target changed after staging: $target"
	check_active_root
	check_power_and_boot_id
	resolve_boot2
	[[ "$target" == "$EXPECTED_TARGET" ]] || \
		fail "live boot2 target changed at the final pre-write gate: $target"
	check_active_root
	check_target_not_in_use
	[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \
		fail 'boot ID changed immediately before write'
	prewrite_target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"
	[[ "$prewrite_target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || \
		fail "boot2 changed at the final pre-write checksum: $prewrite_target_sha256"
	dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4 \
		conv=fsync,notrunc status=none
	sync
	blockdev --flushbufs "$target"
	sync
	target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"
	[[ "$target_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
		fail "post-flush checksum mismatch: $target_sha256"
	[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \
		fail 'boot ID changed during write/flush'
	cleanup_root_stage || fail 'exact root-owned staging cleanup failed after write'
	root_stage_file=
	root_stage_dir=
	already_current=no
	;;
post)
	[[ "$EXPECTED_TARGET" != none && "$target" == "$EXPECTED_TARGET" ]] || \
		fail "live boot2 target changed after write: $target"
	[[ "$target_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || \
		fail "post-write boot2 checksum mismatch: $target_sha256"
	already_current=yes
	;;
*)
	fail "invalid gate mode: $GATE_MODE"
	;;
esac

printf 'gate=passed\n'
printf 'mode=%s\n' "$GATE_MODE"
printf 'target=%s\n' "$target"
printf 'partition_number=%s\n' "$partition_number"
printf 'size=%s\n' "$size"
printf 'root=%s\n' "$active_root"
printf 'boot_id=%s\n' "$EXPECTED_BOOT_ID"
printf 'power=%s\n' "$power_second"
printf 'target_sha256=%s\n' "$target_sha256"
printf 'already_current=%s\n' "$already_current"
REMOTE_GATE
}

printf 'candidate_sha256=%s\n' "$candidate_sha256"
printf 'candidate_size=%s\n' "$candidate_size"
printf 'padded_sha256=%s\n' "$padded_sha256"
printf 'padded_size=%s\n' "$BOOT2_SIZE"

probe_output="$(remote_gate probe none none)" || die 'initial live boot2 gate failed'
printf '%s\n' "$probe_output"
live_target="$(result_field target "$probe_output")" || die 'probe omitted unique target'
[[ "$live_target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] || die 'probe returned unsafe target'
probe_sha256="$(result_field target_sha256 "$probe_output")" || die 'probe omitted checksum'
already_current="$(result_field already_current "$probe_output")" || die 'probe omitted skip state'

summary="$backup_dir/deployment-summary.txt"
manifest="$backup_dir/SHA256SUMS"
if [[ "$already_current" == yes ]]; then
	{
		printf 'experiment=2026-07-19-keyboard-manual-reboot-diagnostic\n'
		printf 'candidate_label=X\noperation=boot2-install\nresult=skipped-already-matching\n'
		printf 'target=%s\nroot=%s\n' "$live_target" "$initial_root"
		printf 'candidate_raw_sha256=%s\n' "$candidate_sha256"
		printf 'candidate_padded_sha256=%s\n' "$padded_sha256"
		printf 'target_sha256=%s\n' "$probe_sha256"
		printf 'boot_id=%s\nreboot_or_shutdown_performed=no\nruntime_result=not-tested\n' \
			"$initial_boot_id"
	} >"$summary"
	chmod 0600 "$summary"
	{
		manifest_line "$padded"
		manifest_line "$summary"
	} >"$manifest"
	chmod 0600 "$manifest"
	skip_manifest_sha256="$(checked_sha256_file "$manifest")"
	sync
	[[ "$(checked_sha256_file "$manifest")" == "$skip_manifest_sha256" ]] || \
		die 'skipped-write evidence manifest changed across sync'
	printf 'result=skipped-already-matching\n'
	printf 'backup_dir=%s\nreboot=none\nruntime_result=not-tested\n' "$backup_dir"
	exit 0
fi
[[ "$already_current" == no && "$probe_sha256" == "$EXPECTED_CURRENT_W_PADDED_SHA256" ]] || \
	die 'initial gate returned an inconsistent Candidate W predecessor checksum'

backup_partial="$backup_dir/boot2-before-candidate-x.img.partial"
backup="$backup_dir/boot2-before-candidate-x.img"
if ! "${ssh_command[@]}" "$target" \
	"sudo -n -- dd if='$live_target' bs=4M iflag=fullblock count=4 status=none" \
	>"$backup_partial"; then
	die "boot2 backup stream failed; inspect $backup_partial"
fi
chmod 0600 "$backup_partial"
[[ "$(file_size "$backup_partial")" == "$BOOT2_SIZE" ]] || \
	die "boot2 backup is short; inspect $backup_partial"
backup_sha256="$(checked_sha256_file "$backup_partial")"
[[ "$backup_sha256" == "$EXPECTED_CURRENT_W_PADDED_SHA256" ]] || \
	die "boot2 backup checksum mismatch; inspect $backup_partial"
mv "$backup_partial" "$backup"
backup_checksum_file="$backup_dir/boot2-before-candidate-x.img.sha256"
printf '%s  %s\n' "$backup_sha256" "$(basename -- "$backup")" >"$backup_checksum_file"
chmod 0600 "$backup_checksum_file"
sync
[[ "$(checked_sha256_file "$backup")" == "$backup_sha256" ]] || \
	die 'durably flushed pre-write backup failed checksum revalidation'
[[ "$(cat "$backup_checksum_file")" == "$backup_sha256  $(basename -- "$backup")" ]] || \
	die 'durably flushed pre-write backup checksum sidecar changed'
[[ "$(checked_sha256_file "$candidate")" == "$X_RAW_SHA256" && \
	"$(file_size "$candidate")" == "$X_RAW_SIZE" ]] || \
	die 'raw candidate changed before remote staging'
[[ "$(checked_sha256_file "$padded")" == "$X_PADDED_SHA256" ]] || \
	die 'padded candidate changed before remote staging'

readback_partial="$backup_dir/boot2-after-candidate-x.img.partial"
readback="$backup_dir/boot2-after-candidate-x.img"
readback_stats="$backup_dir/boot2-after-candidate-x.dd.txt"
dd if=/dev/zero of="$readback_partial" bs=1048576 count=16 conv=fsync
chmod 0600 "$readback_partial"
: >"$readback_stats"
chmod 0600 "$readback_stats"
[[ "$(file_size "$readback_partial")" == "$BOOT2_SIZE" ]] || \
	die 'cannot reserve exact local capacity for the full post-write readback'
sync

remote_stage="$("${ssh_command[@]}" "$target" \
	"umask 077; stage=\$(mktemp '$remote_home/.gemini-candidate-x.XXXXXXXX') || exit 2; chmod 600 \"\$stage\"; printf '%s\\n' \"\$stage\"")"
remote_stage=${remote_stage//$'\r'/}
valid_remote_stage "$remote_stage" || die 'remote mktemp returned an unsafe staging path'

remove_remote_stage() {
	[[ -n "${remote_stage:-}" ]] || return 0
	valid_remote_stage "$remote_stage" || return 2
	"${ssh_command[@]}" "$target" \
		"if test ! -e '$remote_stage' && test ! -L '$remote_stage'; then exit 0; fi; test -f '$remote_stage' && test ! -L '$remote_stage' && test \"\$(readlink -f '$remote_stage')\" = '$remote_stage' && rm -f -- '$remote_stage'"
}

cleanup_stage() {
	if ! remove_remote_stage >/dev/null 2>&1; then
		printf 'warning: exact remote user staging cleanup failed: %s\n' \
			"${remote_stage:-unset}" >&2
	fi
}
trap cleanup_stage EXIT

"${ssh_command[@]}" "$target" \
	"test -f '$remote_stage' && test ! -L '$remote_stage' && cat > '$remote_stage' && chmod 600 '$remote_stage'" \
	<"$padded" || die 'remote staging upload failed'

write_output="$(remote_gate write "$live_target" "$remote_stage")" || \
	die 'immediate pre-write gate or bounded write failed'
printf '%s\n' "$write_output"
write_target="$(result_field target "$write_output")" || die 'write result omitted target'
[[ "$write_target" == "$live_target" ]] || die 'write result target differs from probed target'
write_sha256="$(result_field target_sha256 "$write_output")" || die 'write result omitted checksum'
[[ "$write_sha256" == "$X_PADDED_SHA256" ]] || die 'remote post-flush checksum mismatch'

if ! "${ssh_command[@]}" "$target" \
	"sudo -n -- dd if='$write_target' bs=4M iflag=fullblock count=4 status=none" | \
	dd of="$readback_partial" bs=1048576 conv=notrunc 2>"$readback_stats"; then
	chmod 0600 "$readback_stats"
	die "full boot2 readback failed; inspect $readback_partial"
fi
chmod 0600 "$readback_stats"
readback_stream_bytes="$(awk '$2 == "bytes" { bytes = $1; count++ } \
	END { if (count == 1) print bytes; else exit 1 }' "$readback_stats")" || \
	die "cannot prove the full readback stream length; inspect $readback_stats"
[[ "$readback_stream_bytes" == "$BOOT2_SIZE" ]] || \
	die "full boot2 readback stream length mismatch; inspect $readback_stats"
chmod 0600 "$readback_partial"
[[ "$(file_size "$readback_partial")" == "$BOOT2_SIZE" ]] || \
	die "full boot2 readback is short; inspect $readback_partial"
readback_sha256="$(checked_sha256_file "$readback_partial")"
[[ "$readback_sha256" == "$X_PADDED_SHA256" ]] || \
	die "full boot2 readback checksum mismatch; inspect $readback_partial"
cmp -s "$padded" "$readback_partial" || \
	die "full boot2 readback differs byte-for-byte; inspect $readback_partial"
mv "$readback_partial" "$readback"
readback_checksum_file="$backup_dir/boot2-after-candidate-x.img.sha256"
printf '%s  %s\n' "$readback_sha256" "$(basename -- "$readback")" >"$readback_checksum_file"
chmod 0600 "$readback_checksum_file"
sync
[[ "$(checked_sha256_file "$readback")" == "$readback_sha256" ]] || \
	die 'durably flushed full local readback failed checksum revalidation'
[[ "$(cat "$readback_checksum_file")" == "$readback_sha256  $(basename -- "$readback")" ]] || \
	die 'durably flushed readback checksum sidecar changed'

post_output="$(remote_gate post "$write_target" "$remote_stage")" || \
	die 'final live boot2/root/power/boot-ID gate failed'
printf '%s\n' "$post_output"
post_sha256="$(result_field target_sha256 "$post_output")" || die 'post gate omitted checksum'
[[ "$post_sha256" == "$X_PADDED_SHA256" ]] || die 'final target checksum mismatch'

remove_remote_stage || \
	die 'verified write succeeded, but the exact regular remote staging file could not be removed'
"${ssh_command[@]}" "$target" "test ! -e '$remote_stage' && test ! -L '$remote_stage'" || \
	die 'verified write succeeded, but the remote staging path still exists'
remote_stage=
trap - EXIT

{
	printf 'experiment=2026-07-19-keyboard-manual-reboot-diagnostic\n'
	printf 'candidate_label=X\noperation=standing-latest-validated-candidate-boot2-sync\n'
	printf 'result=write-synced-flushed-full-readback-verified\n'
	printf 'target_logical_name=boot2\ntarget=%s\nroot=%s\n' "$write_target" "$initial_root"
	printf 'candidate_raw_path=%s\n' "$candidate"
	printf 'candidate_raw_size=%s\ncandidate_raw_sha256=%s\n' "$candidate_size" "$candidate_sha256"
	printf 'candidate_padded_size=%s\ncandidate_padded_sha256=%s\n' \
		"$BOOT2_SIZE" "$padded_sha256"
	printf 'expected_previous_label=W\nexpected_previous_sha256=%s\nbackup_sha256=%s\n' \
		"$EXPECTED_CURRENT_W_PADDED_SHA256" "$backup_sha256"
	printf 'remote_post_flush_sha256=%s\nlocal_readback_sha256=%s\n' \
		"$write_sha256" "$readback_sha256"
	printf 'local_readback_stream_bytes=%s\n' "$readback_stream_bytes"
	printf 'boot_id=%s\npower=1|1|Full|100|Good\n' "$initial_boot_id"
	printf 'remote_staging_removed=yes\nreboot_or_shutdown_performed=no\nruntime_result=not-tested\n'
} >"$summary"
chmod 0600 "$summary"

{
	for file in "$padded" "$backup" "$backup_checksum_file" "$readback" \
		"$readback_checksum_file" "$readback_stats" "$summary"; do
		manifest_line "$file"
	done
} >"$manifest"
chmod 0600 "$manifest"
final_summary_sha256="$(checked_sha256_file "$summary")"
final_manifest_sha256="$(checked_sha256_file "$manifest")"
sync
[[ "$(checked_sha256_file "$summary")" == "$final_summary_sha256" && \
	"$(checked_sha256_file "$manifest")" == "$final_manifest_sha256" ]] || \
	die 'final private deployment evidence changed across sync'

printf 'result=write-synced-flushed-full-readback-verified\n'
printf 'target=%s\n' "$write_target"
printf 'candidate_padded_sha256=%s\n' "$padded_sha256"
printf 'backup_sha256=%s\nreadback_sha256=%s\n' "$backup_sha256" "$readback_sha256"
printf 'evidence_manifest_sha256=%s\n' "$final_manifest_sha256"
printf 'backup_dir=%s\nreboot=none\nruntime_result=not-tested\n' "$backup_dir"
