#!/usr/bin/env bash

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
  drivers/tty/serial/8250
  drivers/pinctrl/mediatek
  drivers/soc/mediatek
  drivers/mfd
  drivers/regulator
  drivers/watchdog
  drivers/mmc/host
)

temporary="$(mktemp -d)"
cleanup() {
  rm -rf "${temporary}"
}
trap cleanup EXIT

overall=pass
printf 'validation=first-boot-static-compile\n'
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
  diagnostic_count="$(grep -Eic '(^|[^[:alpha:]])(warning|error|sparse):' "${log}" || true)"
  printf '%s|status=%s|diagnostics=%s\n' "${target}" "${status}" "${diagnostic_count}"
done

printf '\n[diagnostics]\n'
for target in "${targets[@]}"; do
  log="${temporary}/$(printf '%s' "${target}" | tr '/' '_').log"
  if grep -Eiq '(^|[^[:alpha:]])(warning|error|sparse):' "${log}"; then
    printf '=== %s ===\n' "${target}"
    grep -Ei '(^|[^[:alpha:]])(warning|error|sparse):' "${log}" | sed -n '1,100p'
  fi
done

printf '\nresult=%s\n' "${overall}"
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
[[ "${overall}" == pass ]]
