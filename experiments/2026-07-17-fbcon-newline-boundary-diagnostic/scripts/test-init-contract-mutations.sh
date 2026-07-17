#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
validator="${script_dir}/validate-init-contract.sh"
source_init="${experiment_dir}/initramfs/init"
for input in "$validator" "$source_init"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done
for command in cat cp grep mktemp sed; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

workdir="$(mktemp -d "${TMPDIR:-/tmp}/gemini-k-init-mutations.XXXXXX")"
cleanup() {
	rm -rf "$workdir"
}
trap cleanup EXIT

expect_reject() {
	local expected=$1
	local mutated=$2
	if "$validator" --init "$mutated" >"${workdir}/out" 2>"${workdir}/err"; then
		die "validator accepted mutation: $expected"
	fi
	grep -Fq -- "$expected" "${workdir}/err" || {
		cat "${workdir}/err" >&2
		die "validator rejected for an unexpected reason; wanted: $expected"
	}
}

"$validator" --init "$source_init" >/dev/null

mutated="${workdir}/phase1-count"
cp "$source_init" "$mutated"
sed -i.bak 's/readonly CR_TICKS=20/readonly CR_TICKS=19/' "$mutated"
expect_reject "phase 1 must contain exactly 20 iterations" "$mutated"

mutated="${workdir}/phase1-newline"
cp "$source_init" "$mutated"
sed -i.bak "s/printf '\\\\r%s'/printf '\\\\r%s\\\\n'/" "$mutated"
expect_reject "phase-1 emitter must use leading carriage return with no newline" "$mutated"

mutated="${workdir}/storage-access"
cp "$source_init" "$mutated"
sed -i.bak '/export PATH/a\
readonly FORBIDDEN_DEVICE=/dev/mmcblk0' "$mutated"
expect_reject "forbidden storage, framebuffer, raw-memory, MMIO, I2C, reset, watchdog, network, USB, or sysfs-control access" "$mutated"

mutated="${workdir}/sysfs-control-access"
cp "$source_init" "$mutated"
sed -i.bak '/export PATH/a\
readonly FORBIDDEN_CONTROL=/sys/class/udc/dummy_udc.0' "$mutated"
expect_reject "forbidden storage, framebuffer, raw-memory, MMIO, I2C, reset, watchdog, network, USB, or sysfs-control access" "$mutated"

mutated="${workdir}/extra-write"
cp "$source_init" "$mutated"
sed -i.bak '$a\
emit_line "unexpected"' "$mutated"
expect_reject "static hold must be the final console-write call" "$mutated"

printf 'validation=candidate-k-init-contract-mutations\n'
printf 'positive_contract=passed\n'
printf 'mutated_phase1_bound=rejected\n'
printf 'mutated_phase1_newline=rejected\n'
printf 'mutated_storage_access=rejected\n'
printf 'mutated_sysfs_control_access=rejected\n'
printf 'mutated_post-hold-write=rejected\n'
printf 'temporary_mutations_only=yes\n'
printf 'hardware_write=none\n'
