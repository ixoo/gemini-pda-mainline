#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline-config FILE --manifest FILE --package DIR --p-artifact DIR --q-artifact DIR\n' "$0" >&2
}

baseline_config=
manifest=
package=
p_artifact=
q_artifact=
while (($#)); do
	case "$1" in
		--baseline-config) baseline_config=$2; shift 2 ;;
		--manifest) manifest=$2; shift 2 ;;
		--package) package=$2; shift 2 ;;
		--p-artifact) p_artifact=$2; shift 2 ;;
		--q-artifact) q_artifact=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
for path in "$baseline_config" "$manifest" "$package" "$p_artifact" "$q_artifact"; do
	[[ -e "$path" ]] || die "required input missing: $path"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

expect_reject() {
	local label=$1
	shift
	if "$@" >"$workdir/$label.out" 2>"$workdir/$label.err"; then
		die "validator accepted mutation: $label"
	fi
	grep -Fq 'error:' "$workdir/$label.err" || die "mutation lacked validator error: $label"
}

# Positive controls establish that each validator accepts the exact artifact.
"$script_dir/validate-package-delta.py" --baseline-config "$baseline_config" \
	--candidate-package "$package" --manifest "$manifest" >/dev/null
"$script_dir/validate-dtb-delta.py" \
	--baseline "$p_artifact/mt6797-gemini-pda-fbcon-rotation.dtb" \
	--package "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	--candidate "$q_artifact/mt6797-gemini-pda-keyboard-shell.dtb" >/dev/null
"$script_dir/validate-initramfs-delta.sh" \
	"$p_artifact/gemini-fbcon-rotation-initramfs.img" \
	"$q_artifact/gemini-keyboard-shell-initramfs.img" >/dev/null
"$script_dir/validate-boot-delta.py" \
	--baseline "$p_artifact/gemini-fbcon-rotation.boot.img" \
	--candidate "$q_artifact/gemini-keyboard-shell.boot.img" \
	--image-gz "$package/Image.gz" \
	--dtb "$q_artifact/mt6797-gemini-pda-keyboard-shell.dtb" \
	--initramfs "$q_artifact/gemini-keyboard-shell-initramfs.img" >/dev/null

mutate() {
	local source=$1 destination=$2 offset=$3
	cp "$source" "$destination"
	printf '\001' | dd of="$destination" bs=1 seek="$offset" conv=notrunc status=none
}
mutate "$q_artifact/gemini-keyboard-shell.boot.img" "$workdir/bad.boot.img" 2048
expect_reject boot-byte "$script_dir/validate-boot-delta.py" \
	--baseline "$p_artifact/gemini-fbcon-rotation.boot.img" --candidate "$workdir/bad.boot.img" \
	--image-gz "$package/Image.gz" --dtb "$q_artifact/mt6797-gemini-pda-keyboard-shell.dtb" \
	--initramfs "$q_artifact/gemini-keyboard-shell-initramfs.img"
mutate "$q_artifact/mt6797-gemini-pda-keyboard-shell.dtb" "$workdir/bad.dtb" 64
expect_reject dtb-byte "$script_dir/validate-dtb-delta.py" \
	--baseline "$p_artifact/mt6797-gemini-pda-fbcon-rotation.dtb" \
	--package "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" --candidate "$workdir/bad.dtb"
mutate "$q_artifact/gemini-keyboard-shell-initramfs.img" "$workdir/bad-initramfs.img" 32
expect_reject initramfs-byte "$script_dir/validate-initramfs-delta.sh" \
	"$p_artifact/gemini-fbcon-rotation-initramfs.img" "$workdir/bad-initramfs.img"
mkdir -p "$workdir/package/provenance"
cp "$package/kernel.config" "$workdir/package/kernel.config"
cp "$package/provenance/build.json" "$workdir/package/provenance/build.json"
printf '\nCONFIG_I2C_CHARDEV=y\n' >>"$workdir/package/kernel.config"
expect_reject config-extra "$script_dir/validate-package-delta.py" \
	--baseline-config "$baseline_config" --candidate-package "$workdir/package" --manifest "$manifest"

printf 'validation=candidate-q-validator-mutations\n'
printf 'positive_controls=package,dtb,initramfs,android-v0\n'
printf 'rejected_mutations=boot-byte,dtb-byte,initramfs-byte,config-extra\n'
printf 'hardware_write=none\n'
