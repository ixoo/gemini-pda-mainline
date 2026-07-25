#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --w-baseline DIR --x-artifact DIR\n' "$0" >&2
}

package=
w_baseline=
x_artifact=
while (($#)); do
	case "$1" in
	--package|--w-baseline|--x-artifact)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--w-baseline) w_baseline=$2 ;;
		--x-artifact) x_artifact=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
for directory in "$package" "$w_baseline" "$x_artifact"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "required selected directory is missing or a symlink: $directory"
done
for command in awk basename chmod cmp cp cpio fdtput find grep gzip install jq \
	ln mkdir mkfifo mktemp mv python3 rm sed sha256sum sort stat touch uname uniq \
	wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

package="$(cd -- "$package" && pwd -P)"
w_baseline="$(cd -- "$w_baseline" && pwd -P)"
x_artifact="$(cd -- "$x_artifact" && pwd -P)"

readonly PLACEHOLDER_PREFIX=REPLACE_AFTER_CALIBRATION_
readonly PACKAGE_BASENAME=linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-manual-reboot-4cd417ad-c811a159
readonly PACKAGE_SUMS_SHA256=541542094a9f516556ffcab884abd3db1d58537aff6fd7e2f95abba42e2992c7
readonly X_INITRAMFS_SHA256=b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769
readonly X_BOOT_SHA256=bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296
for name in PACKAGE_BASENAME PACKAGE_SUMS_SHA256 X_INITRAMFS_SHA256 X_BOOT_SHA256; do
	value=${!name}
	[[ "$value" != "$PLACEHOLDER_PREFIX"* ]] || \
		die "calibration placeholder remains: $name"
done
for name in PACKAGE_SUMS_SHA256 X_INITRAMFS_SHA256 X_BOOT_SHA256; do
	value=${!name}
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || die "invalid calibrated SHA-256: $name"
done
[[ "$PACKAGE_BASENAME" =~ ^linux-7\.1\.3-gemini-[A-Za-z0-9._-]+$ ]] || \
	die "invalid calibrated package basename"

readonly W_BASELINE_BASENAME=candidate-W-keyboard-wrrd-final-34c41fad
readonly W_DTB_SHA256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
readonly W_INITRAMFS_SHA256=3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6
readonly W_HELPER_SHA256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602
readonly X_ARTIFACT_BASENAME=candidate-X-keyboard-manual-reboot-final-${X_BOOT_SHA256:0:8}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
candidate_builder="$script_dir/build-keyboard-manual-reboot-candidate.sh"
manifest="$repo_root/kernel/manifest.json"
artifact_validator="$repo_root/scripts/validate-kernel-artifact"
package_validator="$script_dir/validate-package-foundation.py"
baseline_validator="$script_dir/validate-w-baseline.py"
initramfs_validator="$script_dir/validate-initramfs.sh"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"

w_dtb="$w_baseline/mt6797-gemini-pda-keyboard-wrrd.dtb"
w_initramfs="$w_baseline/gemini-keyboard-wrrd-initramfs.img"
helper="$w_baseline/input-event-capture"
x_dtb="$x_artifact/mt6797-gemini-pda-keyboard-manual-reboot.dtb"
x_initramfs="$x_artifact/gemini-keyboard-manual-reboot-initramfs.img"
x_boot="$x_artifact/gemini-keyboard-manual-reboot.boot.img"
image="$package/Image"
image_gz="$package/Image.gz"
for input in "$candidate_builder" "$manifest" "$artifact_validator" \
	"$package_validator" "$baseline_validator" "$initramfs_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$w_dtb" "$w_initramfs" \
	"$helper" "$x_dtb" "$x_initramfs" "$x_boot" "$image" "$image_gz" \
	"$package/SHA256SUMS" "$x_artifact/SHA256SUMS"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required validator input missing: $input"
done
[[ -x "$helper" ]] || die "selected Candidate W helper is not executable"
[[ "$(sha256sum "$w_initramfs" | awk '{print $1}')" == "$W_INITRAMFS_SHA256" ]] || \
	die "selected Candidate W initramfs pin changed"
[[ "$(sha256sum "$helper" | awk '{print $1}')" == "$W_HELPER_SHA256" ]] || \
	die "selected Candidate W helper pin changed"

workdir="$(mktemp -d /tmp/candidate-x-mutations.XXXXXX)"
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
		printf 'error: refusing to copy symlinked selected source: %s\n' "$source" >&2
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

new_w_baseline() {
	local label=$1
	local parent="$workdir/w-$label"
	local destination="$parent/$W_BASELINE_BASENAME"
	mkdir "$parent"
	copy_selected_tree "$w_baseline" "$destination" || return
	printf '%s\n' "$destination"
}

new_x_artifact() {
	local label=$1
	local parent="$workdir/x-$label"
	local destination="$parent/$X_ARTIFACT_BASENAME"
	mkdir "$parent"
	copy_selected_tree "$x_artifact" "$destination" || return
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
	[[ "$(basename -- "$candidate_package")" == "$PACKAGE_BASENAME" ]] || {
		printf 'error: selected package basename changed\n' >&2
		return 2
	}
	[[ "$(sha256sum "$candidate_package/SHA256SUMS" | awk '{print $1}')" == \
		"$PACKAGE_SUMS_SHA256" ]] || {
		printf 'error: selected package manifest changed\n' >&2
		return 2
	}
	"$artifact_validator" "$candidate_package" >/dev/null
	"$package_validator" --package "$candidate_package" --manifest "$manifest" >/dev/null
}

expected_x_payload_inventory() {
	printf '%s\n' \
		analysis.txt \
		boot-validation.txt \
		gemini-keyboard-manual-reboot-initramfs.img \
		gemini-keyboard-manual-reboot.boot.img \
		initramfs-build.txt \
		initramfs-validation.txt \
		input-event-capture \
		input-tree.sha256 \
		mt6797-gemini-pda-keyboard-manual-reboot.dtb \
		package-foundation.txt \
		package-validation.txt \
		provenance.txt \
		serializer.txt \
		source-build.json \
		w-baseline-validation.txt
}

validate_selected_x_artifact() {
	local candidate_artifact=$1
	local actual_inventory child duplicate_manifest_path expected_inventory expected_mode
	local expected_payload invalid_manifest_line manifest_inventory mode unexpected_entry
	[[ -d "$candidate_artifact" && ! -L "$candidate_artifact" && \
		"$(basename -- "$candidate_artifact")" == "$X_ARTIFACT_BASENAME" ]] || {
		printf 'error: selected Candidate X directory identity changed\n' >&2
		return 2
	}
	expected_payload="$(expected_x_payload_inventory)"
	expected_inventory="$(printf 'SHA256SUMS\n%s\n' "$expected_payload")"
	unexpected_entry="$(find "$candidate_artifact" -mindepth 1 ! -type f -print -quit)"
	[[ -z "$unexpected_entry" ]] || {
		printf 'error: Candidate X artifact has a non-regular entry: %s\n' \
			"$unexpected_entry" >&2
		return 2
	}
	actual_inventory="$(find "$candidate_artifact" -mindepth 1 -maxdepth 1 \
		-type f -printf '%f\n' | sort)"
	[[ "$actual_inventory" == "$expected_inventory" ]] || {
		printf 'error: Candidate X artifact inventory changed\n' >&2
		return 2
	}
	while IFS= read -r child; do
		mode="$(stat -c '%a' "$candidate_artifact/$child")"
		expected_mode=600
		[[ "$child" != input-event-capture ]] || expected_mode=755
		[[ "$mode" == "$expected_mode" ]] || {
			printf 'error: Candidate X artifact mode changed: %s\n' "$child" >&2
			return 2
		}
	done <<<"$actual_inventory"
	invalid_manifest_line="$(awk '
		length($1) != 64 || $1 ~ /[^0-9a-f]/ || NF != 2 ||
		$2 !~ /^\.\/[A-Za-z0-9][A-Za-z0-9._-]*$/ {
			print NR ":" $0
			exit
		}
	' "$candidate_artifact/SHA256SUMS")"
	[[ -z "$invalid_manifest_line" ]] || {
		printf 'error: malformed Candidate X manifest line: %s\n' \
			"$invalid_manifest_line" >&2
		return 2
	}
	manifest_inventory="$(awk '{ sub(/^\.\//, "", $2); print $2 }' \
		"$candidate_artifact/SHA256SUMS" | sort)"
	duplicate_manifest_path="$(printf '%s\n' "$manifest_inventory" | uniq -d | \
		awk 'NR == 1 { print; exit }')"
	[[ -z "$duplicate_manifest_path" && "$manifest_inventory" == "$expected_payload" ]] || {
		printf 'error: Candidate X manifest inventory changed or contains duplicates\n' >&2
		return 2
	}
	(cd "$candidate_artifact" && sha256sum --check --strict SHA256SUMS >/dev/null) || {
		printf 'error: Candidate X artifact manifest verification failed\n' >&2
		return 2
	}
	[[ "$(sha256sum "$candidate_artifact/gemini-keyboard-manual-reboot.boot.img" | awk '{print $1}')" == \
		"$X_BOOT_SHA256" ]] || {
		printf 'error: Candidate X selected boot hash changed\n' >&2
		return 2
	}
	[[ "$(sha256sum "$candidate_artifact/gemini-keyboard-manual-reboot-initramfs.img" | awk '{print $1}')" == \
		"$X_INITRAMFS_SHA256" ]] || {
		printf 'error: Candidate X selected initramfs hash changed\n' >&2
		return 2
	}
	[[ "$(sha256sum "$candidate_artifact/mt6797-gemini-pda-keyboard-manual-reboot.dtb" | awk '{print $1}')" == \
		"$W_DTB_SHA256" ]] || {
		printf 'error: Candidate X selected DTB hash changed\n' >&2
		return 2
	}
}

validate_selected_x_replica() {
	local candidate_artifact=$1
	local relative
	validate_selected_x_artifact "$candidate_artifact"
	cmp -s "$candidate_artifact/SHA256SUMS" "$rebuilt_x/SHA256SUMS" || {
		printf 'error: Candidate X manifest differs from deterministic rebuild\n' >&2
		return 2
	}
	while IFS= read -r relative || [[ -n "$relative" ]]; do
		relative=${relative#./}
		cmp -s "$candidate_artifact/$relative" "$rebuilt_x/$relative" || {
			printf 'error: Candidate X file differs from deterministic rebuild: %s\n' \
				"$relative" >&2
			return 2
		}
	done < <(awk '{print $2}' "$rebuilt_x/SHA256SUMS")
}

validate_boot() {
	"$boot_validator" --candidate "$1" --image-gz "$2" --dtb "$3" \
		--initramfs "$4"
}

new_semantic_fixture() {
	local label=$1
	local fixture="$workdir/semantic-$label"
	mkdir -p "$fixture/experiment/scripts" "$fixture/experiment/initramfs" \
		"$fixture/root"
	cp "$initramfs_validator" "$fixture/experiment/scripts/validate-initramfs.sh"
	cp "$experiment_dir/initramfs/"* "$fixture/experiment/initramfs/"
	gzip -dc "$x_initramfs" | (cd "$fixture/root" && cpio -idmu --quiet)
	printf '%s\n' "$fixture"
}

rebuild_semantic_fixture() {
	local fixture=$1
	find "$fixture/root" -exec touch -h -d @0 {} +
	(
		cd "$fixture/root"
		find . -print0 | sort -z | cpio --null --create --format=newc \
			--owner=0:0 --reproducible --quiet
	) | gzip -n -9 >"$fixture/candidate.img"
}

validate_semantic_fixture() {
	local fixture=$1
	"$fixture/experiment/scripts/validate-initramfs.sh" --baseline "$w_initramfs" \
		--candidate "$fixture/candidate.img" --helper "$helper"
}

# Positive controls cover each selected input and an independent complete build.
validate_selected_package "$package"
"$baseline_validator" --baseline "$w_baseline" >/dev/null
rebuilt_parent="$workdir/deterministic-rebuild"
mkdir "$rebuilt_parent"
rebuilt_x="$rebuilt_parent/$X_ARTIFACT_BASENAME"
"$candidate_builder" --package "$package" --baseline "$w_baseline" \
	--output "$rebuilt_x" >"$workdir/deterministic-rebuild.txt"
validate_selected_x_artifact "$rebuilt_x"
validate_selected_x_replica "$x_artifact"
cmp -s "$w_dtb" "$x_dtb" || die "Candidate X DTB is not byte-exact Candidate W"
"$initramfs_validator" --baseline "$w_initramfs" --candidate "$x_initramfs" \
	--helper "$helper" >/dev/null
validate_boot "$x_boot" "$image_gz" "$x_dtb" "$x_initramfs" >/dev/null
python3 "$analyzer" --validate-lk --expected-image-gz "$image_gz" \
	--expected-ramdisk "$x_initramfs" --expected-dtb "$x_dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 \
	"$x_boot" >/dev/null

# Caller-controlled TMPDIR must never place validator scratch data in a selected tree.
TMPDIR="$w_baseline" "$initramfs_validator" --baseline "$w_initramfs" \
	--candidate "$x_initramfs" --helper "$helper" >/dev/null
"$baseline_validator" --baseline "$w_baseline" >/dev/null

# Builder destination and selected-source guards.
builder_guard_dir="$workdir/builder-output-guards"
mkdir "$builder_guard_dir"
ln -s missing-target "$builder_guard_dir/$X_ARTIFACT_BASENAME"
expect_reject builder-dangling-output-symlink "$candidate_builder" \
	--package "$package" --baseline "$w_baseline" \
	--output "$builder_guard_dir/$X_ARTIFACT_BASENAME"
mkdir "$builder_guard_dir/existing"
expect_reject builder-existing-output "$candidate_builder" --package "$package" \
	--baseline "$w_baseline" --output "$builder_guard_dir/existing"
expect_reject builder-wrong-output-name "$candidate_builder" --package "$package" \
	--baseline "$w_baseline" --output "$builder_guard_dir/candidate-X-wrong"
expect_reject builder-output-inside-package "$candidate_builder" --package "$package" \
	--baseline "$w_baseline" --output "$package/$X_ARTIFACT_BASENAME"
expect_reject builder-output-inside-baseline "$candidate_builder" --package "$package" \
	--baseline "$w_baseline" --output "$w_baseline/$X_ARTIFACT_BASENAME"
expect_reject builder-output-inside-repository "$candidate_builder" --package "$package" \
	--baseline "$w_baseline" --output "$repo_root/$X_ARTIFACT_BASENAME"
expect_reject builder-missing-parent-inside-package "$candidate_builder" \
	--package "$package" --baseline "$w_baseline" \
	--output "$package/forbidden-output-parent/$X_ARTIFACT_BASENAME"
[[ ! -e "$package/forbidden-output-parent" && \
	! -L "$package/forbidden-output-parent" ]] || \
	die "builder created a forbidden output parent"

package_link="$workdir/selected-package-link"
baseline_link="$workdir/selected-baseline-link"
ln -s "$package" "$package_link"
ln -s "$w_baseline" "$baseline_link"
expect_reject builder-package-symlink "$candidate_builder" --package "$package_link" \
	--baseline "$w_baseline" --output "$builder_guard_dir/pkg-link/$X_ARTIFACT_BASENAME"
expect_reject builder-baseline-symlink "$candidate_builder" --package "$package" \
	--baseline "$baseline_link" --output "$builder_guard_dir/base-link/$X_ARTIFACT_BASENAME"
expect_reject selected-source-symlink-copy copy_selected_tree "$package_link" \
	"$workdir/forbidden-copy"

# Exact Candidate W baseline identity, inventory, and mode.
wrong_name="$workdir/candidate-w-wrong-name"
cp -a "$w_baseline" "$wrong_name"
expect_reject w-baseline-name "$baseline_validator" --baseline "$wrong_name"
expect_reject w-baseline-symlink "$baseline_validator" --baseline "$baseline_link"
bad_w="$(new_w_baseline boot-byte)"
printf '\001' >>"$bad_w/gemini-keyboard-wrrd.boot.img"
refresh_manifest "$bad_w"
expect_reject w-baseline-coherent-boot "$baseline_validator" --baseline "$bad_w"
bad_w="$(new_w_baseline valid-dtb)"
fdtput -t x "$bad_w/mt6797-gemini-pda-keyboard-wrrd.dtb" \
	/keyboard-matrix poll-interval 21
refresh_manifest "$bad_w"
expect_reject w-baseline-coherent-dtb "$baseline_validator" --baseline "$bad_w"
bad_w="$(new_w_baseline helper-mode)"
chmod 0600 "$bad_w/input-event-capture"
expect_reject w-baseline-helper-mode "$baseline_validator" --baseline "$bad_w"
bad_w="$(new_w_baseline symlink-entry)"
ln -s provenance.txt "$bad_w/unexpected-link"
expect_reject w-baseline-symlink-entry "$baseline_validator" --baseline "$bad_w"

# Repository/package provenance and resolved-config invariants.
fixture_repo="$workdir/repository-fixture"
mkdir "$fixture_repo"
cp -a "$repo_root/kernel" "$repo_root/patches" "$repo_root/configs" "$fixture_repo/"
printf '\n# local coherent controller mutation\n' \
	>>"$fixture_repo/patches/v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
expect_reject local-controller-substitution "$package_validator" --package "$package" \
	--manifest "$fixture_repo/kernel/manifest.json"

bad_package="$(new_package extra-file)"
printf 'mutation\n' >"$bad_package/unexpected-file"
refresh_manifest "$bad_package"
expect_reject package-extra-file validate_selected_package "$bad_package"

bad_package="$(new_package unrelated-config)"
printf '# coherent unrelated config mutation\n' >>"$bad_package/kernel.config"
config_hash="$(sha256sum "$bad_package/kernel.config" | awk '{print $1}')"
jq --arg value "$config_hash" '.config_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_manifest "$bad_package"
expect_reject package-unrelated-coherent-config "$package_validator" \
	--package "$bad_package" --manifest "$manifest"

bad_package="$(new_package virtual-console)"
sed -i 's/^CONFIG_CMDLINE="console=ttyS0/CONFIG_CMDLINE="console=tty1 console=ttyS0/' \
	"$bad_package/kernel.config"
config_hash="$(sha256sum "$bad_package/kernel.config" | awk '{print $1}')"
jq --arg value "$config_hash" '.config_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_manifest "$bad_package"
expect_reject package-virtual-console "$package_validator" --package "$bad_package" \
	--manifest "$manifest"

bad_package="$(new_package watchdog-policy)"
sed -i 's/^CONFIG_WATCHDOG_OPEN_TIMEOUT=0$/CONFIG_WATCHDOG_OPEN_TIMEOUT=30/' \
	"$bad_package/kernel.config"
config_hash="$(sha256sum "$bad_package/kernel.config" | awk '{print $1}')"
jq --arg value "$config_hash" '.config_sha256 = $value' \
	"$bad_package/provenance/build.json" >"$workdir/build.json"
mv "$workdir/build.json" "$bad_package/provenance/build.json"
refresh_manifest "$bad_package"
expect_reject package-watchdog-policy "$package_validator" --package "$bad_package" \
	--manifest "$manifest"

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
expect_reject package-coherent-patchset "$package_validator" --package "$bad_package" \
	--manifest "$manifest"

bad_package="$(new_package provenance-symlink)"
ln -s build.json "$bad_package/provenance/configs/unexpected-link"
expect_reject package-provenance-symlink "$package_validator" \
	--package "$bad_package" --manifest "$manifest"
bad_package="$(new_package provenance-empty-directory)"
mkdir "$bad_package/provenance/configs/unexpected-directory"
expect_reject package-provenance-empty-directory "$package_validator" \
	--package "$bad_package" --manifest "$manifest"

# Initramfs byte identity, unsafe archive handling, and semantic exclusions.
cp "$x_initramfs" "$workdir/initramfs-byte.img"
printf '\001' >>"$workdir/initramfs-byte.img"
expect_reject initramfs-byte "$initramfs_validator" --baseline "$w_initramfs" \
	--candidate "$workdir/initramfs-byte.img" --helper "$helper"
cp "$helper" "$workdir/helper-byte"
printf '\001' >>"$workdir/helper-byte"
chmod 0755 "$workdir/helper-byte"
expect_reject helper-byte "$initramfs_validator" --baseline "$w_initramfs" \
	--candidate "$x_initramfs" --helper "$workdir/helper-byte"

gzip -dc "$x_initramfs" | gzip -n -1 >"$workdir/initramfs-noncanonical-gzip.img"
expect_reject initramfs-noncanonical-gzip "$initramfs_validator" \
	--baseline "$w_initramfs" --candidate "$workdir/initramfs-noncanonical-gzip.img" \
	--helper "$helper"
python3 - "$x_initramfs" "$workdir/initramfs-unsafe-path.img" <<'PY'
import gzip
import pathlib
import sys

raw = gzip.decompress(pathlib.Path(sys.argv[1]).read_bytes())
old = b"bin/cat\0"
new = b"../evil\0"
if raw.count(old) != 1 or len(old) != len(new):
    raise SystemExit("unexpected canonical archive fixture")
pathlib.Path(sys.argv[2]).write_bytes(gzip.compress(raw.replace(old, new), compresslevel=9, mtime=0))
PY
expect_reject initramfs-unsafe-path "$initramfs_validator" --baseline "$w_initramfs" \
	--candidate "$workdir/initramfs-unsafe-path.img" --helper "$helper"

fixture="$(new_semantic_fixture watchdog-access)"
printf '\n/dev/watchdog0\n' >>"$fixture/root/bin/x-probe"
printf '\n/dev/watchdog0\n' >>"$fixture/experiment/initramfs/x-probe"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-watchdog-access validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture visible-sink)"
printf '\nprintf test >/dev/tty1\n' >>"$fixture/root/bin/x-record"
printf '\nprintf test >/dev/tty1\n' >>"$fixture/experiment/initramfs/x-record"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-visible-background-sink validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture automatic-reboot)"
printf '\n/bin/reboot\n' >>"$fixture/root/bin/x-probe"
printf '\n/bin/reboot\n' >>"$fixture/experiment/initramfs/x-probe"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-automatic-reboot validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture reboot-sync)"
sed -i '/^\/bin\/busybox reboot -n -f$/i /bin/busybox sync' \
	"$fixture/root/bin/reboot" "$fixture/experiment/initramfs/reboot"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-reboot-sync validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture second-reboot)"
printf '\n/bin/busybox reboot -n -f\n' >>"$fixture/root/bin/reboot"
printf '\n/bin/busybox reboot -n -f\n' >>"$fixture/experiment/initramfs/reboot"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-second-reboot validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture missing-intent)"
sed -i '/manual_reboot=requested method=busybox-forced storage_access=none/d' \
	"$fixture/root/bin/reboot" "$fixture/experiment/initramfs/reboot"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-missing-reboot-intent validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture extra-member)"
printf 'unexpected\n' >"$fixture/root/unexpected-file"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-extra-member validate_semantic_fixture "$fixture"

fixture="$(new_semantic_fixture reboot-symlink)"
rm "$fixture/root/bin/reboot"
ln -s busybox "$fixture/root/bin/reboot"
rebuild_semantic_fixture "$fixture"
expect_reject initramfs-reboot-symlink validate_semantic_fixture "$fixture"

# Exact component hashes reject coherently reconstructed Android-v0 substitutions.
cp "$x_boot" "$workdir/boot-byte.img"
printf '\001' >>"$workdir/boot-byte.img"
expect_reject boot-byte validate_boot "$workdir/boot-byte.img" "$image_gz" \
	"$x_dtb" "$x_initramfs"
cp "$x_dtb" "$workdir/valid-mutated.dtb"
fdtput -t x "$workdir/valid-mutated.dtb" /keyboard-matrix poll-interval 21
python3 "$serializer" --kernel "$image_gz" --ramdisk "$x_initramfs" \
	--dtb "$workdir/valid-mutated.dtb" --output "$workdir/coherent-dtb.boot.img" \
	--name gemini-obs-L --cmdline bootopt=64S3,32N2,64N2 \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-dtb-substitution validate_boot "$workdir/coherent-dtb.boot.img" \
	"$image_gz" "$workdir/valid-mutated.dtb" "$x_initramfs"
gzip -n -1 -c "$image" >"$workdir/substituted-Image.gz"
python3 "$serializer" --kernel "$workdir/substituted-Image.gz" \
	--ramdisk "$x_initramfs" --dtb "$x_dtb" \
	--output "$workdir/coherent-image.boot.img" --name gemini-obs-L \
	--cmdline bootopt=64S3,32N2,64N2 --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-image-substitution validate_boot "$workdir/coherent-image.boot.img" \
	"$workdir/substituted-Image.gz" "$x_dtb" "$x_initramfs"
python3 "$serializer" --kernel "$image_gz" --ramdisk "$workdir/initramfs-byte.img" \
	--dtb "$x_dtb" --output "$workdir/coherent-initramfs.boot.img" \
	--name gemini-obs-L --cmdline bootopt=64S3,32N2,64N2 \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
expect_reject coherent-initramfs-substitution validate_boot \
	"$workdir/coherent-initramfs.boot.img" "$image_gz" "$x_dtb" \
	"$workdir/initramfs-byte.img"

# Final artifact must remain flat, regular, mode-exact, and rebuild-identical.
bad_x="$(new_x_artifact extra-file)"
printf 'mutation\n' >"$bad_x/unexpected-file"
refresh_manifest "$bad_x"
expect_reject x-artifact-coherent-extra-file validate_selected_x_artifact "$bad_x"
bad_x="$(new_x_artifact nested-file)"
mkdir "$bad_x/unexpected-directory"
printf 'mutation\n' >"$bad_x/unexpected-directory/file"
refresh_manifest "$bad_x"
expect_reject x-artifact-nested-entry validate_selected_x_artifact "$bad_x"
bad_x="$(new_x_artifact symlink-entry)"
ln -s provenance.txt "$bad_x/unexpected-link"
expect_reject x-artifact-symlink-entry validate_selected_x_artifact "$bad_x"
bad_x="$(new_x_artifact fifo-entry)"
mkfifo "$bad_x/unexpected-fifo"
expect_reject x-artifact-fifo-entry validate_selected_x_artifact "$bad_x"
bad_x="$(new_x_artifact mode)"
chmod 0644 "$bad_x/provenance.txt"
expect_reject x-artifact-mode validate_selected_x_artifact "$bad_x"
bad_x="$(new_x_artifact provenance)"
printf 'forged_provenance=yes\n' >>"$bad_x/provenance.txt"
refresh_manifest "$bad_x"
expect_reject x-artifact-coherent-provenance validate_selected_x_replica "$bad_x"

printf 'validation=candidate-x-validator-mutations\n'
printf '%s\n' \
	'positive_controls=selected-package,w-baseline,deterministic-x-rebuild,x-artifact,exact-w-dtb,initramfs,android-v0,lk,tmpdir-isolation'
printf 'rejection_count=%s\n' "$(wc -l <"$rejections")"
rejected_mutations="$(sort "$rejections" | awk '
	BEGIN { separator="" }
	{ printf "%s%s", separator, $0; separator="," }
')"
printf 'rejected_mutations=%s\n' "$rejected_mutations"
printf 'hardware_write=none\nflash=none\n'
