#!/usr/bin/env bash

# Compile every kernel subsystem directory touched by a C source in the
# current patch series with warnings and sparse enabled. This is source review
# evidence only; it does not load modules or touch hardware.

set -euo pipefail

readonly SOURCE_DIR="${GEMINI_SOURCE_DIR:-${HOME}/src/gemini-pda/linux-7.1.3}"
readonly BUILD_DIR="${GEMINI_BUILD_DIR:-${HOME}/build/gemini-pda/linux-7.1.3}"

[[ -d "${SOURCE_DIR}" ]] || {
	echo "error: source tree not found: ${SOURCE_DIR}" >&2
	exit 1
}
[[ -f "${BUILD_DIR}/.config" ]] || {
	echo "error: configured build tree not found: ${BUILD_DIR}" >&2
	exit 1
}

targets=(
	drivers/clk/mediatek
	drivers/gpu/drm/mediatek
	drivers/gpu/drm/panel
	drivers/gpu/drm/panfrost
	drivers/iio/adc
	drivers/input/keyboard
	drivers/iommu
	drivers/mfd
	drivers/mmc/host
	drivers/nvmem
	drivers/phy/mediatek
	drivers/pinctrl/mediatek
	drivers/pmdomain/mediatek
	drivers/pwm
	drivers/regulator
	drivers/rtc
	drivers/spi
	drivers/soc/mediatek
	drivers/thermal/mediatek
	drivers/usb/host
	drivers/usb/mtu3
	drivers/usb/musb
	drivers/usb/typec
)

temporary=$(mktemp -d)
cleanup() { rm -rf "${temporary}"; }
trap cleanup EXIT

overall=pass
printf 'validation=series-static-compile\n'
printf 'source=%s\n' "${SOURCE_DIR}"
printf 'build=%s\n' "${BUILD_DIR}"
printf 'compiler=%s\n' "$(gcc --version | head -n 1)"
printf 'sparse=%s\n' "$(command -v sparse)"
printf 'warnings=enabled\n'
printf 'sparse_check=enabled\n'
printf '\n[target_results]\n'

for target in "${targets[@]}"; do
	log="${temporary}/$(printf '%s' "${target}" | tr '/' '_').log"
	status=pass
	if ! make -s -C "${SOURCE_DIR}" O="${BUILD_DIR}" ARCH=arm64 \
		W=1 C=1 M="${target}" >"${log}" 2>&1; then
		status=fail
		overall=fail
	fi
	diagnostic_count=$(grep -Eic '(^|[^[:alpha:]])(warning|error|sparse):' "${log}" || true)
	if (( diagnostic_count )); then
		overall=fail
	fi
	printf '%s|status=%s|diagnostics=%s\n' "${target}" "${status}" "${diagnostic_count}"
done

printf '\n[diagnostics]\n'
for target in "${targets[@]}"; do
	log="${temporary}/$(printf '%s' "${target}" | tr '/' '_').log"
	if grep -Eiq '(^|[^[:alpha:]])(warning|error|sparse):' "${log}"; then
		printf '=== %s ===\n' "${target}"
		grep -Ei '(^|[^[:alpha:]])(warning|error|sparse):' "${log}" | sed -n '1,120p'
	fi
done

printf '\nresult=%s\n' "${overall}"
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
[[ "${overall}" == pass ]]
