#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --baseline Z_INITRAMFS --defkeymap FILE --output FILE --keymap-output FILE --helper-output FILE --verifier-output FILE\n' "$0" >&2
}

baseline=
defkeymap=
output=
keymap_output=
helper_output=
verifier_output=
while (($#)); do
	case "$1" in
	--baseline|--defkeymap|--output|--keymap-output|--helper-output|--verifier-output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--baseline) baseline=$2 ;;
		--defkeymap) defkeymap=$2 ;;
		--output) output=$2 ;;
		--keymap-output) keymap_output=$2 ;;
		--helper-output) helper_output=$2 ;;
		--verifier-output) verifier_output=$2 ;;
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
*) die 'Candidate AA helper must be built on Linux aarch64' ;;
esac
for path in "$baseline" "$defkeymap"; do
	[[ -f "$path" && ! -L "$path" ]] || die "required regular input absent: $path"
done
for path in "$output" "$keymap_output" "$helper_output" "$verifier_output"; do
	[[ -n "$path" && -d "$(dirname -- "$path")" ]] || die 'every output parent must exist'
	[[ ! -e "$path" && ! -L "$path" ]] || die "refusing to overwrite $path"
done
[[ "$output" != "$keymap_output" && "$output" != "$helper_output" && \
	"$output" != "$verifier_output" && "$keymap_output" != "$helper_output" && \
	"$keymap_output" != "$verifier_output" && \
	"$helper_output" != "$verifier_output" ]] || die 'outputs must be distinct'
for command in awk cc chmod cmp cpio dirname find grep gzip install mkdir mktemp mv \
	python3 readelf rm sha256sum sort touch uname; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

readonly Z_INITRAMFS_SHA256=a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2
readonly DEFKEYMAP_SHA256=318f48316e6bed5ada064879535ec2bca470dc1a8b8c9abd1d92da81bb2c6c7c
readonly KEYMAP_SHA256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c
readonly UNICODE_SOURCE_SHA256=4a3f8064dddb5845886453bc0fdc5753e87b3f6ef8ce064c0c2a32fb7c7bf357
readonly UNICODE_HELPER_SHA256=5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650
readonly VERIFIER_SOURCE_SHA256=70d70bcef6e403d850c32b85f4bab928b2eb1444fae68ec3f629d7ff7c22785d
readonly KEYMAP_VERIFIER_SHA256=29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238
[[ "$(sha256sum "$baseline" | awk '{print $1}')" == "$Z_INITRAMFS_SHA256" ]] || \
	die 'baseline is not exact Candidate Z initramfs'
[[ "$(sha256sum "$defkeymap" | awk '{print $1}')" == "$DEFKEYMAP_SHA256" ]] || \
	die 'defkeymap input is not the pinned Linux v7.1 source'

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
source_dir="$experiment_dir/initramfs"
unicode_source="$experiment_dir/src/console-unicode-mode.c"
verifier_source="$experiment_dir/src/console-keymap-verify.c"
generator="$script_dir/generate-console-keymap.py"
keymap_validator="$script_dir/validate-console-keymap.py"
verifier_test="$script_dir/test-keymap-verifier.py"
initramfs_validator="$script_dir/validate-initramfs.py"
for path in "$unicode_source" "$verifier_source" "$generator" "$keymap_validator" \
	"$verifier_test" "$initramfs_validator" \
	"$source_dir/init" "$source_dir/local-shell" "$source_dir/x-record"; do
	[[ -f "$path" && ! -L "$path" ]] || die "repository input missing or unsafe: $path"
done

hash_inputs() {
	sha256sum "$unicode_source" "$verifier_source" "$generator" \
		"$keymap_validator" "$verifier_test" "$initramfs_validator" "$source_dir/init" \
		"$source_dir/local-shell" "$source_dir/x-record"
}
inputs_at_start="$(hash_inputs)"
workdir="$(mktemp -d /tmp/candidate-aa-initramfs.XXXXXX)"
cleanup() { [[ ! -d "$workdir" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT

helper_flags=(
	-static -std=c11 -Os -Wall -Wextra -Werror -fno-ident
	-fno-asynchronous-unwind-tables -fno-stack-protector
	-Wl,--build-id=none -s
)
[[ "$(sha256sum "$unicode_source" | awk '{print $1}')" == "$UNICODE_SOURCE_SHA256" ]] || \
	die 'console Unicode helper source identity changed'
[[ "$(sha256sum "$verifier_source" | awk '{print $1}')" == "$VERIFIER_SOURCE_SHA256" ]] || \
	die 'console keymap verifier source identity changed'
cc "${helper_flags[@]}" -o "$workdir/console-unicode-mode-1" "$unicode_source"
cc "${helper_flags[@]}" -o "$workdir/console-unicode-mode-2" "$unicode_source"
cmp -s "$workdir/console-unicode-mode-1" "$workdir/console-unicode-mode-2" || \
	die 'two console-mode helper builds differ'
readelf -h "$workdir/console-unicode-mode-1" | grep -Fq 'Machine:                           AArch64' || \
	die 'console-mode helper is not AArch64'
if readelf -l "$workdir/console-unicode-mode-1" | grep -Fq INTERP; then
	die 'console-mode helper is dynamically linked'
fi
chmod 0700 "$workdir/console-unicode-mode-1"
[[ "$(sha256sum "$workdir/console-unicode-mode-1" | awk '{print $1}')" == \
	"$UNICODE_HELPER_SHA256" ]] || die 'console-mode helper binary identity changed'

cc "${helper_flags[@]}" -o "$workdir/console-keymap-verify-1" "$verifier_source"
cc "${helper_flags[@]}" -o "$workdir/console-keymap-verify-2" "$verifier_source"
cmp -s "$workdir/console-keymap-verify-1" "$workdir/console-keymap-verify-2" || \
	die 'two console keymap verifier builds differ'
readelf -h "$workdir/console-keymap-verify-1" | \
	grep -Fq 'Machine:                           AArch64' || \
	die 'console keymap verifier is not AArch64'
if readelf -l "$workdir/console-keymap-verify-1" | grep -Fq INTERP; then
	die 'console keymap verifier is dynamically linked'
fi
chmod 0700 "$workdir/console-keymap-verify-1"
[[ "$(sha256sum "$workdir/console-keymap-verify-1" | awk '{print $1}')" == \
	"$KEYMAP_VERIFIER_SHA256" ]] || die 'console keymap verifier binary identity changed'

python3 "$generator" --source "$defkeymap" --output "$workdir/gemini-us-1.bkeymap" \
	>"$workdir/keymap-generation.txt"
python3 "$generator" --source "$defkeymap" --output "$workdir/gemini-us-2.bkeymap" \
	>/dev/null
cmp -s "$workdir/gemini-us-1.bkeymap" "$workdir/gemini-us-2.bkeymap" || \
	die 'two generated Gemini keymaps differ'
[[ "$(sha256sum "$workdir/gemini-us-1.bkeymap" | awk '{print $1}')" == "$KEYMAP_SHA256" ]] || \
	die 'generated Gemini keymap identity changed'
python3 "$keymap_validator" --source "$defkeymap" \
	--keymap "$workdir/gemini-us-1.bkeymap" >"$workdir/keymap-validation.txt"
python3 "$verifier_test" --verifier "$workdir/console-keymap-verify-1" \
	--keymap "$workdir/gemini-us-1.bkeymap" >"$workdir/keymap-verifier-test.txt"

mkdir "$workdir/root"
gzip -dc "$baseline" | (cd "$workdir/root" && cpio -idmu --quiet)
# The extraction root pre-exists, so cpio does not restore the archived `.` mode.
chmod 0755 "$workdir/root"
install -m 0755 "$source_dir/init" "$workdir/root/init"
install -m 0755 "$source_dir/local-shell" "$workdir/root/bin/local-shell"
install -m 0755 "$source_dir/x-record" "$workdir/root/bin/x-record"
install -m 0755 "$workdir/console-unicode-mode-1" \
	"$workdir/root/bin/console-unicode-mode"
install -m 0755 "$workdir/console-keymap-verify-1" \
	"$workdir/root/bin/console-keymap-verify"
install -m 0444 "$workdir/gemini-us-1.bkeymap" \
	"$workdir/root/etc/gemini-us.bkeymap"
find "$workdir/root" -exec touch -h -d @0 {} +
(
	cd "$workdir/root"
	find . -print0 | sort -z | cpio --null --create --format=newc \
		--owner=0:0 --reproducible --quiet
) | gzip -n -9 >"$workdir/candidate.img"
chmod 0600 "$workdir/candidate.img"

[[ "$(hash_inputs)" == "$inputs_at_start" ]] || die 'repository inputs changed during construction'
python3 "$initramfs_validator" --baseline "$baseline" \
	--candidate "$workdir/candidate.img" --source-dir "$source_dir" \
	--keymap "$workdir/gemini-us-1.bkeymap" \
	--unicode-helper "$workdir/console-unicode-mode-1" \
	--keymap-verifier "$workdir/console-keymap-verify-1" >/dev/null

install -m 0600 "$workdir/gemini-us-1.bkeymap" "$workdir/final-keymap"
install -m 0700 "$workdir/console-unicode-mode-1" "$workdir/final-helper"
install -m 0700 "$workdir/console-keymap-verify-1" "$workdir/final-verifier"
mv --no-clobber --no-target-directory -- "$workdir/final-keymap" "$keymap_output"
mv --no-clobber --no-target-directory -- "$workdir/final-helper" "$helper_output"
mv --no-clobber --no-target-directory -- "$workdir/final-verifier" "$verifier_output"
mv --no-clobber --no-target-directory -- "$workdir/candidate.img" "$output"
[[ -f "$output" && -f "$keymap_output" && -f "$helper_output" && \
	-f "$verifier_output" ]] || \
	die 'atomic output handoff failed'

printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'baseline=exact-candidate-z\n'
printf 'changed_members=init,bin/local-shell,bin/x-record\n'
printf 'added_members=bin/console-keymap-verify,bin/console-unicode-mode,etc/gemini-us.bkeymap\n'
printf 'keymap_sha256=%s\n' "$KEYMAP_SHA256"
printf 'unicode_helper_sha256=%s\n' "$(sha256sum "$helper_output" | awk '{print $1}')"
printf 'keymap_verifier_sha256=%s\n' "$(sha256sum "$verifier_output" | awk '{print $1}')"
printf 'helper_compiler=%s\n' "$(cc --version | head -n 1)"
printf 'helper_reproducible_builds=2-each\nkeymap_reproducible_generations=2\n'
printf 'keymap_parser_tests=11-of-11\n'
printf 'runtime_gate=sha256-K_UNICODE-existing-KDG-or-preflight-load-KDGKBENT-2048-kernel-entries\n'
printf 'watchdog_recovery=byte-exact-candidate-z\n'
printf 'hardware_write=none\n'
