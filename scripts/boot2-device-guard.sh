#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only Linux block-identity gate. Source this library in the same remote
# shell as a reviewed installer, or invoke --check explicitly. No write API.

# BOOT2_DEVICE_GUARD_LIBRARY_BEGIN
_boot2_guard_fail() {
	printf 'boot2 device guard: %s\n' "$*" >&2
	return 1
}

_boot2_guard_valid_id() {
	local major minor
	[[ "$1" =~ ^([1-9][0-9]{0,3}):(0|[1-9][0-9]{0,6})$ ]] || return 1
	major=${BASH_REMATCH[1]}
	minor=${BASH_REMATCH[2]}
	((major <= 4095 && minor <= 1048575))
}

_boot2_guard_device_id() {
	local record major minor
	record=$(stat -L -c '%F|%t:%T' -- "$1") ||
		{ _boot2_guard_fail 'cannot stat block device'; return 1; }
	[[ "$record" =~ ^block\ special\ file\|([0-9a-f]{1,8}):([0-9a-f]{1,8})$ ]] ||
		{ _boot2_guard_fail 'device is not an identifiable block node'; return 1; }
	major=$((16#${BASH_REMATCH[1]}))
	minor=$((16#${BASH_REMATCH[2]}))
	_boot2_guard_valid_id "$major:$minor" ||
		{ _boot2_guard_fail 'invalid block device number'; return 1; }
	printf '%s:%s\n' "$major" "$minor"
}

_boot2_guard_sysfs_device() {
	local number=$1 sys_path name recorded node_number class_path
	_boot2_guard_valid_id "$number" || return 1
	sys_path=$(readlink -f -- "/sys/dev/block/$number") ||
		{ _boot2_guard_fail 'cannot resolve sysfs block identity'; return 1; }
	[[ "$sys_path" == /sys/devices/* && "$sys_path" != *'/../'* ]] ||
		{ _boot2_guard_fail 'unresolved sysfs block identity'; return 1; }
	name=${sys_path##*/}
	[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] ||
		{ _boot2_guard_fail 'malformed sysfs block name'; return 1; }
	class_path=$(readlink -f -- "/sys/class/block/$name") || return 1
	[[ "$class_path" == "$sys_path" ]] ||
		{ _boot2_guard_fail 'sysfs class identity disagrees'; return 1; }
	recorded=$(cat -- "$sys_path/dev") ||
		{ _boot2_guard_fail 'missing sysfs device number'; return 1; }
	[[ "$recorded" == "$number" ]] ||
		{ _boot2_guard_fail 'sysfs device number disagrees'; return 1; }
	node_number=$(_boot2_guard_device_id "/dev/$name") || return 1
	[[ "$node_number" == "$number" ]] ||
		{ _boot2_guard_fail 'device node and sysfs disagree'; return 1; }
	printf '/dev/%s\n' "$name"
}

_boot2_guard_mount_root() {
	# Only kernel device numbers decide mount ownership. The source field may
	# legitimately be /dev/root, an alias, or unrelated text for a bind mount.
	awk -v target="$1" -v disk="$2" '
	function refuse() { bad = 1; exit 1 }
	function numeric(s) { return s ~ /^(0|[1-9][0-9]*)$/ }
	function device(s, a) {
		if (split(s, a, ":") != 2 || !numeric(a[1]) || !numeric(a[2]))
			return 0
		return a[1] <= 4095 && a[2] <= 1048575
	}
	{
		if (NF < 10 || !numeric($1) || $1 == 0 || !numeric($2) ||
		    !device($3) || $4 !~ /^\// || $5 !~ /^\// || seen[$1]++)
			refuse()
		separator = 0
		for (i = 7; i <= NF; i++) {
			if ($i == "-") {
				if (separator) refuse()
				separator = i
			}
		}
		if (!separator || separator + 3 != NF) refuse()
		if ($3 == target || $3 == disk) refuse()
		if ($5 == "/") { roots++; root = $3 }
		rows++
	}
	END {
		if (bad || !rows || roots != 1 || root ~ /^0:/) exit 1
		print root
	}'
}

_boot2_guard_holders() {
	local holders
	holders=$(find "/sys/dev/block/$1/holders" -mindepth 1 -maxdepth 1 -print) ||
		{ _boot2_guard_fail 'cannot inspect holders'; return 1; }
	[[ -z "$holders" ]] ||
		{ _boot2_guard_fail 'target has a block-device holder'; return 1; }
}

boot2_device_guard() (
	# A subshell keeps locale and local observations out of the caller. Every
	# failed command is checked explicitly, including when invoked from an if.
	export LC_ALL=C
	local target=${1:-} expected=${2:-} expected_root=${3:-}
	local command target_id root_id root_device mountinfo swaps swap swap_id
	local self_ns init_ns later_root later_id canonical_target swap_table
	local target_sys partition parent_id
	[[ $# == 2 || $# == 3 ]] ||
		{ _boot2_guard_fail 'require TARGET EXPECTED_MAJOR:MINOR [EXPECTED_ROOT_MAJOR:MINOR]'; return 1; }
	[[ "$target" == /dev/* && "$target" != *$'\n'* && "$target" != *$'\r'* ]] ||
		{ _boot2_guard_fail 'require an explicit device path'; return 1; }
	_boot2_guard_valid_id "$expected" ||
		{ _boot2_guard_fail 'malformed expected target number'; return 1; }
	[[ $# == 2 ]] || _boot2_guard_valid_id "$expected_root" ||
		{ _boot2_guard_fail 'malformed expected root number'; return 1; }
	for command in awk cat find readlink stat; do
		command -v "$command" >/dev/null 2>&1 ||
			{ _boot2_guard_fail "missing command: $command"; return 1; }
	done
	self_ns=$(readlink -- /proc/self/ns/mnt) || return 1
	init_ns=$(readlink -- /proc/1/ns/mnt) || return 1
	[[ "$self_ns" =~ ^mnt:\[[0-9]+\]$ && "$self_ns" == "$init_ns" ]] ||
		{ _boot2_guard_fail 'not in the init mount namespace'; return 1; }
	target_id=$(_boot2_guard_device_id "$target") || return 1
	[[ "$target_id" == "$expected" ]] ||
		{ _boot2_guard_fail 'target device number changed'; return 1; }
	canonical_target=$(_boot2_guard_sysfs_device "$target_id") || return 1
	target_sys=$(readlink -f -- "/sys/dev/block/$target_id") || return 1
	partition=$(cat -- "$target_sys/partition") ||
		{ _boot2_guard_fail 'target is not a verified partition'; return 1; }
	[[ "$partition" =~ ^[1-9][0-9]*$ ]] ||
		{ _boot2_guard_fail 'invalid partition identity'; return 1; }
	parent_id=$(cat -- "${target_sys%/*}/dev") ||
		{ _boot2_guard_fail 'missing parent block identity'; return 1; }
	_boot2_guard_valid_id "$parent_id" && [[ "$parent_id" != "$target_id" ]] ||
		{ _boot2_guard_fail 'invalid parent block identity'; return 1; }
	_boot2_guard_sysfs_device "$parent_id" >/dev/null || return 1
	mountinfo=$(cat -- /proc/self/mountinfo) ||
		{ _boot2_guard_fail 'cannot read mountinfo'; return 1; }
	root_id=$(_boot2_guard_mount_root "$target_id" "$parent_id" <<<"$mountinfo") ||
		{ _boot2_guard_fail 'mounted target or malformed/unresolved root mountinfo'; return 1; }
	[[ -z "$expected_root" || "$root_id" == "$expected_root" ]] ||
		{ _boot2_guard_fail 'root device number changed'; return 1; }
	root_device=$(_boot2_guard_sysfs_device "$root_id") || return 1
	_boot2_guard_holders "$target_id" || return 1
	_boot2_guard_holders "$parent_id" || return 1
	swap_table=$(cat -- /proc/swaps) ||
		{ _boot2_guard_fail 'cannot read active swaps'; return 1; }
	swaps=$(awk '
		NR == 1 {
			if (NF != 5 || $1 != "Filename" || $2 != "Type" ||
			    $3 != "Size" || $4 != "Used" || $5 != "Priority") exit 1
			next
		}
		{
			if (NF != 5 || $1 !~ /^\/dev\// || $1 ~ /\\/ ||
			    $2 != "partition" || $3 !~ /^[0-9]+$/ ||
			    $4 !~ /^[0-9]+$/ || $5 !~ /^-?[0-9]+$/) exit 1
			print $1
		}
		END { if (!NR) exit 1 }
	' <<<"$swap_table") ||
		{ _boot2_guard_fail 'malformed or unsupported swap identity'; return 1; }
	while IFS= read -r swap; do
		[[ -n "$swap" ]] || continue
		swap_id=$(_boot2_guard_device_id "$swap") || return 1
		[[ "$swap_id" != "$target_id" && "$swap_id" != "$parent_id" ]] ||
			{ _boot2_guard_fail 'target is active swap'; return 1; }
	done <<<"$swaps"
	# Revalidate after collecting the other evidence. This detects changes
	# during collection; it does not lock out later mounts or other namespaces.
	mountinfo=$(cat -- /proc/self/mountinfo) || return 1
	later_root=$(_boot2_guard_mount_root "$target_id" "$parent_id" <<<"$mountinfo") ||
		{ _boot2_guard_fail 'mount state changed or is invalid'; return 1; }
	later_id=$(_boot2_guard_device_id "$target") || return 1
	[[ "$later_root" == "$root_id" && "$later_id" == "$target_id" ]] ||
		{ _boot2_guard_fail 'device identity changed during collection'; return 1; }
	_boot2_guard_sysfs_device "$root_id" >/dev/null || return 1
	_boot2_guard_holders "$target_id" || return 1
	_boot2_guard_holders "$parent_id" || return 1
	swaps=$(cat -- /proc/swaps) || return 1
	[[ "$swaps" == "$swap_table" ]] ||
		{ _boot2_guard_fail 'swap state changed during collection'; return 1; }
	printf 'boot2_device_guard=passed\ntarget_device=%s\ntarget_major_minor=%s\n' \
		"$canonical_target" "$target_id"
	printf 'root_device=%s\nroot_major_minor=%s\n' "$root_device" "$root_id"
)
# BOOT2_DEVICE_GUARD_LIBRARY_END

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	if [[ ${1:-} == --check && ($# == 3 || $# == 4) ]]; then
		shift
		boot2_device_guard "$@"
	else
		printf 'usage: %s --check TARGET EXPECTED_MAJOR:MINOR [EXPECTED_ROOT_MAJOR:MINOR]\n' "$0" >&2
		[[ ${1:-} == --help && $# == 1 ]] || exit 2
	fi
fi
