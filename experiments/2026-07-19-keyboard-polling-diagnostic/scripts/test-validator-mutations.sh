#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline-config FILE --manifest FILE --package DIR --p-artifact DIR --u-artifact DIR\n' "$0" >&2
}

baseline_config=
manifest=
package=
p_artifact=
u_artifact=
while (($#)); do
	case "$1" in
		--baseline-config) baseline_config=$2; shift 2 ;;
		--manifest) manifest=$2; shift 2 ;;
		--package) package=$2; shift 2 ;;
		--p-artifact) p_artifact=$2; shift 2 ;;
		--u-artifact) u_artifact=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
for path in "$baseline_config" "$manifest" "$package" "$p_artifact" "$u_artifact"; do
	[[ -e "$path" ]] || die "required input missing: $path"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
package_validator="$repo_root/experiments/2026-07-18-keyboard-shell-diagnostic/scripts/validate-package-delta.py"
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

validate_package() {
	"$package_validator" --baseline-config "$baseline_config" \
		--candidate-package "$1" --manifest "$manifest" \
		--expected-profile observability-fbcon-rotation-keyboard-polling
}

# Positive controls establish that each validator accepts the exact artifact.
validate_package "$package" >/dev/null
"$script_dir/validate-dtb-delta.py" \
	--baseline "$p_artifact/mt6797-gemini-pda-fbcon-rotation.dtb" \
	--package "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	--candidate "$u_artifact/mt6797-gemini-pda-keyboard-polling.dtb" >/dev/null
"$script_dir/validate-initramfs-delta.sh" \
	"$p_artifact/gemini-fbcon-rotation-initramfs.img" \
	"$u_artifact/gemini-keyboard-polling-initramfs.img" >/dev/null
"$script_dir/validate-boot-delta.py" \
	--baseline "$p_artifact/gemini-fbcon-rotation.boot.img" \
	--candidate "$u_artifact/gemini-keyboard-polling.boot.img" \
	--image-gz "$package/Image.gz" \
	--dtb "$u_artifact/mt6797-gemini-pda-keyboard-polling.dtb" \
	--initramfs "$u_artifact/gemini-keyboard-polling-initramfs.img" >/dev/null

mutate() {
	local source=$1 destination=$2 offset=$3
	cp "$source" "$destination"
	printf '\001' | dd of="$destination" bs=1 seek="$offset" conv=notrunc status=none
}
mutate "$u_artifact/gemini-keyboard-polling.boot.img" "$workdir/bad.boot.img" 2048
expect_reject boot-byte "$script_dir/validate-boot-delta.py" \
	--baseline "$p_artifact/gemini-fbcon-rotation.boot.img" --candidate "$workdir/bad.boot.img" \
	--image-gz "$package/Image.gz" --dtb "$u_artifact/mt6797-gemini-pda-keyboard-polling.dtb" \
	--initramfs "$u_artifact/gemini-keyboard-polling-initramfs.img"
mutate "$u_artifact/mt6797-gemini-pda-keyboard-polling.dtb" "$workdir/bad.dtb" 64
expect_reject dtb-byte "$script_dir/validate-dtb-delta.py" \
	--baseline "$p_artifact/mt6797-gemini-pda-fbcon-rotation.dtb" \
	--package "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" --candidate "$workdir/bad.dtb"
mutate "$u_artifact/gemini-keyboard-polling-initramfs.img" "$workdir/bad-initramfs.img" 32
expect_reject initramfs-byte "$script_dir/validate-initramfs-delta.sh" \
	"$p_artifact/gemini-fbcon-rotation-initramfs.img" "$workdir/bad-initramfs.img"
mkdir -p "$workdir/package/provenance"
cp "$package/kernel.config" "$workdir/package/kernel.config"
cp "$package/provenance/build.json" "$workdir/package/provenance/build.json"
printf '\nCONFIG_I2C_CHARDEV=y\n' >>"$workdir/package/kernel.config"
expect_reject config-extra validate_package "$workdir/package"

printf 'validation=candidate-u-validator-mutations\n'
printf 'positive_controls=package,dtb,initramfs,android-v0\n'
printf 'rejected_mutations=boot-byte,dtb-byte,initramfs-byte,config-extra\n'
printf 'hardware_write=none\n'
