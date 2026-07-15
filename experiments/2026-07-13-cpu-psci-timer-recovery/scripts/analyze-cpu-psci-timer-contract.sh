#!/usr/bin/env bash

# Compare MT6797 CPU/PSCI/timer source contracts with Linux 7.1.3. This is a
# source-only analyzer: vendor files are read from immutable Git objects and
# are never copied into the repository.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}

[[ -d "$vendor_tree/.git" ]] || { printf 'missing vendor Git tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

vendor_show() {
	git -C "$vendor_tree" show "HEAD:$1"
}

vendor_hash() {
	if git -C "$vendor_tree" cat-file -e "HEAD:$1" 2>/dev/null; then
		git -C "$vendor_tree" rev-parse "HEAD:$1"
	else
		printf 'missing'
	fi
}

linux_hash() {
	sha256sum "$linux_tree/$1" 2>/dev/null | awk '{print $1}' || printf 'missing'
}

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD)"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_commit=%s\n' "$(git -C "$linux_tree" rev-parse --verify HEAD 2>/dev/null || printf unknown)"

printf '\n[source hashes]\n'
for path in \
	arch/arm64/boot/dts/mt6797.dtsi \
	arch/arm64/kernel/psci.c \
	drivers/clocksource/arch_timer_mt6797.c \
	drivers/misc/mediatek/base/power/spm_v2/mt_spm.c \
	drivers/misc/mediatek/base/power/mt6797/mt_cpu_psci_ops.h; do
	printf 'vendor.%s=%s\n' "$path" "$(vendor_hash "$path")"
done
for path in \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	drivers/clocksource/arm_arch_timer.c \
	drivers/firmware/psci/psci.c \
	arch/arm64/kernel/cpu_ops.c \
	drivers/of/cpu.c \
	Documentation/devicetree/bindings/arm/cpus.yaml \
	drivers/clocksource/timer-probe.c \
	Documentation/devicetree/bindings/timer/arm,arch_timer.yaml \
	Documentation/devicetree/bindings/arm/psci.yaml; do
	printf 'linux.%s=%s\n' "$path" "$(linux_hash "$path")"
done

printf '\n[vendor CPU/PSCI/timer DT]\n'
vendor_show arch/arm64/boot/dts/mt6797.dtsi |
	rg -n -A 18 -B 3 'cpu@000|cpu@100|cpu@200|idle-states|arm,psci-suspend-param|enable-method|cpu-release-addr|psci|armv8-timer|clock-frequency' |
	head -n 520 || true

printf '\n[vendor PSCI/idle/PM source anchors]\n'
git -C "$vendor_tree" grep -n -E 'psci|cpu_suspend|cpu_on|arm,psci-suspend-param|spm|wfi|arch_timer|timer' -- \
	arch/arm64 drivers/clocksource drivers/misc/mediatek/base/power 2>/dev/null |
	head -n 320 || true

printf '\n[Linux 7.1.3 generic PSCI/timer contracts]\n'
rg -n -C 3 'psci-0\.2|cpu_on|cpu_off|cpu_suspend|affinity_info|enable-method|armv8-timer|clock-frequency|interrupts' \
	"$linux_tree/drivers/firmware/psci/psci.c" \
	"$linux_tree/drivers/clocksource/arm_arch_timer.c" \
	"$linux_tree/Documentation/devicetree/bindings/timer/arm,arch_timer.yaml" \
	"$linux_tree/Documentation/devicetree/bindings/arm/psci.yaml" |
	head -n 520 || true

printf '\n[Linux 7.1.3 CPU frequency-property audit]\n'
rg -n -C 3 'clock-frequency|unevaluatedProperties|enable-method|cpu-idle-states|cpu-release-addr' \
	"$linux_tree/Documentation/devicetree/bindings/arm/cpus.yaml" \
	"$linux_tree/arch/arm64/kernel/cpu_ops.c" \
	"$linux_tree/drivers/of/cpu.c" \
	"$linux_tree/drivers/cpufreq" -g '*.c' -g '*.h' -g '*.yaml' |
	head -n 320 || true

printf '\n[Linux MT6797 CPU/timer DTS]\n'
rg -n -A 24 -B 3 'cpu@|idle-states|psci|timer' \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi" |
	head -n 360 || true

printf '\n[local Gemini CPU/timer declarations]\n'
patch="$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"
if [ -r "$patch" ]; then
	rg -n -C 5 'cpu[0-9]|clock-frequency|psci|idle-states|timer|arch_timer' "$patch" || true
	if rg -q '^[+&]cpu[0-9]+[[:space:]]*\{[[:space:]]*clock-frequency' "$patch"; then
		echo 'local_cpu_clock_frequency=present'
	else
		echo 'local_cpu_clock_frequency=omitted_after_cpu_binding_audit'
	fi
else
	echo 'local_patch=not_visible_from_guest'
fi

printf '\n[decision]\n'
printf '%s\n' \
	'live_topology_is_10_cpus_8x_cortex_a53_plus_2x_cortex_a72;online_reporting_requires_a_repeatable_mainline_test' \
	'generic_arm64_cpu_topology_psci_0_2_and_armv8_arch_timer_are_reuse_candidates' \
	'live_psci_function_ids_are_standard_smccc_0x84000001_through_0x84000004' \
	'vendor_idle_state_suspend_parameters_are_not_reused_without_firmware_semantics' \
	'per_cpu_clock_frequency_is_vendor_metadata_not_a_linux_7_1_3_cpu_binding_property_and_is_omitted_from_the_local_dts' \
	'no_new_cpu_or_timer_driver_is_justified_by_the_observed_identity;mainline_boot_and_hotplug_tests_remain_required'
