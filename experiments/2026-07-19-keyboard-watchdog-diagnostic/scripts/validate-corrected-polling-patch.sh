#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --patch FILE\n' "$0" >&2; }

patch_file=
while (($#)); do
	case "$1" in
		--patch) patch_file=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ -s "$patch_file" ]] || die "polling patch is missing"
for command in awk grep mktemp rm sed sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
readonly expected_sha256=4a183e91b07fb5d62e005d94bf1b416c798555945b93047b5619ceca4a0d09de
actual_sha256="$(sha256sum "$patch_file" | awk '{print $1}')"
[[ "$actual_sha256" == "$expected_sha256" ]] || die "polling patch hash mismatch"

[[ "$(grep -c '^diff --git ' "$patch_file")" == 1 ]] || \
	die "polling implementation patch must change one file"
grep -Fqx 'diff --git a/drivers/input/keyboard/matrix_keypad.c b/drivers/input/keyboard/matrix_keypad.c' \
	"$patch_file" || die "polling patch target changed"

added="$(mktemp)"
trap 'rm -f "$added"' EXIT
sed -n 's/^+\([^+]\)/\1/p' "$patch_file" >"$added"
for required in \
	'static void matrix_keypad_cancel_work(void *data)' \
	'cancel_delayed_work_sync(&keypad->work);' \
	'err = devm_add_action_or_reset(&pdev->dev, matrix_keypad_cancel_work,' \
	'guard(mutex)(&input_dev->mutex);' \
	'if (input_device_enabled(input_dev)) {' \
	'device_property_read_u32(&pdev->dev, "poll-interval",'; do
	grep -Fq "$required" "$added" || die "corrected polling patch lacks: $required"
done
[[ "$(grep -Fxc $'\tguard(mutex)(&input_dev->mutex);' "$added")" == 2 ]] || \
	die "suspend and resume must both lock the input mutex"
[[ "$(grep -Fxc $'\tif (input_device_enabled(input_dev)) {' "$added")" == 2 ]] || \
	die "suspend and resume must both gate on enabled input state"

cleanup_line="$(grep -nF 'devm_add_action_or_reset(&pdev->dev, matrix_keypad_cancel_work,' \
	"$added" | awk -F: 'NR == 1 {print $1}')"
register_line="$(grep -nF 'err = input_register_device(keypad->input_dev);' \
	"$patch_file" | awk -F: 'NR == 1 {print $1}')"
[[ "$cleanup_line" =~ ^[0-9]+$ && "$register_line" =~ ^[0-9]+$ ]] || \
	die "could not resolve cleanup and registration ordering"
# The added-lines view and patch view use different line spaces. Confirm order
# directly in the patch as a second, comparable pair.
cleanup_patch_line="$(grep -nF 'devm_add_action_or_reset(&pdev->dev, matrix_keypad_cancel_work,' \
	"$patch_file" | awk -F: 'NR == 1 {print $1}')"
[[ "$cleanup_patch_line" -lt "$register_line" ]] || \
	die "managed work cleanup must be registered before input registration"

printf 'validation=candidate-v-corrected-polling-patch\n'
printf 'patch_sha256=%s\n' "$actual_sha256"
printf 'lifecycle=managed-cancel-before-input-registration\n'
printf 'suspend_resume=input-mutex-plus-enabled-state\n'
printf 'hardware_write=none\n'
