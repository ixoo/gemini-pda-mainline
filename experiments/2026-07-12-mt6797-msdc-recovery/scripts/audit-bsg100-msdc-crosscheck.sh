#!/usr/bin/env bash

set -euo pipefail

readonly REFERENCE="${1:?usage: $0 BSG100_TREE [REPOSITORY_ROOT]}"
readonly REPOSITORY_ROOT="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)}"
readonly SUCCESS_LOG="${REFERENCE}/logs/2026-07-05-35-msdc0-mt2701-compat-boot.log"
readonly IRQ_LOG="${REFERENCE}/logs/2026-07-05-31-msdc0-irq-levellow-boot.log"
readonly COMPAT_PATCH="${REPOSITORY_ROOT}/patches/v7.1.3/0017-mmc-mtk-sd-add-MT6797-support.patch"
readonly SOC_PATCH="${REPOSITORY_ROOT}/patches/v7.1.3/0018-arm64-dts-mediatek-mt6797-add-MSDC-controllers.patch"
readonly BOARD_PATCH="${REPOSITORY_ROOT}/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"
readonly PINCTRL_PATCH="${REPOSITORY_ROOT}/patches/v7.1.3/0071-arm64-dts-mediatek-gemini-use-pinmux-only-for-MT6797-MSDC.patch"

for command in git rg strings; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

has() {
  rg -q -- "$1" "$2"
}

has_strings() {
  strings -a "$2" | rg -- "$1" >/dev/null
}

[[ -d "${REFERENCE}/.git" && -f "${SUCCESS_LOG}" && -f "${IRQ_LOG}" ]] || {
  echo "error: reference tree or expected tracked logs are missing" >&2
  exit 1
}
for file in "${COMPAT_PATCH}" "${SOC_PATCH}" "${BOARD_PATCH}" "${PINCTRL_PATCH}"; do
  [[ -f "${file}" ]] || {
    echo "error: current repository patch is missing: ${file}" >&2
    exit 1
  }
done

has_strings 'mmc0: new high speed MMC card' "${SUCCESS_LOG}" || {
  echo "error: reference success log has no eMMC enumeration marker" >&2
  exit 1
}
has_strings 'mmcblk0: p1 .* p33' "${SUCCESS_LOG}" || {
  echo "error: reference success log has no complete partition marker" >&2
  exit 1
}
has_strings 'msdc_init_hw done' "${SUCCESS_LOG}" || {
  echo "error: reference success log has no controller-init marker" >&2
  exit 1
}
has_strings 'msdc_init_hw done' "${IRQ_LOG}" || {
  echo "error: reference IRQ-polarity log has no controller-init marker" >&2
  exit 1
}

has 'mt6797_compat' "${COMPAT_PATCH}" || {
  echo "error: current tree has no dedicated MT6797 compatibility record" >&2
  exit 1
}
for marker in \
  '.clk_div_bits = 12' \
  '.pad_tune_reg = MSDC_PAD_TUNE0' \
  '.async_fifo = true' \
  '.data_tune = true' \
  '.busy_check = false' \
  '.stop_clk_fix = false' \
  '.enhance_rx = false' \
  '.support_64g = false'; do
  has "${marker}" "${COMPAT_PATCH}" || {
    echo "error: current MT6797 compatibility field missing: ${marker}" >&2
    exit 1
  }
done
has 'compatible = "mediatek,mt6797-mmc"' "${SOC_PATCH}" || {
  echo "error: current SoC node does not use the MT6797 identity" >&2
  exit 1
}
has 'interrupts = <GIC_SPI 79 IRQ_TYPE_LEVEL_LOW>' "${SOC_PATCH}" || {
  echo "error: current MSDC0 interrupt polarity is not level-low" >&2
  exit 1
}
for marker in \
  'max-frequency = <25000000>' \
  'vmmc-supply = <&mt6351_vemc_reg>' \
  'vqmmc-supply = <&mt6351_vio18_reg>' \
  'non-removable' \
  'bus-width = <8>'; do
  has "${marker}" "${BOARD_PATCH}" || {
    echo "error: current Gemini eMMC boundary missing: ${marker}" >&2
    exit 1
  }
done
if rg -q '^\+[^+].*(drive-strength =|bias-pull-)' "${PINCTRL_PATCH}"; then
  echo "error: current pinmux-only patch still carries unsupported pinconf" >&2
  exit 1
fi

printf 'validation=bsg100-msdc-crosscheck\n'
printf 'reference_revision=%s\n' "$(git -C "${REFERENCE}" rev-parse HEAD)"
printf 'reference_success_log_sha256=%s\n' "$(hash_file "${SUCCESS_LOG}")"
printf 'reference_irq_polarity_log_sha256=%s\n' "$(hash_file "${IRQ_LOG}")"
printf 'reference_kernel=6.6\n'
printf 'reference_runtime=hardware_boot_confirmed\n'
printf 'reference_compat=mediatek,mt2701-mmc\n'
printf 'reference_irq=MSDC0_SPI79_level_low\n'
printf 'reference_eMMC=DF4064_high_speed_partitions_p1_to_p33\n'
printf 'current_kernel=7.1.3\n'
printf 'current_compat=mediatek,mt6797-mmc\n'
printf 'current_register_profile=MT2701_generation_equivalent;recheck_sdio_irq_false\n'
printf 'current_irq=MSDC0_SPI79_level_low\n'
printf 'current_eMMC_boundary=8bit_nonremovable_25MHz_vmmc_vqmmc\n'
printf 'current_pad_boundary=pinmux_only;firmware_pad_state_retained\n'
printf 'current_runtime_mainline_boot=not_attempted\n'

printf '\n[decision]\n'
printf '%s\n' \
  'The independently tracked bsg100 hardware boot validates the level-low MSDC0 IRQ, explicit rail contract, and pinmux-only boundary on this hardware family.' \
  'Its mt2701 compatible is evidence about register generation, not a requirement to discard the more specific MT6797 compatible in the 7.1.3 tree.' \
  'The local MT6797 record deliberately preserves the same register profile while keeping the SoC identity and disabling SDIO-only recheck behavior.' \
  'The cross-check strengthens the first-boot design but does not prove that the current 7.1.3 package has booted.' \
  'hardware_write=none'
