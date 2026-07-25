#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --p-artifact DIR --v-artifact DIR\n' "$0" >&2
}

package=
p_artifact=
v_artifact=
while (($#)); do
	case "$1" in
	--package|--p-artifact|--v-artifact)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--p-artifact) p_artifact=$2 ;;
		--v-artifact) v_artifact=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
for directory in "$package" "$p_artifact" "$v_artifact"; do
	[[ -d "$directory" ]] || die "required directory missing: $directory"
done
for command in awk basename chmod cp dd fdtput file find grep gzip jq mkdir \
	mktemp mv python3 readelf rm sha256sum sort strings wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
manifest="$repo_root/kernel/manifest.json"
artifact_validator="$repo_root/scripts/validate-kernel-artifact"
package_validator="$script_dir/validate-package-foundation.py"
patch_validator="$script_dir/validate-corrected-polling-patch.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
polling_patch="$repo_root/patches/v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch"

p_dtb="$p_artifact/mt6797-gemini-pda-fbcon-rotation.dtb"
p_initramfs="$p_artifact/gemini-fbcon-rotation-initramfs.img"
oracle="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
image_gz="$package/Image.gz"
candidate_dtb="$v_artifact/mt6797-gemini-pda-keyboard-watchdog.dtb"
candidate_initramfs="$v_artifact/gemini-keyboard-watchdog-initramfs.img"
candidate_boot="$v_artifact/gemini-keyboard-watchdog.boot.img"
helper="$v_artifact/input-event-capture"
for input in "$manifest" "$artifact_validator" "$package_validator" \
	"$patch_validator" "$dtb_validator" "$initramfs_validator" \
	"$boot_validator" "$polling_patch" "$p_dtb" "$p_initramfs" "$oracle" \
	"$image_gz" "$candidate_dtb" "$candidate_initramfs" "$candidate_boot" \
	"$helper" "$v_artifact/SHA256SUMS"; do
	[[ -s "$input" ]] || die "required validator input missing: $input"
done
[[ -x "$helper" ]] || die "selected helper is not executable"

workdir="$(mktemp -d "${TMPDIR:-/tmp}/candidate-v-mutations.XXXXXX")"
cleanup() { rm -rf "$workdir"; }
trap cleanup EXIT
rejections="$workdir/rejections"
: >"$rejections"

expect_reject() {
	local label=$1
	shift
	if "$@" >"$workdir/$label.out" 2>"$workdir/$label.err"; then
		die "validator accepted mutation: $label"
	fi
	grep -Fq 'error:' "$workdir/$label.err" || \
		die "mutation rejection lacked an explicit validator error: $label"
	printf '%s\n' "$label" >>"$rejections"
}

validate_package() {
	"$package_validator" --package "$1" --manifest "${2:-$manifest}"
}

validate_dtb() {
	"$dtb_validator" --baseline-p "$1" --package-oracle "$2" --candidate "$3"
}

validate_initramfs() {
	"$initramfs_validator" --baseline "$p_initramfs" --candidate "$1" --helper "$2"
}

validate_boot() {
	"$boot_validator" --candidate "$1" --image-gz "$2" --dtb "$3" --initramfs "$4"
}

copy_and_append() {
	cp "$1" "$2"
	printf '\001' >>"$2"
}

mutated_dtb() {
	local label=$1
	cp "$candidate_dtb" "$workdir/$label.dtb"
	printf '%s\n' "$workdir/$label.dtb"
}

new_package() {
	local label=$1
	local parent="$workdir/package-$label"
	mkdir "$parent"
	cp -a "$package" "$parent/"
	printf '%s\n' "$parent/$(basename -- "$package")"
}

refresh_package_manifest() {
	local candidate_package=$1
	local temporary="$workdir/refreshed-SHA256SUMS"
	(
		cd "$candidate_package"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
	) >"$temporary"
	mv "$temporary" "$candidate_package/SHA256SUMS"
}

calculate_packaged_patchset() {
	local candidate_package=$1
	local series="$candidate_package/provenance/series"
	{
		printf '%s  patches/series\n' "$(sha256sum "$series" | awk '{print $1}')"
		while IFS= read -r relative || [[ -n "$relative" ]]; do
			[[ -z "$relative" || "$relative" == \#* ]] && continue
			printf '%s  %s\n' \
				"$(sha256sum "$candidate_package/provenance/patches/$relative" | awk '{print $1}')" \
				"$relative"
		done <"$series"
	} | sha256sum | awk '{print $1}'
}

# Positive controls prove the unmodified selected inputs pass every layer.
(cd "$v_artifact" && sha256sum --check SHA256SUMS >/dev/null)
"$artifact_validator" "$package" >/dev/null
validate_package "$package" >/dev/null
"$patch_validator" --patch "$polling_patch" >/dev/null
validate_dtb "$p_dtb" "$oracle" "$candidate_dtb" >/dev/null
validate_initramfs "$candidate_initramfs" "$helper" >/dev/null
validate_boot "$candidate_boot" "$image_gz" "$candidate_dtb" \
	"$candidate_initramfs" >/dev/null

# Immutable P and package-oracle identity gates.
copy_and_append "$p_dtb" "$workdir/wrong-p.dtb"
expect_reject wrong-p-byte validate_dtb "$workdir/wrong-p.dtb" "$oracle" "$candidate_dtb"
copy_and_append "$oracle" "$workdir/wrong-oracle.dtb"
expect_reject wrong-package-oracle-byte validate_dtb "$p_dtb" \
	"$workdir/wrong-oracle.dtb" "$candidate_dtb"

# Exact-P semantic preservation and allowlist checks, all against a valid FDT.
bad="$(mutated_dtb simplefb-deleted)"
fdtput -r "$bad" /chosen/framebuffer@7dfb0000
expect_reject simplefb-node-deleted validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb simplefb-clocks)"
fdtput -t x "$bad" /chosen/framebuffer@7dfb0000 clocks 3 45 6 7
expect_reject simplefb-clock-cells validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb watchdog-irq)"
fdtput -t x "$bad" /watchdog@10007000 interrupts 0 190 4
expect_reject watchdog-interrupt-reintroduced validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb ramoops-record-size)"
fdtput -t x "$bad" /reserved-memory/ramoops@44410000 record-size 0x2000
expect_reject ramoops-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb cpu-clock-frequency)"
fdtput -t x "$bad" /cpus/cpu@0 clock-frequency 0x1
expect_reject cpu-clock-frequency validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb atf-compatible)"
fdtput -t s "$bad" /reserved-memory/memory@44600000 compatible mediatek,mutated-atf
expect_reject atf-reserved-compatible validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb scp-status)"
fdtput -t s "$bad" /scp@10020000 status okay
expect_reject scp-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb tphy-status)"
fdtput -t s "$bad" /t-phy@11290000 status disabled
expect_reject tphy-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb mtu3-status)"
fdtput -t s "$bad" /usb@11271000 status disabled
expect_reject mtu3-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb unrelated-root)"
fdtput -t s "$bad" / candidate-v-unrelated mutation
expect_reject unrelated-root-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb target-extra-property)"
fdtput -t i "$bad" /keyboard-matrix debounce-delay-ms 5
expect_reject target-extra-property validate_dtb "$p_dtb" "$oracle" "$bad"

bad="$(mutated_dtb duplicate-phandle)"
fdtput -t x "$bad" /pinctrl@10005000/i2c5-pins phandle 0x29
expect_reject duplicate-phandle validate_dtb "$p_dtb" "$oracle" "$bad"

# Runtime payload and final Android container pins.
copy_and_append "$candidate_initramfs" "$workdir/initramfs-byte.img"
expect_reject initramfs-byte validate_initramfs "$workdir/initramfs-byte.img" "$helper"
copy_and_append "$helper" "$workdir/helper-byte"
chmod 0755 "$workdir/helper-byte"
expect_reject helper-byte validate_initramfs "$candidate_initramfs" "$workdir/helper-byte"
copy_and_append "$candidate_boot" "$workdir/boot-byte.img"
expect_reject boot-byte validate_boot "$workdir/boot-byte.img" "$image_gz" \
	"$candidate_dtb" "$candidate_initramfs"

# A local corrected-patch substitution is rejected independently of package bytes.
fixture_repo="$workdir/repository-fixture"
mkdir "$fixture_repo"
cp -a "$repo_root/kernel" "$repo_root/patches" "$repo_root/configs" "$fixture_repo/"
printf '\n# mutation\n' >>"$fixture_repo/patches/v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch"
expect_reject corrected-local-patch-mutation validate_package "$package" \
	"$fixture_repo/kernel/manifest.json"

# Complete-package pinning rejects coherent manifest refreshes and provenance forgery.
bad_package="$(new_package extra-file)"
printf 'mutation\n' >"$bad_package/provenance/unexpected-file"
refresh_package_manifest "$bad_package"
expect_reject complete-package-inventory validate_package "$bad_package"

bad_package="$(new_package config)"
printf '\nCONFIG_I2C_CHARDEV=y\n' >>"$bad_package/kernel.config"
config_hash="$(sha256sum "$bad_package/kernel.config" | awk '{print $1}')"
jq --arg value "$config_hash" '.config_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_package_manifest "$bad_package"
expect_reject package-config-substitution validate_package "$bad_package"

bad_package="$(new_package image)"
printf '\001' >>"$bad_package/Image.gz"
refresh_package_manifest "$bad_package"
expect_reject package-image-substitution validate_package "$bad_package"

bad_package="$(new_package patchset)"
jq '.patchset_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_package_manifest "$bad_package"
expect_reject package-patchset-substitution validate_package "$bad_package"

bad_package="$(new_package package-provenance)"
printf '\n' >>"$bad_package/provenance/kernel-manifest.json"
refresh_package_manifest "$bad_package"
expect_reject package-provenance-substitution validate_package "$bad_package"

bad_package="$(new_package forged-0084)"
printf '\n# forged packaged polling implementation\n' \
	>>"$bad_package/provenance/patches/v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch"
forged_patchset="$(calculate_packaged_patchset "$bad_package")"
jq --arg value "$forged_patchset" '.patchset_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_package_manifest "$bad_package"
expect_reject packaged-0084-forged-provenance validate_package "$bad_package"

printf 'validation=candidate-v-validator-mutations\n'
printf 'positive_controls=kernel-package,selected-package,corrected-patch,dtb,initramfs,android-v0,artifact-manifest\n'
printf 'rejection_count=%s\n' "$(wc -l <"$rejections")"
printf 'rejected_mutations=%s\n' \
	"$(sort "$rejections" | awk 'BEGIN { separator="" } { printf "%s%s", separator, $0; separator="," }')"
printf 'hardware_write=none\nflash=none\n'
