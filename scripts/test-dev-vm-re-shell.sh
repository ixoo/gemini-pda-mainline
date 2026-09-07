#!/usr/bin/env bash
# shellcheck disable=SC2016

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="${SCRIPT_DIR}/dev-vm"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/dev-vm-re-shell.XXXXXX")"
trap 'rm -rf "${TEST_ROOT}"' EXIT

BIN="${TEST_ROOT}/bin"
PROBE_TMP="${TEST_ROOT}/probe-tmp"
CALL_LOG="${TEST_ROOT}/calls.log"
OUT="${TEST_ROOT}/stdout"
ERR="${TEST_ROOT}/stderr"
INPUT="${TEST_ROOT}/input"
GUEST_HOME="${TEST_ROOT}/guest-home"
mkdir -p "${BIN}" "${PROBE_TMP}" "${GUEST_HOME}/reverse-engineering/gemini-vendor"
: >"${CALL_LOG}"

cat >"${BIN}/limactl" <<'EOF'
#!/usr/bin/env bash

set -euo pipefail

printf 'CALL\n' >>"${STUB_CALL_LOG}"
printf '<%s>\n' "$@" >>"${STUB_CALL_LOG}"

case "${1:-}" in
  --version)
    if [[ "${STUB_VERSION_SIGNAL:-0}" == 1 ]]; then
      kill -TERM "$$"
    fi
    if [[ "${STUB_VERSION_BIG:-0}" == 1 ]]; then
      for _ in $(seq 1 70000); do printf x; done
      printf '\n'
    else
      printf '%s\n' "${STUB_VERSION:-limactl version 2.2.0}"
    fi
    ;;
  list)
    printf '%s\n' "${STUB_INSTANCE:-gemini-pda-dev}"
    ;;
  start)
    ;;
  shell)
    if [[ "${2:-}" == "--help" ]]; then
      if [[ "${STUB_HELP_BIG:-0}" == 1 ]]; then
        for _ in $(seq 1 70000); do printf x; done
        printf '\n'
      else
        printf '%s\n' "${STUB_HELP:-global --tty option: Set to false for automation}"
      fi
      exit 0
    fi
    if [[ "${STUB_RUN_GUEST:-0}" != 1 ]]; then
      exit "${STUB_SHELL_STATUS:-0}"
    fi
    guest_start=0
    for ((index=1; index<$#; index++)); do
      if [[ "${!index}" == "--" ]]; then
        guest_start=$((index + 1))
        break
      fi
    done
    [[ "${guest_start}" -gt 0 ]] || exit 90
    guest=("${@:guest_start}")
    [[ "${guest[0]:-}" == /bin/sh && "${guest[1]:-}" == -c && "${guest[3]:-}" == re-shell ]] || exit 92
    guest_home="${STUB_GUEST_HOME_OVERRIDE-${STUB_GUEST_HOME}}"
    HOME="${guest_home}" /bin/sh -c "${guest[2]}" "${guest[3]}" "${guest[@]:4}"
    ;;
  *)
    exit 91
    ;;
esac
EOF
chmod +x "${BIN}/limactl"

export PATH="${BIN}:${PATH}"
export STUB_CALL_LOG="${CALL_LOG}"
export STUB_GUEST_HOME="${GUEST_HOME}"
export STUB_INSTANCE="gemini-pda-dev"

run_script() {
  export TMPDIR="${PROBE_TMP}"
  export STUB_VERSION STUB_VERSION_BIG STUB_VERSION_SIGNAL STUB_HELP STUB_HELP_BIG STUB_RUN_GUEST STUB_SHELL_STATUS STUB_GUEST_HOME_OVERRIDE
  set +e
  "${SCRIPT}" re-shell "$@" >"${OUT}" 2>"${ERR}"
  STATUS=$?
  set -e
}

reset_case() {
  : >"${CALL_LOG}"
  : >"${OUT}"
  : >"${ERR}"
  unset STUB_VERSION STUB_VERSION_BIG STUB_VERSION_SIGNAL STUB_HELP STUB_HELP_BIG STUB_RUN_GUEST STUB_SHELL_STATUS STUB_GUEST_HOME_OVERRIDE
}

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_status() {
  [[ "${STATUS}" -eq "$1" ]] || fail "expected status $1, got ${STATUS}"
}

assert_failure() {
  [[ "${STATUS}" -ne 0 ]] || fail "expected failure status, got zero"
}

assert_file_contains() {
  grep -F -- "$1" "$2" >/dev/null || fail "missing '$1' in $2"
}

assert_file_absent() {
  ! grep -F -- "$1" "$2" >/dev/null || fail "unexpected '$1' in $2"
}

assert_probe_clean() {
  [[ -z "$(find "${PROBE_TMP}" -maxdepth 1 -type f -name 'dev-vm-lima-version.*' -print -quit)" ]] || fail "Lima probe residue remains"
}

# Malformed explicit forms are rejected before require_lima or any limactl call.
for malformed in foo --; do
  reset_case
  run_script ${malformed}
  assert_failure
  [[ ! -s "${CALL_LOG}" ]] || fail "limactl called for malformed argv ${malformed}"
done
reset_case
run_script -- relative
assert_failure
[[ ! -s "${CALL_LOG}" ]] || fail "limactl called for relative command"

# The zero-argument branch retains its historical argv and status behavior.
reset_case
STUB_SHELL_STATUS=37
run_script
assert_status 37
assert_probe_clean
first_lines="$(sed -n '1,8p' "${CALL_LOG}")"
[[ "${first_lines}" == $'CALL\n<list>\n<--format>\n<{{.Name}}>\nCALL\n<start>\n<gemini-pda-dev>\nCALL' ]] || fail "zero-argument limactl argv changed"
assert_file_absent '<--version>' "${CALL_LOG}"
assert_file_contains '<bash>' "${CALL_LOG}"
assert_file_contains '<-lc>' "${CALL_LOG}"

# Version and bounded help failures stop before list/start/shell transport.
reset_case
STUB_VERSION='limactl version 2.1.0'
run_script -- /usr/bin/true
assert_failure
assert_file_contains '<--version>' "${CALL_LOG}"
assert_file_absent '<list>' "${CALL_LOG}"
assert_file_absent '<start>' "${CALL_LOG}"
assert_file_absent '<shell>' "${CALL_LOG}"
assert_file_contains 'requires Lima 2.2.0' "${ERR}"
assert_probe_clean

reset_case
STUB_HELP='help without tty automation support'
run_script -- /usr/bin/true
assert_failure
assert_file_contains '<--version>' "${CALL_LOG}"
assert_file_contains '<shell>' "${CALL_LOG}"
assert_file_contains '<--help>' "${CALL_LOG}"
assert_file_absent '<list>' "${CALL_LOG}"
assert_file_absent '<start>' "${CALL_LOG}"
assert_file_contains 'requires bounded Lima --tty=false support' "${ERR}"
assert_probe_clean

reset_case
STUB_HELP_BIG=1
run_script -- /usr/bin/true
assert_failure
assert_file_absent '<start>' "${CALL_LOG}"
assert_file_contains 'Lima shell help output exceeds the 65536-byte bound' "${ERR}"
assert_probe_clean

reset_case
STUB_VERSION_BIG=1
run_script -- /usr/bin/true
assert_failure
assert_file_absent '<list>' "${CALL_LOG}"
assert_file_absent '<start>' "${CALL_LOG}"
assert_file_contains 'exceeds the 65536-byte bound' "${ERR}"
assert_probe_clean

reset_case
STUB_VERSION_SIGNAL=1
run_script -- /usr/bin/true
assert_failure
assert_file_absent '<list>' "${CALL_LOG}"
assert_file_absent '<start>' "${CALL_LOG}"
assert_probe_clean

# Explicit transport preserves literal arguments and uses the direct shell.
reset_case
STUB_RUN_GUEST=1
run_script -- /usr/bin/printf '%s\n' 'space value' 'quote" value' '$dollar' 'semi;colon' '--leading-option'
assert_status 0
expected=$'space value\nquote" value\n$dollar\nsemi;colon\n--leading-option\n'
printf '%s' "${expected}" | cmp -s - "${OUT}" || fail "literal command arguments changed"
assert_probe_clean
assert_file_contains '<--tty=false>' "${CALL_LOG}"
assert_file_contains '<--workdir=/tmp>' "${CALL_LOG}"
assert_file_contains '</bin/sh>' "${CALL_LOG}"
assert_file_contains '<-c>' "${CALL_LOG}"
assert_file_absent '<bash>' "${CALL_LOG}"
assert_file_absent '<-lc>' "${CALL_LOG}"
assert_file_absent '<-l>' "${CALL_LOG}"
assert_file_absent '<-i>' "${CALL_LOG}"
assert_file_absent 'SHELL' "${CALL_LOG}"
assert_file_contains 'exec /usr/bin/env -i' "${CALL_LOG}"
assert_file_contains 'cd -P' "${CALL_LOG}"

# The guest script rejects empty and relative HOME values before touching payloads.
for invalid_home in '' relative/home; do
  reset_case
  STUB_RUN_GUEST=1
  STUB_GUEST_HOME_OVERRIDE="${invalid_home}"
  run_script -- /usr/bin/true
  assert_status 1
  assert_file_contains 'error: guest home unavailable' "${ERR}"
done

# The guest script physically enters the payload before invoking the target.
reset_case
STUB_RUN_GUEST=1
run_script -- /bin/pwd
assert_status 0
expected_pwd="$(cd -P "${GUEST_HOME}/reverse-engineering/gemini-vendor" && pwd -P)"
printf '%s\n' "${expected_pwd}" | cmp -s - "${OUT}" || fail "guest physical working directory changed"

# The exact six-variable environment is applied only at env -i.
reset_case
STUB_RUN_GUEST=1
run_script -- /usr/bin/env
assert_status 0
printf '%s\n' \
  'DEBUGINFOD_URLS=' \
  'LC_ALL=C' \
  'PATH=/usr/bin:/bin' \
  'PIP_NO_INDEX=1' \
  'PYTHONDONTWRITEBYTECODE=1' \
  'TZ=UTC' | cmp -s - <(LC_ALL=C sort "${OUT}") || fail "environment assignments changed"

# The transport does not consume stdin.
reset_case
STUB_RUN_GUEST=1
printf '%s' 'stdin $ value; unchanged\n' >"${INPUT}"
run_script -- /bin/sh -c cat <"${INPUT}"
assert_status 0
cmp -s "${INPUT}" "${OUT}" || fail "stdin bytes changed"

# Guest-side failures are fixed and sanitized; target exit status propagates.
rm -rf "${GUEST_HOME}/reverse-engineering/gemini-vendor"
reset_case
STUB_RUN_GUEST=1
run_script -- /usr/bin/true
assert_status 1
assert_file_contains 'error: vendor payload unavailable' "${ERR}"
assert_file_absent "${GUEST_HOME}" "${ERR}"
mkdir -p "${GUEST_HOME}/reverse-engineering/gemini-vendor"

reset_case
STUB_RUN_GUEST=1
run_script -- /bin/sh -c 'exit 23'
assert_status 23

# Shell metacharacters remain data; the host never evaluates or joins argv.
MARKER="${TEST_ROOT}/marker"
reset_case
STUB_RUN_GUEST=1
evil='$(touch '"${MARKER}"')'
run_script -- /usr/bin/printf '%s\n' "${evil}" '--literal'
assert_status 0
assert_file_contains "\$(touch ${MARKER})" "${OUT}"
[[ ! -e "${MARKER}" ]] || fail "host evaluated a command argument"

echo "PASS: dev-vm re-shell transport regression"
