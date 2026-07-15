#!/usr/bin/env bash

set -euo pipefail

readonly MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR
readonly GHIDRA_VERSION="12.1.2"
readonly GHIDRA_RELEASE_DATE="20260605"
readonly GHIDRA_SHA256="b62e81a0390618466c019c60d8c2f796ced2509c4c1aea4a37644a77272cf99d"
readonly GHIDRA_ARCHIVE="ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_RELEASE_DATE}.zip"
readonly GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/${GHIDRA_ARCHIVE}"

install_system_packages() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "system provisioning must run as root" >&2
    exit 1
  fi

  local line
  local -a packages=()

  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    packages+=("${line}")
  done < "${SCRIPT_DIR}/apt-packages.txt"

  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends "${packages[@]}"
}

provision_user() {
  if [[ "${EUID}" -eq 0 ]]; then
    echo "user provisioning must not run as root" >&2
    exit 1
  fi

  local venv="${HOME}/.local/share/venvs/dtschema"
  local tool

  mkdir -p \
    "${HOME}/.local/bin" \
    "${HOME}/.local/opt" \
    "${HOME}/.local/share/venvs" \
    "${HOME}/.cache/gemini-pda" \
    "${HOME}/src" \
    "${HOME}/build" \
    "${HOME}/artifacts" \
    "${HOME}/reverse-engineering" \
    "${HOME}/.config/gemini-pda"

  python3 -m venv "${venv}"
  "${venv}/bin/python" -m pip install --disable-pip-version-check --upgrade pip
  "${venv}/bin/python" -m pip install \
    --disable-pip-version-check \
    --upgrade \
    --requirement "${SCRIPT_DIR}/python-requirements.txt"

  for tool in "${venv}"/bin/dt-* "${venv}/bin/vmlinux-to-elf"; do
    [[ -e "${tool}" ]] || continue
    ln -sfn "${tool}" "${HOME}/.local/bin/$(basename "${tool}")"
  done

  ln -sfn /mnt/gemini-pda-mainline "${HOME}/gemini-pda-mainline-host"
  ln -sfn \
    /mnt/gemini-pda-mainline/artifacts/device-userspace/latest \
    "${HOME}/reverse-engineering/gemini-vendor"

  install_ghidra

  ccache --set-config=max_size=20G
  ccache --set-config=compression=true

  "${venv}/bin/python" -m pip freeze \
    > "${HOME}/.config/gemini-pda/python-packages.txt"
  dpkg-query --show --showformat='${binary:Package}\t${Version}\n' \
    > "${HOME}/.config/gemini-pda/debian-packages.txt"
}

install_ghidra() {
  local archive="${HOME}/.cache/gemini-pda/${GHIDRA_ARCHIVE}"
  local install_dir="${HOME}/.local/opt/ghidra_${GHIDRA_VERSION}_PUBLIC"
  local actual_digest=""

  if [[ -r "${archive}" ]]; then
    actual_digest="$(sha256sum "${archive}" | awk '{print $1}')"
  fi

  if [[ "${actual_digest}" != "${GHIDRA_SHA256}" ]]; then
    rm -f "${archive}.partial"
    curl --fail --location --retry 3 --output "${archive}.partial" "${GHIDRA_URL}"
    printf '%s  %s\n' "${GHIDRA_SHA256}" "${archive}.partial" | sha256sum --check --status
    mv "${archive}.partial" "${archive}"
  fi

  if [[ ! -d "${install_dir}" ]]; then
    unzip -q "${archive}" -d "${HOME}/.local/opt"
  fi

  if [[ ! -x "${install_dir}/Ghidra/Features/Decompiler/build/os/linux_arm_64/decompile" ]]; then
    (
      cd "${install_dir}/support/gradle"
      ./gradlew --no-daemon buildNatives
    )
  fi

  ln -sfn "${install_dir}/support/analyzeHeadless" "${HOME}/.local/bin/ghidra-analyze"
  ln -sfn "${install_dir}/ghidraRun" "${HOME}/.local/bin/ghidra"
}

case "${MODE}" in
  system)
    install_system_packages
    ;;
  user)
    provision_user
    ;;
  *)
    echo "usage: $0 system|user" >&2
    exit 2
    ;;
esac
