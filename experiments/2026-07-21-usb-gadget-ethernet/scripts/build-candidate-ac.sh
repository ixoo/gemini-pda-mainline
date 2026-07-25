#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline EXACT_AB_ARTIFACT --output-parent DIR\n' "$0" >&2
}

baseline=
output_parent=
while (($#)); do
	case "$1" in
	--baseline|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline) baseline=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run inside the Linux development VM'
case "$(uname -m)" in
aarch64|arm64) ;;
*) die 'Candidate AC must be built on Linux aarch64' ;;
esac
[[ -d "$baseline" && ! -L "$baseline" && -d "$output_parent" && \
	! -L "$output_parent" ]] || \
	die 'exact AB artifact and output parent are required'
for command in awk chmod cmp dirname find git grep install mkdir mktemp mv \
	python3 rm sha256sum sort touch tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$baseline"|"$baseline"/*)
	die 'output parent must be outside repository and AB baseline'
	;;
esac

baseline_validator="$script_dir/validate-ab-baseline.py"
initramfs_builder="$script_dir/build-initramfs.sh"
initramfs_validator="$script_dir/validate-initramfs.py"
boot_validator="$script_dir/validate-boot.py"
final_validator="$script_dir/validate-final-artifact.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$baseline_validator" "$initramfs_builder" "$initramfs_validator" \
	"$boot_validator" "$final_validator" "$serializer" "$analyzer"; do
	[[ -s "$input" && ! -L "$input" ]] || die "required repository input missing: $input"
done

repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
[[ "$repo_revision" =~ ^[0-9a-f]{40}$|^[0-9a-f]{64}$ ]] || \
	die 'repository revision is not a full object ID'
input_tree_at_start="$(
	python3 "$final_validator" --hash-input-tree --repo-root "$repo_root"
)"

hash_baseline() {
	local unexpected
	unexpected="$(find "$baseline" -mindepth 1 -maxdepth 1 ! -type f -print -quit)"
	[[ -z "$unexpected" ]] || die "unsafe AB baseline entry: $unexpected"
	find "$baseline" -mindepth 1 -maxdepth 1 -type f -print0 | \
		sort -z | xargs -0 sha256sum
}
baseline_at_start="$(hash_baseline)"

workdir="$(mktemp -d "$output_parent/.candidate-AC.XXXXXX")"
cleanup() {
	if [[ -n "${workdir:-}" && -d "$workdir" ]]; then
		rm -rf -- "$workdir"
	fi
}
trap cleanup EXIT
stage="$workdir/stage"
inputs="$workdir/validated-inputs"
replica="$workdir/replica"
mkdir "$stage" "$inputs" "$replica"

normalize_log() {
	local source=$1
	local temporary="${source}.normalized"
	while IFS= read -r line || [[ -n "$line" ]]; do
		line=${line//"$workdir"/@WORK@}
		line=${line//"$baseline"/@CANDIDATE_AB@}
		line=${line//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$line"
	done <"$source" >"$temporary"
	mv "$temporary" "$source"
}

python3 "$baseline_validator" --artifact "$baseline" \
	>"$stage/ab-baseline-validation.txt"
normalize_log "$stage/ab-baseline-validation.txt"
[[ "$(hash_baseline)" == "$baseline_at_start" ]] || \
	die 'AB baseline changed during validation'

# Snapshot every assembly byte only after exact AB validation passes.
install -m 0600 "$baseline/Image.gz" "$inputs/Image.gz"
install -m 0600 "$baseline/System.map" "$inputs/System.map"
install -m 0600 "$baseline/source-build.json" "$inputs/source-build.json"
install -m 0600 "$baseline/gemini-mt6797-kernel-restart-initramfs.img" \
	"$inputs/ab-initramfs.img"
install -m 0600 "$baseline/mt6797-gemini-pda-kernel-restart.dtb" \
	"$inputs/ab.dtb"
install -m 0600 "$baseline/gemini-us.bkeymap" "$inputs/gemini-us.bkeymap"
install -m 0700 "$baseline/console-unicode-mode" "$inputs/console-unicode-mode"
install -m 0700 "$baseline/console-keymap-verify" "$inputs/console-keymap-verify"
install -m 0700 "$baseline/input-event-capture" "$inputs/input-event-capture"
[[ "$(hash_baseline)" == "$baseline_at_start" ]] || \
	die 'AB baseline changed during immutable snapshot'

candidate_initramfs="$stage/gemini-usb-gadget-ethernet-initramfs.img"
replica_initramfs="$replica/gemini-usb-gadget-ethernet-initramfs.img"
"$initramfs_builder" --baseline "$inputs/ab-initramfs.img" \
	--output "$candidate_initramfs" >"$stage/initramfs-build.txt"
normalize_log "$stage/initramfs-build.txt"
python3 "$initramfs_validator" --baseline "$inputs/ab-initramfs.img" \
	--candidate "$candidate_initramfs" --source-dir "$experiment_dir/initramfs" \
	>"$stage/initramfs-validation.txt"
normalize_log "$stage/initramfs-validation.txt"
"$initramfs_builder" --baseline "$inputs/ab-initramfs.img" \
	--output "$replica_initramfs" >/dev/null
python3 "$initramfs_validator" --baseline "$inputs/ab-initramfs.img" \
	--candidate "$replica_initramfs" --source-dir "$experiment_dir/initramfs" \
	>/dev/null
cmp -s "$candidate_initramfs" "$replica_initramfs" || \
	die 'two Candidate AC initramfs constructions differ'

candidate_dtb="$stage/mt6797-gemini-pda-usb-gadget-ethernet.dtb"
install -m 0600 "$inputs/ab.dtb" "$candidate_dtb"
candidate="$stage/gemini-usb-gadget-ethernet.boot.img"
replica_boot="$replica/gemini-usb-gadget-ethernet.boot.img"
bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$inputs/Image.gz" \
	--ramdisk "$candidate_initramfs" --dtb "$candidate_dtb" \
	--output "$candidate" --name gemini-obs-L --cmdline "$bootopt" \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
	>"$stage/serializer.raw"
grep -v '^output=' "$stage/serializer.raw" >"$stage/serializer.txt"
rm "$stage/serializer.raw"
normalize_log "$stage/serializer.txt"
python3 "$serializer" --kernel "$inputs/Image.gz" \
	--ramdisk "$replica_initramfs" --dtb "$inputs/ab.dtb" \
	--output "$replica_boot" --name gemini-obs-L --cmdline "$bootopt" \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
cmp -s "$candidate" "$replica_boot" || \
	die 'two Candidate AC Android-v0 constructions differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$inputs/Image.gz" \
	--expected-ramdisk "$candidate_initramfs" --expected-dtb "$candidate_dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$candidate" \
	>"$stage/analysis.txt"
normalize_log "$stage/analysis.txt"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit exactly 32 gates'
python3 "$boot_validator" --candidate "$candidate" \
	--image-gz "$inputs/Image.gz" --dtb "$candidate_dtb" \
	--initramfs "$candidate_initramfs" >"$stage/boot-validation.txt"
normalize_log "$stage/boot-validation.txt"
python3 "$boot_validator" --candidate "$replica_boot" \
	--image-gz "$inputs/Image.gz" --dtb "$inputs/ab.dtb" \
	--initramfs "$replica_initramfs" >/dev/null

install -m 0600 "$inputs/Image.gz" "$stage/Image.gz"
install -m 0600 "$inputs/System.map" "$stage/System.map"
install -m 0600 "$inputs/source-build.json" "$stage/source-build.json"
install -m 0600 "$inputs/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$inputs/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$inputs/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$inputs/input-event-capture" "$stage/input-event-capture"

input_tree_at_end="$(
	python3 "$final_validator" --hash-input-tree --repo-root "$repo_root"
)"
[[ "$input_tree_at_end" == "$input_tree_at_start" ]] || \
	die 'repository build inputs changed during Candidate AC assembly'
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$repo_revision" ]] || \
	die 'repository revision changed during Candidate AC assembly'
[[ "$(hash_baseline)" == "$baseline_at_start" ]] || \
	die 'AB baseline changed during Candidate AC assembly'
printf '%s\n' "$input_tree_at_start" >"$stage/input-tree.sha256"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
candidate_initramfs_sha256="$(sha256sum "$candidate_initramfs" | awk '{print $1}')"
input_tree_sha256="$(sha256sum "$stage/input-tree.sha256" | awk '{print $1}')"
{
	printf 'experiment=2026-07-21-usb-gadget-ethernet\n'
	printf 'candidate_label=AC\n'
	printf 'marker=GEMINI_USB_GADGET_ETHERNET_20260721_AC\n'
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'ab_artifact=candidate-AB-mt6797-kernel-restart-final-61c74592\n'
	printf 'ab_manifest_sha256=f7500569b83cf36e2bfcb0c7db3cef33a3c3776e85615c5719acf64e6f2accb0\n'
	printf 'ab_boot_sha256=61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446\n'
	printf 'ab_initramfs_sha256=b57dc3143e7ca7df90d742bcacc692221b4d7b6d346e5192d7bc68acaac00ea7\n'
	printf 'ab_image_gz_sha256=37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f\n'
	printf 'ab_dtb_sha256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f\n'
	printf 'ab_keymap_sha256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c\n'
	printf 'ab_system_map_sha256=355a547d5ce17dc295d5c66760415c7a2056be1897db57d8325b303eb32c4e63\n'
	printf 'ab_source_build_sha256=c672d58074bde6505e892cf94336de08e2135c6b1197e046db45d83f3551b8a5\n'
	printf 'candidate_image_gz_sha256=37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f\n'
	printf 'candidate_dtb_sha256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f\n'
	printf 'candidate_system_map_sha256=355a547d5ce17dc295d5c66760415c7a2056be1897db57d8325b303eb32c4e63\n'
	printf 'candidate_source_build_sha256=c672d58074bde6505e892cf94336de08e2135c6b1197e046db45d83f3551b8a5\n'
	printf 'candidate_keymap_sha256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c\n'
	printf 'candidate_keymap_verifier_sha256=29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238\n'
	printf 'candidate_unicode_helper_sha256=5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650\n'
	printf 'candidate_input_helper_sha256=b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602\n'
	printf 'candidate_initramfs_sha256=%s\n' "$candidate_initramfs_sha256"
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'boot2_capacity=16777216\n'
	printf 'input_tree_sha256=%s\n' "$input_tree_sha256"
	printf 'kernel_lineage=byte-exact-hardware-passed-ab\n'
	printf 'dtb_lineage=byte-exact-hardware-passed-ab\n'
	printf 'source_build_lineage=byte-exact-hardware-passed-ab\n'
	printf 'initramfs_delta=init,bin/ac-record,bin/usb-net,bin/usb-shell,bin/ip,bin/nc,bin/ping\n'
	printf 'local_console=exact-ab\n'
	printf 'keymap_and_gate=exact-ab\n'
	printf 'reboot_dispatch=exact-ab-ENV-alias-absolute-wrapper\n'
	printf 'manual_reboot=exact-ab-busybox-reboot-no-sync-force\n'
	printf 'usb_interface=usb0\n'
	printf 'device_address=10.15.19.82/24\n'
	printf 'host_address=10.15.19.1/24\n'
	printf 'device_mac=42:00:15:19:82:01\n'
	printf 'host_mac=42:00:15:19:82:00\n'
	printf 'tcp_port=2323\n'
	printf 'usb0_wait_seconds=30\n'
	printf 'tcp_service=busybox-nc--ll--p-2323--e-/bin/usb-shell\n'
	printf 'tcp_shell=unauthenticated-root-direct-trusted-link-only\n'
	printf 'listener_lifetime=persistent-until-reboot\n'
	printf 'usb_descriptor=exact-ab-g_ether\n'
	printf 'runtime_networking=usb0-static-ipv4-direct-link\n'
	printf 'network_side_paths=dhcp-none,route-none,bridge-none,ipv6-none\n'
	printf 'storage_access=none\n'
	printf 'watchdog_userspace=start-none,open-none,ping-none,countdown-none,fallback-none\n'
	printf 'automatic_reboot=none\n'
	printf 'deterministic_replica=initramfs-and-android-v0-byte-identical\n'
	printf 'hardware_write=none\n'
	printf 'flash=none\n'
	printf 'runtime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map \
	ab-baseline-validation.txt analysis.txt boot-validation.txt \
	console-keymap-verify console-unicode-mode \
	gemini-usb-gadget-ethernet-initramfs.img \
	gemini-usb-gadget-ethernet.boot.img gemini-us.bkeymap \
	initramfs-build.txt initramfs-validation.txt input-event-capture \
	input-tree.sha256 mt6797-gemini-pda-usb-gadget-ethernet.dtb \
	provenance.txt serializer.txt source-build.json | sort)"
actual_inventory="$(
	find "$stage" -mindepth 1 -maxdepth 1 -type f -printf '%f\n' | sort
)"
unexpected_entry="$(find "$stage" -mindepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate AC output inventory is not exact'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AC output manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-AC-usb-gadget-ethernet-final-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv --no-clobber --no-target-directory -- "$stage" "$artifact"
stage=
python3 "$final_validator" --artifact "$artifact" --baseline "$baseline" >/dev/null
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv --no-clobber --no-target-directory -- "$artifact" "$output"
[[ -d "$output" && ! -L "$output" && ! -e "$artifact" ]] || \
	die 'atomic Candidate AC artifact handoff failed'
# The validated artifact has moved out of the private construction directory.
# Remove the remaining immutable-input and replica snapshots instead of leaving
# hidden build state beside the published artifact.
cleanup
workdir=
trap - EXIT

printf 'validation=candidate-ac-usb-gadget-ethernet\n'
printf 'artifact=%s\n' "$output"
printf 'candidate=%s/gemini-usb-gadget-ethernet.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
	"$candidate_sha256" "$candidate_size"
printf 'kernel_lineage=byte-exact-hardware-passed-ab\n'
printf 'dtb_lineage=byte-exact-hardware-passed-ab\n'
printf 'runtime_networking=usb0-static-ipv4-direct-link\n'
printf 'tcp_service=10.15.19.82:2323,busybox-nc-persistent-shell\n'
printf 'local_console_keymap_reboot=exact-ab\n'
printf 'watchdog_userspace=none\nautomatic_reboot=none\n'
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
