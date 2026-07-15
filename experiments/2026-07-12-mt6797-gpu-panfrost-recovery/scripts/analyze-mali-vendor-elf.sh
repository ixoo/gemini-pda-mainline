#!/usr/bin/env bash

# Recover the vendor Mali/Kbase and MT6797 platform contract without running
# the vendor driver or copying its proprietary ABI. The ELF and source tree
# are immutable evidence in the development VM.

set -eu
export LC_ALL=C

VMLINUX=${VMLINUX:-/home/julien.guest/reverse-engineering/work/gemini-kernel/vmlinux.elf}
VENDOR_TREE=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
LINUX_TREE=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}

[[ -r "$VMLINUX" ]] || { printf 'missing vendor ELF: %s\n' "$VMLINUX" >&2; exit 1; }
[[ -d "$VENDOR_TREE/.git" ]] || { printf 'missing vendor tree: %s\n' "$VENDOR_TREE" >&2; exit 1; }
[[ -d "$LINUX_TREE" ]] || { printf 'missing Linux tree: %s\n' "$LINUX_TREE" >&2; exit 1; }

printf 'vmlinux=%s\n' "$VMLINUX"
printf 'vmlinux_sha256=%s\n' "$(sha256sum "$VMLINUX" | awk '{print $1}')"
printf 'vendor_tree=%s\n' "$VENDOR_TREE"
printf 'vendor_commit=%s\n' "$(git -C "$VENDOR_TREE" rev-parse HEAD)"
printf 'linux_tree=%s\n' "$LINUX_TREE"
linux_commit=$(git -C "$LINUX_TREE" rev-parse --verify HEAD 2>/dev/null | head -n 1 || true)
printf 'linux_commit=%s\n' "${linux_commit:-unknown}"

printf '\n[vendor source hashes]\n'
for file in \
	arch/arm64/boot/dts/mt6797.dtsi \
	drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c \
	include/uapi/linux/autoconf.h \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p0/drivers/gpu/arm/midgard/platform/devicetree/mali_kbase_config_devicetree.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p0/drivers/gpu/arm/midgard/platform/devicetree/mali_kbase_runtime_pm.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p0/drivers/gpu/arm/midgard/mali_kbase_device.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_kbase_spm.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_kbase_spm.h \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_kbase_spm_fw.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_kbase_spm_hal.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mtk_platform_common/mtk_platform_common.c \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/mali_kbase_core_linux.c; do
	if git -C "$VENDOR_TREE" cat-file blob "HEAD:$file" >/tmp/gemini-gpu-hash 2>/dev/null; then
		printf '%s ' "$file"
		sha256sum /tmp/gemini-gpu-hash | awk '{print $1}'
	else
		printf '%s missing\n' "$file"
	fi
done

printf '\n[vendor build identity]\n'
git -C "$VENDOR_TREE" show HEAD:include/uapi/linux/autoconf.h |
	rg -n 'CONFIG_MTK_GPU_VERSION|CONFIG_MTK_GPU_SUPPORT' || true
printf 'captured_spm_dvfs_config='
if git -C "$VENDOR_TREE" show HEAD:include/uapi/linux/autoconf.h |
	rg -q 'CONFIG_MTK_GPU_SPM_DVFS_SUPPORT'; then
	git -C "$VENDOR_TREE" show HEAD:include/uapi/linux/autoconf.h |
		rg 'CONFIG_MTK_GPU_SPM_DVFS_SUPPORT' || true
else
	printf 'absent_or_disabled\n'
fi
git -C "$VENDOR_TREE" show HEAD:drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/Kbuild |
	rg -n 'MTK_GPU_SPM|MTK_GPU_APM|MTK_GPU_DPM|MTK_GPU_OCP' || true
printf 'generic_midgard_r12p0_tree='
if git -C "$VENDOR_TREE" ls-tree -r --name-only HEAD |
	rg -q 'mali_midgard/mali-r12p0/drivers/gpu/arm/midgard/mali_kbase_device.c'; then
	printf 'present\n'
else
	printf 'absent\n'
fi
printf 'configured_midgard_r12p1_tree='
if git -C "$VENDOR_TREE" ls-tree -r --name-only HEAD |
	rg -q 'mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/mali_kbase_device.c'; then
	printf 'present\n'
else
	printf 'absent\n'
fi
printf 'mt6797_kbase_platform_tree='
if git -C "$VENDOR_TREE" ls-tree -r --name-only HEAD |
	rg -q 'mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c'; then
	printf 'present\n'
else
	printf 'absent\n'
fi
printf 'exact_mtk_kbase_text_matches=\n'
if git -C "$VENDOR_TREE" grep -n -i -E \
	'mtk_(platform|kbase|gpu_pmu|gpufreq)|mt_gpufreq|mtcmos-mfg|MFG_BG3D' HEAD -- \
	drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797 \
	2>/dev/null; then
	:
else
	printf '%s\n' '(none in the Mali source subtree)'
fi

printf '\n[MT6797 source callbacks]\n'
git -C "$VENDOR_TREE" show HEAD:drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c |
	rg -n -C 2 'mtk_platform_init|_mtk_of_ioremap|mtk_pm_callback_power_on|mtk_pm_callback_power_off|mtk_debug_mfg_reset|kbase_platform_early_init|devm_clk_get|mtk_kbase_spm' |
	head -n 260 || true

printf '\n[vendor DT and DVFS contract]\n'
git -C "$VENDOR_TREE" show HEAD:arch/arm64/boot/dts/mt6797.dtsi |
	rg -n -C 8 'mali@13040000|gpufreq|clock-names = "mfg-main"|mtcmos-mfg-core' |
	head -n 180 || true
git -C "$VENDOR_TREE" show HEAD:arch/arm64/boot/dts/mt6797.dtsi |
	rg -n -C 4 'compatible = "mediatek,mt6797-gpufreq"|"clk_mux"|"clk_main_parent"|"clk_sub_parent"' || true
git -C "$VENDOR_TREE" show HEAD:drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c |
	rg -n -C 3 'VGPU_SET_BY_EXTIC|GPU_LDO_BASE|EXTIC_VSEL|RT5735|VSEL' |
	head -n 180 || true

printf '\n[ELF symbols]\n'
nm -an "$VMLINUX" |
	rg -i ' (kbase_platform_device_probe|kbase_platform_early_init|kbase_get_platform_config|mtk_platform_init|mtk_debug_mfg_reset|mtk_get_gpu_pmu|pm_callback_power_on|pm_callback_power_off|mt_gpufreq_pdrv_probe)' || true

printf '\n[ELF platform strings]\n'
strings -tx "$VMLINUX" |
	rg -i 'mediatek,(infracfg_ao|topckgen|g3d_config|g3d_dfp_config|dvfs_proc2)|mtcmos-mfg|mfg-main|mfg52m|mux-univpll2-d8|clk_(mux|main_parent|sub_parent)' || true

printf '\n[ELF platform init and early probe]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc0006144a8 \
	--stop-address=0xffffffc0006148d0 "$VMLINUX" |
	rg -e '^ffffffc000614(4a8|4b8|538)' -e '_mtk_of_ioremap' -e 'devm_clk_get' \
		-e 'mt_gpufreq_get_freq_by_idx' -e 'clk_prepare' -e 'clk_set_parent' \
		-e 'mtk_wdt_swsysret_config' -e 'spm_topaxi_protect' -e '#0x(47e|352|4|10c7|a00000)' || true

printf '\n[ELF power and reset callbacks]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc0006139f8 \
	--stop-address=0xffffffc000614538 "$VMLINUX" |
	rg -e '^ffffffc000613(9f8|a28|cc8|f48|fa8)' -e 'mt_gpufreq_voltage_enable_set' \
		-e 'clk_prepare' -e 'clk_enable' -e 'clk_disable' -e 'clk_unprepare' \
		-e 'spm_topaxi_protect' -e 'ged_dvfs_gpu_clock_switch_notify' \
		-e 'mtk_set_vgpu_power_on_flag' -e 'str.*\[x[0-9]+, #[0-9]+' -e '#0x(1ff|8dbc|a00000|10c7)' || true
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc000614468 \
	--stop-address=0xffffffc0006144a8 "$VMLINUX" |
	rg -e 'mtk_debug_mfg_reset' -e 'str.*\[x[0-9]+, #0xc\]' -e '__const_udelay' -e '#0x(3|10c7)' || true

printf '\n[mainline comparison]\n'
sha256sum \
	"$LINUX_TREE/drivers/gpu/drm/panfrost/panfrost_device.c" \
	"$LINUX_TREE/drivers/gpu/drm/panfrost/panfrost_gpu.c" \
	"$LINUX_TREE/drivers/gpu/drm/panfrost/panfrost_drv.c" \
	"$LINUX_TREE/Documentation/devicetree/bindings/gpu/arm,mali-midgard.yaml"
rg -n -C 3 'GPU_MODEL\(t880|0x880|arm,mali-t860|arm,mali-t880|devm_clk_get|mali-supply|power-domains|resets|operating-points-v2' \
	"$LINUX_TREE/drivers/gpu/drm/panfrost/panfrost_gpu.c" \
	"$LINUX_TREE/drivers/gpu/drm/panfrost/panfrost_drv.c" \
	"$LINUX_TREE/Documentation/devicetree/bindings/gpu/arm,mali-midgard.yaml" |
	head -n 260 || true

printf '\n[decision]\n'
printf '%s\n' \
	'live_product_id_0x0880_matches_mainline_panfrost_t880_model' \
	'vendor_tree_contains_generic_arm_midgard_r12p0_and_configured_r12p1_sources' \
	'exact_mt6797_kbase_platform_source_is_present_in_pinned_git_and_correlates_with_vendor_elf' \
	'vendor_mtk_platform_maps_five_compatible_nodes_and_requests_ten_clocks' \
	'captured_build_omits_mtk_gpu_spm_dvfs_support_and_elf_does_not_request_optional_gpupm_or_ap_dma_clocks' \
	'r12p1_source_contains_optional_spm_dvfs_pcm_path_but_optional_feature_is_not_proven_enabled_on_live_build' \
	'vendor_power_on_enables_vgpu_then_prepares_mfg_async_mfg_core0_core1_core2_core3_mfg_main_and_mfg52m_vcg' \
	'vendor_mfg_reset_writes_g3d_config_offset_0xc_high_then_low_with_source_udelay_1us' \
	'vendor_early_init_defers_until_external_vgpu_controller_is_ready_when_eem_is_active' \
	'linux_panfrost_binding_supports_one_or_two_clocks_optional_mali_supply_single_power_domain_optional_resets_and_opp' \
	'reuse_panfrost_core_model; add_a_new_mt6797_platform_integration_or_backend_if_the_recovered_contract_cannot_fit_generic_resources' \
	'if_future_runtime_gpu_id_does_not_match_a_supported_midgard_model_use_a_new_gpu_driver_boundary' \
	'keep_gemini_gpu_disabled_until_reset_power_domain_regulator_and_fixed_opp_tests_are_reproducible'
