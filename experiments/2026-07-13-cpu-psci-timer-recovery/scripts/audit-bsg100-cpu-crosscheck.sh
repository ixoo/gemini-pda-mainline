#!/usr/bin/env bash

set -euo pipefail

readonly REFERENCE="${1:?usage: $0 BSG100_TREE [REPOSITORY_ROOT]}"
readonly REPOSITORY_ROOT="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)}"
readonly FIRST_SMP_LOG="${REFERENCE}/logs/2026-07-04-21-scp-node-boot.log"
readonly CPU1_LOG="${REFERENCE}/logs/2026-07-06-74-psci-cpu1-diag-boot.log"
readonly CPU8_LOG="${REFERENCE}/logs/2026-07-06-83-cpu8-scpsys-retest-boot.log"
readonly EIGHT_CPU_LOG="${REFERENCE}/logs/2026-07-06-78-maxcpus8-boot.log"
readonly BOOT_DOCUMENT="${REFERENCE}/boot.md"
readonly BOARD_PATCH="${REPOSITORY_ROOT}/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"

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

has_strings() {
  strings -a "$2" | rg -- "$1" >/dev/null
}

has_document() {
  rg -q -- "$1" "$2"
}

[[ -d "${REFERENCE}/.git" ]] || {
  echo "error: reference tree is not a Git worktree" >&2
  exit 1
}
for file in "${FIRST_SMP_LOG}" "${CPU1_LOG}" "${CPU8_LOG}" "${EIGHT_CPU_LOG}" "${BOOT_DOCUMENT}"; do
  [[ -f "${file}" ]] || {
    echo "error: expected reference log is missing: ${file}" >&2
    exit 1
  }
done
[[ -f "${BOARD_PATCH}" ]] || {
  echo "error: current Gemini board patch is missing" >&2
  exit 1
}

has_strings 'psci: PSCIv0.2 detected in firmware' "${FIRST_SMP_LOG}" || {
  echo "error: first SMP log has no PSCI marker" >&2
  exit 1
}
has_strings 'smp: Bringing up secondary CPUs' "${FIRST_SMP_LOG}" || {
  echo "error: first SMP log has no secondary-CPU marker" >&2
  exit 1
}
has_strings 'CPU_ON cpu1 returned 0' "${CPU1_LOG}" || {
  echo "error: CPU1 diagnostic log has no successful CPU_ON marker" >&2
  exit 1
}
has_strings 'smp: Brought up 1 node, 2 CPUs' "${CPU1_LOG}" || {
  echo "error: CPU1 diagnostic log has no two-CPU marker" >&2
  exit 1
}
has_strings 'smp: Brought up 1 node, 8 CPUs' "${EIGHT_CPU_LOG}" || {
  echo "error: maxcpus=8 log has no eight-CPU marker" >&2
  exit 1
}
has_strings 'smp: Bringing up secondary CPUs' "${CPU8_LOG}" || {
  echo "error: CPU8 retest log has no secondary-CPU marker" >&2
  exit 1
}
has_document 'CPU_ON.*cpu8.*never returns' "${BOOT_DOCUMENT}" || {
  echo "error: bsg100 boot document has no CPU8 failure statement" >&2
  exit 1
}
has_document 'maxcpus=8' "${BOOT_DOCUMENT}" || {
  echo "error: bsg100 boot document has no maxcpus=8 workaround statement" >&2
  exit 1
}

printf 'validation=bsg100-cpu-psci-crosscheck\n'
printf 'reference_revision=%s\n' "$(git -C "${REFERENCE}" rev-parse HEAD)"
printf 'reference_first_smp_log_sha256=%s\n' "$(hash_file "${FIRST_SMP_LOG}")"
printf 'reference_cpu1_diagnostic_log_sha256=%s\n' "$(hash_file "${CPU1_LOG}")"
printf 'reference_cpu8_retest_log_sha256=%s\n' "$(hash_file "${CPU8_LOG}")"
printf 'reference_maxcpus8_log_sha256=%s\n' "$(hash_file "${EIGHT_CPU_LOG}")"
printf 'reference_boot_document_sha256=%s\n' "$(hash_file "${BOOT_DOCUMENT}")"
printf 'reference_kernel=6.6\n'
printf 'reference_psci=standard_psci_v0.2_smc\n'
printf 'reference_cpu1=CPU_ON_success;two_cpus\n'
printf 'reference_cpu8=secondary_bringup_failure_at_A72_boundary\n'
printf 'reference_workaround=maxcpus=8;A53_cluster_only\n'
printf 'current_kernel=7.1.3\n'
printf 'current_board_cpu_nodes=10_psci_nodes_inherited_from_mt6797_dtsi\n'
printf 'current_maxcpus_token=absent_from_patch_layer\n'
printf 'current_runtime_mainline_boot=not_attempted\n'

printf '\n[decision]\n'
printf '%s\n' \
  'The bsg100 hardware logs show standard PSCI and successful A53 CPU_ON calls through eight CPUs, but a separate A72-cluster CPU8 bring-up failure.' \
  'This is evidence that generic PSCI is the correct transport while full ten-core enablement remains a runtime gate; it does not justify copying a maxcpus=8 workaround into the 7.1.3 patch layer before reproducing the failure.' \
  'The current board intentionally retains all ten generic CPU nodes and no maxcpus token; the first mainline boot must capture exactly where CPU bring-up stops.' \
  'hardware_write=none'
