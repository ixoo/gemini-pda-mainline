#!/usr/bin/env bash

set -euo pipefail

readonly PACKAGE="${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel artifact}"
readonly SOURCE_DIR="${GEMINI_SOURCE_DIR:-${HOME}/src/gemini-pda/linux-7.1.3}"
readonly BUILD_DIR="${GEMINI_BUILD_DIR:-${HOME}/build/gemini-pda/linux-7.1.3}"
readonly DTB="${GEMINI_DTB:-${PACKAGE}/dtbs/mediatek/mt6797-gemini-pda.dtb}"
readonly SCHEMA="${BUILD_DIR}/Documentation/devicetree/bindings/processed-schema.json"

for command in dt-validate make sha256sum; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "error: required command not found: ${command}" >&2
    exit 1
  }
done

[[ -d "${SOURCE_DIR}" ]] || {
  echo "error: Linux source tree not found: ${SOURCE_DIR}" >&2
  exit 1
}
[[ -f "${DTB}" ]] || {
  echo "error: Gemini DTB not found: ${DTB}" >&2
  exit 1
}

# Generate only the merged schema. The Linux 7.1.x build system exposes this
# through the dt_binding_schemas phony target; invoking the generated JSON path
# directly is not portable because the top-level Makefile conditionally
# includes the bindings sub-make only for its phony targets. Do not invoke the
# broad dtbs_check target, which rebuilds every arm64 board in the tree.
make -s -C "${SOURCE_DIR}" O="${BUILD_DIR}" ARCH=arm64 \
  dt_binding_schemas
[[ -s "${SCHEMA}" ]] || {
  echo "error: processed schema was not generated: ${SCHEMA}" >&2
  exit 1
}

temporary="$(mktemp)"
cleanup() {
  rm -f "${temporary}"
}
trap cleanup EXIT

if ! dt-validate -s "${SCHEMA}" -l mediatek,gemini-pda "${DTB}" \
  >"${temporary}" 2>&1; then
  cat "${temporary}"
  exit 1
fi

printf 'validation=gemini-dtb-schema\n'
printf 'package=%s\n' "${PACKAGE}"
printf 'dtb=%s\n' "${DTB}"
printf 'dtb_sha256=%s\n' "$(sha256sum "${DTB}" | awk '{print $1}')"
printf 'schema=%s\n' "${SCHEMA}"
printf 'schema_sha256=%s\n' "$(sha256sum "${SCHEMA}" | awk '{print $1}')"
printf 'dt_validate=%s\n' "$(dt-validate --version 2>&1 | head -n 1 || true)"
if [[ -s "${temporary}" ]]; then
  printf 'validator_output<<EOF\n'
  cat "${temporary}"
  printf 'EOF\n'
else
  printf 'validator_output=empty\n'
fi
printf 'result=pass\n'
