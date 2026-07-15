#!/usr/bin/env bash

set -euo pipefail

readonly REPO_ROOT="${REPO_ROOT:-/mnt/gemini-pda-mainline}"
readonly SOURCE_DIR="${GEMINI_SOURCE_DIR:-${HOME}/src/gemini-pda/linux-7.1.3}"
readonly CHECKPATCH="${SOURCE_DIR}/scripts/checkpatch.pl"
readonly SERIES="${REPO_ROOT}/patches/series"

[[ -x "${CHECKPATCH}" ]] || {
  echo "error: checkpatch.pl not found: ${CHECKPATCH}" >&2
  exit 1
}
[[ -r "${SERIES}" ]] || {
  echo "error: patch series not found: ${SERIES}" >&2
  exit 1
}

temporary="$(mktemp)"
cleanup() {
  rm -f "${temporary}"
}
trap cleanup EXIT

patch_count=0
nonzero_count=0
while IFS= read -r relative || [[ -n "${relative}" ]]; do
  case "${relative}" in
    ''|'#'*) continue ;;
  esac
  patch_count=$((patch_count + 1))
  patch="${REPO_ROOT}/patches/${relative}"
  [[ -f "${patch}" ]] || {
    echo "error: missing patch: ${patch}" >&2
    exit 1
  }
  printf '\n=== %s ===\n' "${relative}" >>"${temporary}"
  if ! perl "${CHECKPATCH}" --no-tree --strict --terse --show-types \
    "${patch}" >>"${temporary}" 2>&1; then
    nonzero_count=$((nonzero_count + 1))
  fi
done <"${SERIES}"

error_count="$(grep -Ec '(^|: )ERROR:' "${temporary}" || true)"
warning_count="$(grep -Ec '(^|: )WARNING:' "${temporary}" || true)"
check_count="$(grep -Ec '(^|: )CHECK:' "${temporary}" || true)"

printf 'validation=checkpatch-series\n'
printf 'checkpatch=%s\n' "${CHECKPATCH}"
printf 'patch_count=%s\n' "${patch_count}"
printf 'checkpatch_nonzero=%s\n' "${nonzero_count}"
printf 'errors=%s\n' "${error_count}"
printf 'warnings=%s\n' "${warning_count}"
printf 'checks=%s\n' "${check_count}"
printf '\ndiagnostics_by_patch:\n'
grep -E '^(===|[^=]+:[0-9]+: (ERROR|WARNING|CHECK):)' "${temporary}" \
  | sed -n '1,240p'
printf '\nfirst_diagnostics:\n'
grep -E '^[^=]+:[0-9]+: (ERROR|WARNING|CHECK):' "${temporary}" \
  | sed -n '1,160p'
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
