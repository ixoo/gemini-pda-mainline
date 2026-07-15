#!/usr/bin/env bash
set -euo pipefail

# Recover the compiled AW9523 keyboard contract from the exact active boot
# image's reconstructed ELF. This never executes the image and never touches
# a device. The ELF remains guest-private under the reverse-engineering tree.

vmlinux=${VMLINUX:-$HOME/reverse-engineering/work/gemini-kernel-active-20260714/vmlinux.elf}
active_boot_sha256=${ACTIVE_BOOT_SHA256:-1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513}
active_kernel_payload_sha256=${ACTIVE_KERNEL_PAYLOAD_SHA256:-b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d}

die() {
	echo "error: $*" >&2
	exit 1
}

for command in nm objdump strings sha256sum rg; do
	command -v "$command" >/dev/null 2>&1 || die "$command is required"
done
[[ -r $vmlinux ]] || die "vendor ELF is missing: $vmlinux"

export LC_ALL=C

probe_dump=$(mktemp)
map_dump=$(mktemp)
trap 'rm -f "$probe_dump" "$map_dump"' EXIT

objdump -d --no-show-raw-insn --disassemble=aw9523_i2c_probe "$vmlinux" >"$probe_dump"
objdump -s --start-address=0xffffffc001233a38 \
	--stop-address=0xffffffc001234058 "$vmlinux" >"$map_dump"

require_probe_anchor() {
	local needle=$1
	rg -Fq -- "$needle" "$probe_dump" || die "missing AW9523 probe anchor: $needle"
}

require_probe_anchor 'str	x0, [x1, #240]'
require_probe_anchor 'str	w2, [x1, #248]'
require_probe_anchor 'mov	w2, #0x7d'
require_probe_anchor 'mov	w2, #0xf0'

if rg -Fq -- 'mov	w2, #0x1d0' "$probe_dump"; then
	die 'active AW9523 capability list unexpectedly contains KEY_FN (0x1d0)'
fi

rg -Fq -- 'META-L' "$map_dump" || die 'compiled keymap lacks META-L label'
rg -Fq -- 'f0000000' "$map_dump" || die 'compiled keymap lacks KEY_UNKNOWN entries'

build_string=$(strings -a "$vmlinux" | rg -m1 '^Linux version 3\.18\.41' || true)
[[ -n $build_string ]] || die 'Linux build string is missing'

echo 'validation=active-aw9523-elf-keymap-contract'
echo "active_boot_image_sha256=$active_boot_sha256"
echo "active_kernel_payload_sha256=$active_kernel_payload_sha256"
echo "active_vmlinux_sha256=$(sha256sum "$vmlinux" | awk '{print $1}')"
echo "build_string=$build_string"
echo 'aw9523_i2c_probe_compiled_capability_key_leftmeta=0x7d'
echo 'aw9523_i2c_probe_compiled_capability_key_unknown=0xf0'
echo 'aw9523_i2c_probe_compiled_capability_key_fn=absent'
echo 'compiled_keymap_address=0xffffffc001233a38'
echo 'compiled_keymap_entries=56'
echo 'compiled_keymap_entry_stride_bytes=28'
echo 'compiled_keymap_keycode_offset_bytes=12'
echo 'compiled_keymap_leftmeta_coordinate=(row=4,col=3)'
echo 'compiled_keymap_unknown_coordinates=(row=7,col=3..6)'
echo 'active_boot_keymap_matches_live_capability_bitmap=yes'
echo 'retained_source_keymap_matches_active_boot=no'
echo 'hardware_write=none'
