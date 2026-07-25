#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --v-baseline DIR --w-artifact DIR\n' "$0" >&2
}

package=
v_baseline=
w_artifact=
while (($#)); do
	case "$1" in
	--package|--v-baseline|--w-artifact)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--v-baseline) v_baseline=$2 ;;
		--w-artifact) w_artifact=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
for directory in "$package" "$v_baseline" "$w_artifact"; do
	[[ -d "$directory" ]] || die "required directory missing: $directory"
done
for command in awk basename chmod cmp cp fdtput find grep gzip jq mkdir mktemp \
	ln mv python3 rm sed sha256sum sort uname uniq wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

package="$(cd -- "$package" && pwd -P)"
v_baseline="$(cd -- "$v_baseline" && pwd -P)"
w_artifact="$(cd -- "$w_artifact" && pwd -P)"

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly PACKAGE_SUMS_SHA256=6337c00318acecea64ed77fe67757744f9c2ad9d730c1c22b14b7ad43b2a91d0
readonly W_BOOT_SHA256=34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4
for name in PACKAGE_SUMS_SHA256 W_BOOT_SHA256; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done

readonly PACKAGE_BASENAME=linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-4cd417ad-28a94091
readonly V_BASELINE_BASENAME=candidate-V-keyboard-watchdog-final-9ef0ee8d
readonly V_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly W_ARTIFACT_BASENAME=candidate-W-keyboard-wrrd-final-${W_BOOT_SHA256:0:8}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
candidate_builder="$script_dir/build-keyboard-wrrd-candidate.sh"
manifest="$repo_root/kernel/manifest.json"
artifact_validator="$repo_root/scripts/validate-kernel-artifact"
package_validator="$script_dir/validate-package-foundation.py"
controller_validator="$script_dir/validate-controller-patch.sh"
baseline_validator="$script_dir/validate-v-baseline.py"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
controller_patch="$repo_root/patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"

v_dtb="$v_baseline/mt6797-gemini-pda-keyboard-watchdog.dtb"
v_initramfs="$v_baseline/gemini-keyboard-watchdog-initramfs.img"
helper="$v_baseline/input-event-capture"
w_dtb="$w_artifact/mt6797-gemini-pda-keyboard-wrrd.dtb"
w_initramfs="$w_artifact/gemini-keyboard-wrrd-initramfs.img"
w_boot="$w_artifact/gemini-keyboard-wrrd.boot.img"
image="$package/Image"
image_gz="$package/Image.gz"
for input in "$candidate_builder" "$manifest" "$artifact_validator" "$package_validator" \
	"$controller_validator" "$baseline_validator" "$initramfs_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$controller_patch" \
	"$v_dtb" "$v_initramfs" "$helper" "$w_dtb" "$w_initramfs" \
	"$w_boot" "$image" "$image_gz" "$package/SHA256SUMS" \
	"$w_artifact/SHA256SUMS"; do
	[[ -s "$input" ]] || die "required validator input missing: $input"
done
[[ -x "$helper" ]] || die "selected Candidate V helper is not executable"

workdir="$(mktemp -d /tmp/candidate-w-mutations.XXXXXX)"
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

refresh_manifest() {
	local directory=$1
	local temporary="$workdir/refreshed-SHA256SUMS"
	(
		cd "$directory"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
	) >"$temporary"
	mv "$temporary" "$directory/SHA256SUMS"
}

copy_selected_tree() {
	local source=$1
	local destination=$2
	[[ -d "$source" && ! -L "$source" ]] || {
		printf 'error: refusing to copy a symlinked selected source: %s\n' \
			"$source" >&2
		return 2
	}
	[[ ! -e "$destination" && ! -L "$destination" ]] || {
		printf 'error: refusing to overwrite mutation destination: %s\n' \
			"$destination" >&2
		return 2
	}
	mkdir "$destination"
	cp -a "$source/." "$destination/"
}

new_package() {
	local label=$1
	local parent="$workdir/package-$label"
	local destination="$parent/$PACKAGE_BASENAME"
	mkdir "$parent"
	copy_selected_tree "$package" "$destination" || return
	printf '%s\n' "$destination"
}

new_v_baseline() {
	local label=$1
	local parent="$workdir/v-$label"
	local destination="$parent/$V_BASELINE_BASENAME"
	mkdir "$parent"
	copy_selected_tree "$v_baseline" "$destination" || return
	printf '%s\n' "$destination"
}

new_w_artifact() {
	local label=$1
	local parent="$workdir/w-$label"
	local destination="$parent/$W_ARTIFACT_BASENAME"
	mkdir "$parent"
	copy_selected_tree "$w_artifact" "$destination" || return
	printf '%s\n' "$destination"
}

calculate_packaged_patchset() {
	local candidate_package=$1
	local packaged_series="$candidate_package/provenance/series"
	{
		printf '%s  patches/series\n' "$(sha256sum "$packaged_series" | awk '{print $1}')"
		while IFS= read -r relative || [[ -n "$relative" ]]; do
			[[ -z "$relative" || "$relative" == \#* ]] && continue
			printf '%s  %s\n' \
				"$(sha256sum "$candidate_package/provenance/patches/$relative" | awk '{print $1}')" \
				"$relative"
		done <"$packaged_series"
	} | sha256sum | awk '{print $1}'
}

validate_selected_package() {
	local candidate_package=$1
	[[ "$(basename -- "$candidate_package")" == "$PACKAGE_BASENAME" ]] || \
		{ printf 'error: selected package basename changed\n' >&2; return 2; }
	[[ "$(sha256sum "$candidate_package/SHA256SUMS" | awk '{print $1}')" == \
		"$PACKAGE_SUMS_SHA256" ]] || \
		{ printf 'error: selected package manifest changed\n' >&2; return 2; }
	"$artifact_validator" "$candidate_package" >/dev/null
	"$package_validator" --package "$candidate_package" --manifest "$manifest" \
		>/dev/null
}

validate_selected_w_artifact() {
	local candidate_artifact=$1
	local actual_inventory
	local duplicate_manifest_path
	local expected_inventory
	local expected_payload_inventory
	local invalid_manifest_line
	local manifest_inventory
	local unexpected_entry
	[[ "$(basename -- "$candidate_artifact")" == "$W_ARTIFACT_BASENAME" ]] || \
		{ printf 'error: selected Candidate W basename changed\n' >&2; return 2; }
	expected_payload_inventory="$(printf '%s\n' \
		analysis.txt \
		boot-validation.txt \
		controller-patch.txt \
		gemini-keyboard-wrrd-initramfs.img \
		gemini-keyboard-wrrd.boot.img \
		initramfs-build.txt \
		initramfs-validation.txt \
		input-event-capture \
		input-tree.sha256 \
		mt6797-gemini-pda-keyboard-wrrd.dtb \
		package-foundation.txt \
		package-validation.txt \
		provenance.txt \
		serializer.txt \
		source-build.json \
		v-baseline-validation.txt)"
	expected_inventory="$(printf 'SHA256SUMS\n%s\n' "$expected_payload_inventory")"
	unexpected_entry="$(find "$candidate_artifact" -mindepth 1 ! -type f \
		-print -quit)"
	[[ -z "$unexpected_entry" ]] || {
		printf 'error: Candidate W artifact has a non-regular entry: %s\n' \
			"$unexpected_entry" >&2
		return 2
	}
	actual_inventory="$(find "$candidate_artifact" -mindepth 1 -maxdepth 1 \
		-type f -printf '%f\n' | sort)"
	[[ "$actual_inventory" == "$expected_inventory" ]] || \
		{ printf 'error: Candidate W artifact inventory changed\n' >&2; return 2; }
	invalid_manifest_line="$(awk '
		length($1) != 64 || $1 ~ /[^0-9a-f]/ || NF != 2 ||
		$2 !~ /^\.\/[A-Za-z0-9][A-Za-z0-9._-]*$/ {
			print NR ":" $0
			exit
		}
	' "$candidate_artifact/SHA256SUMS")"
	[[ -z "$invalid_manifest_line" ]] || {
		printf 'error: malformed Candidate W manifest line: %s\n' \
			"$invalid_manifest_line" >&2
		return 2
	}
	manifest_inventory="$(awk '{ sub(/^\.\//, "", $2); print $2 }' \
		"$candidate_artifact/SHA256SUMS" | sort)"
	duplicate_manifest_path="$(printf '%s\n' "$manifest_inventory" | uniq -d | \
		awk 'NR == 1 { print; exit }')"
	[[ -z "$duplicate_manifest_path" ]] || {
		printf 'error: duplicate Candidate W manifest path: %s\n' \
			"$duplicate_manifest_path" >&2
		return 2
	}
	[[ "$manifest_inventory" == "$expected_payload_inventory" ]] || {
		printf 'error: Candidate W manifest inventory changed\n' >&2
		return 2
	}
	(cd "$candidate_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
		{ printf 'error: Candidate W manifest verification failed\n' >&2; return 2; }
}

validate_selected_w_replica() {
	local candidate_artifact=$1
	local relative
	validate_selected_w_artifact "$candidate_artifact"
	cmp -s "$candidate_artifact/SHA256SUMS" "$rebuilt_w/SHA256SUMS" || {
		printf 'error: Candidate W manifest differs from a fresh deterministic rebuild\n' >&2
		return 2
	}
	while IFS= read -r relative || [[ -n "$relative" ]]; do
		relative=${relative#./}
		cmp -s "$candidate_artifact/$relative" "$rebuilt_w/$relative" || {
			printf 'error: Candidate W file differs from a fresh deterministic rebuild: %s\n' \
				"$relative" >&2
			return 2
		}
	done < <(awk '{ print $2 }' "$rebuilt_w/SHA256SUMS")
}

validate_boot() {
	"$boot_validator" --candidate "$1" --image-gz "$2" --dtb "$3" \
		--initramfs "$4"
}

# Positive controls cover every selected input and the complete W output.
validate_selected_package "$package"
"$controller_validator" --patch "$controller_patch" >/dev/null
"$baseline_validator" --baseline "$v_baseline" >/dev/null
rebuilt_parent="$workdir/deterministic-rebuild"
mkdir "$rebuilt_parent"
rebuilt_w="$rebuilt_parent/$W_ARTIFACT_BASENAME"
"$candidate_builder" --package "$package" --baseline "$v_baseline" \
	--output "$rebuilt_w" >"$workdir/deterministic-rebuild.txt"
validate_selected_w_artifact "$rebuilt_w"
validate_selected_w_replica "$w_artifact"
cmp -s "$v_dtb" "$w_dtb" || die "Candidate W DTB is not byte-exact Candidate V"
[[ "$(sha256sum "$w_dtb" | awk '{print $1}')" == "$V_DTB_SHA256" ]] || \
	die "Candidate W DTB pin changed"
"$initramfs_validator" --baseline "$v_initramfs" --candidate "$w_initramfs" \
	--helper "$helper" >/dev/null
validate_boot "$w_boot" "$image_gz" "$w_dtb" "$w_initramfs" >/dev/null
python3 "$analyzer" --validate-lk --expected-image-gz "$image_gz" \
	--expected-ramdisk "$w_initramfs" --expected-dtb "$w_dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$w_boot" >/dev/null

# Candidate V remains an immutable, fully inventoried baseline.
builder_guard_dir="$workdir/builder-output-guards"
mkdir "$builder_guard_dir"
ln -s missing-target "$builder_guard_dir/$W_ARTIFACT_BASENAME"
expect_reject builder-dangling-output-symlink "$candidate_builder" \
	--package "$package" --baseline "$v_baseline" \
	--output "$builder_guard_dir/$W_ARTIFACT_BASENAME"
mkdir "$builder_guard_dir/existing"
expect_reject builder-existing-output "$candidate_builder" \
	--package "$package" --baseline "$v_baseline" \
	--output "$builder_guard_dir/existing"
expect_reject builder-output-inside-package "$candidate_builder" \
	--package "$package" --baseline "$v_baseline" \
	--output "$package/$W_ARTIFACT_BASENAME"
expect_reject builder-missing-parent-inside-package "$candidate_builder" \
	--package "$package" --baseline "$v_baseline" \
	--output "$package/forbidden-output-parent/$W_ARTIFACT_BASENAME"
[[ ! -e "$package/forbidden-output-parent" && \
	! -L "$package/forbidden-output-parent" ]] || \
	die "builder created a forbidden output parent inside the selected package"

selected_source_link="$workdir/selected-package-link"
ln -s "$package" "$selected_source_link"
expect_reject selected-source-symlink-copy copy_selected_tree \
	"$selected_source_link" "$workdir/forbidden-copy"

wrong_name="$workdir/candidate-v-wrong-name"
cp -a "$v_baseline" "$wrong_name"
expect_reject v-baseline-name "$baseline_validator" --baseline "$wrong_name"

bad_v="$(new_v_baseline boot-byte)"
printf '\001' >>"$bad_v/gemini-keyboard-watchdog.boot.img"
refresh_manifest "$bad_v"
expect_reject v-baseline-coherent-boot "$baseline_validator" --baseline "$bad_v"

bad_v="$(new_v_baseline valid-dtb)"
fdtput -t x "$bad_v/mt6797-gemini-pda-keyboard-watchdog.dtb" \
	/keyboard-matrix poll-interval 21
refresh_manifest "$bad_v"
expect_reject v-baseline-coherent-dtb "$baseline_validator" --baseline "$bad_v"

# The controller line is independently guarded from package provenance.
cp "$controller_patch" "$workdir/controller-extra.patch"
printf '\ndiff --git a/extra.c b/extra.c\n' >>"$workdir/controller-extra.patch"
expect_reject controller-extra-file "$controller_validator" \
	--patch "$workdir/controller-extra.patch"

# A changed local source input cannot be hidden behind the selected package.
fixture_repo="$workdir/repository-fixture"
mkdir "$fixture_repo"
cp -a "$repo_root/kernel" "$repo_root/patches" "$repo_root/configs" "$fixture_repo/"
printf '\n# local controller mutation\n' \
	>>"$fixture_repo/patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
expect_reject local-controller-substitution "$package_validator" \
	--package "$package" --manifest "$fixture_repo/kernel/manifest.json"

# Coherently refreshed package manifests and provenance remain unselected.
bad_package="$(new_package extra-file)"
printf 'mutation\n' >"$bad_package/unexpected-file"
refresh_manifest "$bad_package"
expect_reject package-extra-file validate_selected_package "$bad_package"

bad_package="$(new_package config)"
sed -i 's/^# CONFIG_I2C_CHARDEV is not set$/CONFIG_I2C_CHARDEV=y/' \
	"$bad_package/kernel.config"
config_hash="$(sha256sum "$bad_package/kernel.config" | awk '{print $1}')"
jq --arg value "$config_hash" '.config_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_manifest "$bad_package"
expect_reject package-coherent-config "$package_validator" \
	--package "$bad_package" --manifest "$manifest"

bad_package="$(new_package image)"
printf '\000' >>"$bad_package/Image"
gzip -n -9 -c "$bad_package/Image" >"$workdir/Image.gz"
mv "$workdir/Image.gz" "$bad_package/Image.gz"
refresh_manifest "$bad_package"
expect_reject package-coherent-image validate_selected_package "$bad_package"

bad_package="$(new_package patchset)"
printf '\n# forged packaged controller patch\n' \
	>>"$bad_package/provenance/patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
forged_patchset="$(calculate_packaged_patchset "$bad_package")"
jq --arg value "$forged_patchset" '.patchset_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_manifest "$bad_package"
expect_reject package-coherent-patchset "$package_validator" \
	--package "$bad_package" --manifest "$manifest"

# Runtime components and coherent Android containers are pinned separately.
cp "$w_initramfs" "$workdir/initramfs-byte.img"
printf '\001' >>"$workdir/initramfs-byte.img"
expect_reject initramfs-byte "$initramfs_validator" --baseline "$v_initramfs" \
	--candidate "$workdir/initramfs-byte.img" --helper "$helper"

cp "$helper" "$workdir/helper-byte"
printf '\001' >>"$workdir/helper-byte"
chmod 0755 "$workdir/helper-byte"
expect_reject helper-byte "$initramfs_validator" --baseline "$v_initramfs" \
	--candidate "$w_initramfs" --helper "$workdir/helper-byte"

cp "$w_boot" "$workdir/boot-byte.img"
printf '\001' >>"$workdir/boot-byte.img"
expect_reject boot-byte validate_boot "$workdir/boot-byte.img" "$image_gz" \
	"$w_dtb" "$w_initramfs"

cp "$w_dtb" "$workdir/valid-mutated.dtb"
fdtput -t x "$workdir/valid-mutated.dtb" /keyboard-matrix poll-interval 21
python3 "$serializer" --kernel "$image_gz" --ramdisk "$w_initramfs" \
	--dtb "$workdir/valid-mutated.dtb" --output "$workdir/coherent-dtb.boot.img" \
	--name gemini-obs-L --cmdline bootopt=64S3,32N2,64N2 \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-dtb-substitution validate_boot \
	"$workdir/coherent-dtb.boot.img" "$image_gz" "$workdir/valid-mutated.dtb" \
	"$w_initramfs"

gzip -n -1 -c "$image" >"$workdir/substituted-Image.gz"
! cmp -s "$workdir/substituted-Image.gz" "$image_gz" || \
	die "coherent Image.gz substitution did not change the selected stream"
python3 "$serializer" --kernel "$workdir/substituted-Image.gz" \
	--ramdisk "$w_initramfs" --dtb "$w_dtb" \
	--output "$workdir/coherent-image.boot.img" --name gemini-obs-L \
	--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-image-substitution validate_boot \
	"$workdir/coherent-image.boot.img" "$workdir/substituted-Image.gz" \
	"$w_dtb" "$w_initramfs"

python3 "$serializer" --kernel "$image_gz" \
	--ramdisk "$workdir/initramfs-byte.img" --dtb "$w_dtb" \
	--output "$workdir/coherent-initramfs.boot.img" --name gemini-obs-L \
	--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-initramfs-substitution validate_boot \
	"$workdir/coherent-initramfs.boot.img" "$image_gz" "$w_dtb" \
	"$workdir/initramfs-byte.img"

bad_w="$(new_w_artifact extra-file)"
printf 'mutation\n' >"$bad_w/unexpected-file"
refresh_manifest "$bad_w"
expect_reject w-artifact-coherent-inventory validate_selected_w_artifact "$bad_w"

bad_w="$(new_w_artifact nested-file)"
mkdir "$bad_w/unexpected-directory"
printf 'mutation\n' >"$bad_w/unexpected-directory/file"
refresh_manifest "$bad_w"
expect_reject w-artifact-coherent-nested-entry \
	validate_selected_w_artifact "$bad_w"

bad_w="$(new_w_artifact symlink-entry)"
ln -s provenance.txt "$bad_w/unexpected-link"
expect_reject w-artifact-symlink-entry validate_selected_w_artifact "$bad_w"

bad_w="$(new_w_artifact provenance-file)"
printf 'forged_provenance=yes\n' >>"$bad_w/provenance.txt"
refresh_manifest "$bad_w"
expect_reject w-artifact-coherent-provenance \
	validate_selected_w_replica "$bad_w"

printf 'validation=candidate-w-validator-mutations\n'
printf '%s\n' \
	'positive_controls=selected-package,controller,v-baseline,deterministic-w-rebuild,w-artifact,exact-v-dtb,initramfs,android-v0,lk'
printf 'rejection_count=%s\n' "$(wc -l <"$rejections")"
rejected_mutations="$(sort "$rejections" | awk '
	BEGIN { separator="" }
	{ printf "%s%s", separator, $0; separator="," }
')"
printf 'rejected_mutations=%s\n' \
	"$rejected_mutations"
printf 'hardware_write=none\nflash=none\n'
