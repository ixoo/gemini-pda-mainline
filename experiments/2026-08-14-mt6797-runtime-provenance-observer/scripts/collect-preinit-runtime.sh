#!/usr/bin/env bash

# Wait for the exact Gemini RNDIS interface and capture the read-only observer
# fast path. Retained pstore is collected independently after the reset cycle.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323
readonly WAIT_SECONDS=240
readonly PROBE_SHA256=dedf74e5fd3a2c48dbba9155b39adbc6a1bf373842b5c8d23a0b1bad0a989dec
readonly VALIDATOR_SHA256=dcce5ea4d0eca7ad87474d673453463c1cadc298498c6915b5fb3b288510de90
readonly CANDIDATE_SHA256=99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
  printf 'usage: %s --output artifacts/runtime-captures/provenance-preinit-attempt-N/runtime.txt\n' "$0" >&2
}

output=
while (($#)); do
  case "$1" in
  --output)
    (($# >= 2)) || die '--output requires a value'
    [[ -z "${output}" ]] || die 'duplicate --output'
    output=$2
    shift 2
    ;;
  -h|--help) usage; exit 0 ;;
  *) usage; die "unknown option: $1" ;;
  esac
done
[[ -n "${output}" ]] || { usage; exit 2; }

for command in awk base64 basename chmod dirname git grep ifconfig mkdir mktemp \
  nc python3 rm route sha256sum sleep tr; do
  command -v "${command}" >/dev/null 2>&1 ||
    die "required host command missing: ${command}"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
probe="${script_dir}/remote-preinit-runtime-probe.sh"
validator="${script_dir}/validate-preinit-runtime.py"
for input in "${probe}" "${validator}"; do
  [[ -f "${input}" && ! -L "${input}" && -s "${input}" ]] ||
    die "runtime input is missing or unsafe: ${input}"
done
[[ "$(sha256sum "${probe}" | awk '{print $1}')" == "${PROBE_SHA256}" ]] ||
  die 'pre-init runtime probe identity changed'
[[ "$(sha256sum "${validator}" | awk '{print $1}')" == "${VALIDATOR_SHA256}" ]] ||
  die 'pre-init runtime validator identity changed'

private_root="${repo_root}/artifacts/runtime-captures"
[[ -d "${private_root}" && ! -L "${private_root}" ]] ||
  die 'private runtime-capture root is absent or unsafe'
private_root="$(cd -- "${private_root}" && pwd -P)"
case "${output}" in /*) ;; *) output="${repo_root}/${output#./}" ;; esac
capture_dir="$(dirname -- "${output}")"
[[ "$(dirname -- "${capture_dir}")" == "${private_root}" &&
   "$(basename -- "${capture_dir}")" == provenance-preinit-attempt-* &&
   "$(basename -- "${output}")" == runtime.txt ]] ||
  die 'output must be runtime.txt in one new provenance-preinit-attempt-* private child'
[[ ! -e "${capture_dir}" && ! -L "${capture_dir}" ]] ||
  die 'capture directory already exists'
git -C "${repo_root}" check-ignore -q "${capture_dir}" ||
  die 'capture directory is not ignored by Git'
mkdir -m 0700 "${capture_dir}"
output="${capture_dir}/runtime.txt"

command_file="$(mktemp "${TMPDIR:-/tmp}/.provenance-preinit-runtime.XXXXXXXX")"
# The trap invokes this helper indirectly.
# shellcheck disable=SC2329
cleanup() { [[ ! -e "${command_file:-}" ]] || rm -f -- "${command_file}"; }
trap cleanup EXIT HUP INT TERM
payload="$(base64 <"${probe}" | tr -d '\n')"
[[ "${payload}" =~ ^[A-Za-z0-9+/]+=*$ ]] || die 'probe base64 encoding is malformed'
printf "printf '%%s' '%s' | /bin/busybox base64 -d | /bin/busybox sh\n" \
  "${payload}" >"${command_file}"
chmod 0600 "${command_file}"

interface=
mac=
for ((attempt = 0; attempt < WAIT_SECONDS; attempt++)); do
  # ifconfig -l emits a space-separated interface inventory on the host.
  # shellcheck disable=SC2046
  for candidate in $(ifconfig -l); do
    candidate_mac="$(ifconfig "${candidate}" 2>/dev/null |
      awk '/^[[:space:]]*ether / {print tolower($2); count++} END {exit count != 1}')" || true
    case "${candidate_mac}" in
    42:00:15:19:82:00|42:00:15:19:84:00) ;;
    *) continue ;;
    esac
    if ! ifconfig "${candidate}" | awk -v address="${HOST_ADDRESS}" \
      '$1 == "inet" && $2 == address {found++} END {exit found != 1}'; then
      continue
    fi
    route_interface="$(route -n get "${DEVICE_ADDRESS}" 2>/dev/null |
      awk '$1 == "interface:" {print $2; count++} END {exit count != 1}')" || true
    [[ "${route_interface}" == "${candidate}" ]] || continue
    interface=${candidate}
    mac=${candidate_mac}
    break 2
  done
  sleep 1
done
[[ -n "${interface}" ]] ||
  die "exact Gemini USB interface did not become ready within ${WAIT_SECONDS} seconds"

{
  printf '__GEMINI_PROVENANCE_HOST_BEGIN__\n'
  printf 'interface=%s\nmac=%s\nhost_address=%s/24\n' \
    "${interface}" "${mac}" "${HOST_ADDRESS}"
  printf 'device_endpoint=%s:%s\nroute_interface=%s\n' \
    "${DEVICE_ADDRESS}" "${DEVICE_PORT}" "${interface}"
  printf 'installed_full_sha256=%s\n' "${CANDIDATE_SHA256}"
  printf 'device_partition_reads=none\ndevice_storage_writes=none\n'
  printf 'runtime_probe_transport=stdin-pipe-no-device-file\nreboot_request=none\n'
  printf '__GEMINI_PROVENANCE_HOST_END__\n'
} >"${output}"
chmod 0600 "${output}"

set +e
nc -4 -b "${interface}" -s "${HOST_ADDRESS}" -G 5 -w 45 \
  "${DEVICE_ADDRESS}" "${DEVICE_PORT}" <"${command_file}" >>"${output}" 2>&1
nc_status=$?
set -e
printf 'nc_exit_status=%s\n' "${nc_status}" >>"${output}"

set +e
classification="$(python3 "${validator}" "${output}")"
classification_status=$?
set -e
printf '%s\n' "${classification}" |
  grep -E '^(runtime_classification|runtime_reason|cpu8_cpu9_admission|claim_scope)=' \
  >"${capture_dir}/classification.txt" || die 'validator output is malformed'
chmod 0600 "${capture_dir}/classification.txt"
(
  cd "${capture_dir}"
  sha256sum runtime.txt classification.txt >SHA256SUMS
)
chmod 0600 "${capture_dir}/SHA256SUMS"

printf '%s\n' "${classification}"
printf 'capture=%s\nnc_exit_status=%s\n' "${output}" "${nc_status}"
exit "${classification_status}"
