#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C

readonly PACKAGE="${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel artifact}"
readonly SOURCE_DIR="${GEMINI_SOURCE_DIR:-${HOME}/src/gemini-pda/linux-7.1.3}"
readonly BUILD_DIR="${GEMINI_BUILD_DIR:-${HOME}/build/gemini-pda/linux-7.1.3}"
readonly DTB_DIR="${GEMINI_DTB_DIR:-${PACKAGE}/dtbs/mediatek}"
readonly SCHEMA="${BUILD_DIR}/Documentation/devicetree/bindings/processed-schema.json"

targets=(
	mt6797-evb.dtb
	mt6797-gemini-pda.dtb
	mt6797-x20-dev.dtb
)

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

make -s -C "${SOURCE_DIR}" O="${BUILD_DIR}" ARCH=arm64 dt_binding_schemas
[[ -s "${SCHEMA}" ]] || {
	echo "error: processed schema was not generated: ${SCHEMA}" >&2
	exit 1
}

temporary="$(mktemp -d)"
cleanup() {
	rm -rf "${temporary}"
}
trap cleanup EXIT

overall=pass
printf 'validation=mt6797-dtb-schema-bounded\n'
printf 'package=%s\n' "${PACKAGE}"
printf 'source=%s\n' "${SOURCE_DIR}"
printf 'schema=%s\n' "${SCHEMA}"
printf 'schema_sha256=%s\n' "$(sha256sum "${SCHEMA}" | awk '{print $1}')"
printf 'dt_validate=%s\n' "$(dt-validate --version 2>&1 | head -n 1 || true)"

printf '\n[target_results]\n'
for target in "${targets[@]}"; do
	dtb="${DTB_DIR}/${target}"
	log="${temporary}/${target}.log"
	if [[ ! -f "${dtb}" ]]; then
		printf '%s|status=missing|diagnostics=0\n' "${target}"
		overall=fail
		continue
	fi
	status=pass
	if ! dt-validate -s "${SCHEMA}" -l mediatek,mt6797 "${dtb}" >"${log}" 2>&1; then
		status=fail
		overall=fail
	fi
	diagnostics=0
	if [[ -s "${log}" ]]; then
		diagnostics="$(wc -l <"${log}" | tr -d ' ')"
	fi
	printf '%s|sha256=%s|status=%s|diagnostics=%s\n' \
		"${target}" "$(sha256sum "${dtb}" | awk '{print $1}')" "${status}" "${diagnostics}"
done

printf '\n[diagnostics]\n'
for target in "${targets[@]}"; do
	log="${temporary}/${target}.log"
	if [[ -s "${log}" ]]; then
		printf '=== %s ===\n' "${target}"
		cat "${log}"
	fi
done

printf '\nresult=%s\n' "${overall}"
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
[[ "${overall}" == pass ]]
