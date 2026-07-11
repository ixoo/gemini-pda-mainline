#!/usr/bin/env bash

set -euo pipefail

readonly MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR

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
    "${HOME}/.local/share/venvs" \
    "${HOME}/src" \
    "${HOME}/build" \
    "${HOME}/artifacts" \
    "${HOME}/.config/gemini-pda"

  python3 -m venv "${venv}"
  "${venv}/bin/python" -m pip install --disable-pip-version-check --upgrade pip
  "${venv}/bin/python" -m pip install \
    --disable-pip-version-check \
    --upgrade \
    --requirement "${SCRIPT_DIR}/python-requirements.txt"

  for tool in "${venv}"/bin/dt-*; do
    [[ -e "${tool}" ]] || continue
    ln -sfn "${tool}" "${HOME}/.local/bin/$(basename "${tool}")"
  done

  ln -sfn /mnt/gemini-pda-mainline "${HOME}/gemini-pda-mainline-host"

  ccache --set-config=max_size=20G
  ccache --set-config=compression=true

  "${venv}/bin/python" -m pip freeze \
    > "${HOME}/.config/gemini-pda/python-packages.txt"
  dpkg-query --show --showformat='${binary:Package}\t${Version}\n' \
    > "${HOME}/.config/gemini-pda/debian-packages.txt"
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
