#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk basename cat chmod dirname grep mkdir mktemp python3 rm shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
watcher="$script_dir/collect-cycle.sh"
collector="$script_dir/collect-runtime.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
control="$(mktemp -d /tmp/candidate-ai-cycle-one-shot.XXXXXX)"
fake_bin="$control/bin"
mkdir -m 0700 "$fake_bin"
reject_output="$private_root/ai-one-shot-reject-selftest-$$-$RANDOM"
success_output="$private_root/ai-one-shot-success-selftest-$$-$RANDOM"
reject_nc_count="$control/reject-nc-count"
success_nc_count="$control/success-nc-count"
link_state="$control/link-state"
absence_count="$control/absence-count"
ioreg_count="$control/ioreg-count"
runtime_fixture="$control/runtime-fixture"

cleanup() {
	local output
	for output in "$reject_output" "$success_output"; do
		if [[ -d "$output" && ! -L "$output" && \
			"$(dirname -- "$output")" == "$private_root" && \
			"$(basename -- "$output")" == ai-one-shot-*-selftest-* ]]; then
			rm -r -- "$output"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -f "$watcher" && ! -L "$watcher" ]] || die 'AI watcher is absent or unsafe'
[[ -f "$collector" && ! -L "$collector" ]] || die 'AI collector is absent or unsafe'
for output in "$reject_output" "$success_output"; do
	[[ ! -e "$output" && ! -L "$output" ]] || die 'self-test output collision'
done

set +e
bash "$collector" --interface en99 --output "$control/wrong-runtime.txt" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	>"$control/wrong-hash.stdout" 2>"$control/wrong-hash.stderr"
wrong_hash_rc=$?
set -e
[[ "$wrong_hash_rc" == 2 ]] || die "wrong-hash collector exit was $wrong_hash_rc, expected 2"
grep -q 'installed full-partition checksum is not Candidate AI' \
	"$control/wrong-hash.stderr" || die 'runtime collector accepted a different image hash'
[[ ! -e "$control/wrong-runtime.txt" && ! -L "$control/wrong-runtime.txt" ]] || \
	die 'wrong installed-image hash created a runtime capture'

cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
: "${AI_TEST_LINK_STATE:?}"
: "${AI_TEST_ABSENCE_COUNT:?}"
state=$(cat "$AI_TEST_LINK_STATE")
case "${1:-}" in
-l)
	case "$state" in
	initial|reappeared)
		printf 'en99\n'
		;;
	absent)
		count=0
		if [[ -f "$AI_TEST_ABSENCE_COUNT" ]]; then
			read -r count <"$AI_TEST_ABSENCE_COUNT"
		fi
		count=$((count + 1))
		printf '%s\n' "$count" >"$AI_TEST_ABSENCE_COUNT"
		if ((count >= 2)); then
			printf 'reappeared\n' >"$AI_TEST_LINK_STATE"
		fi
		;;
	initial-absent)
		;;
	*)
		exit 91
		;;
	esac
	;;
-a)
	[[ "$state" == initial || "$state" == reappeared ]] || exit 0
	printf 'en99: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
en99)
	[[ "$state" == initial || "$state" == reappeared ]] || exit 1
	printf 'en99: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
*)
	exit 1
	;;
esac
EOF
cat >"$fake_bin/ioreg" <<'EOF'
#!/usr/bin/env bash
: "${AI_TEST_LINK_STATE:?}"
state=$(cat "$AI_TEST_LINK_STATE")
case "$state" in
initial|reappeared)
	printf 'USB Serial Number = GEMINI_OBSERVABILITY_20260717_L\n'
	;;
initial-absent)
	: "${AI_TEST_IOREG_COUNT:?}"
	count=0
	if [[ -f "$AI_TEST_IOREG_COUNT" ]]; then
		read -r count <"$AI_TEST_IOREG_COUNT"
	fi
	count=$((count + 1))
	printf '%s\n' "$count" >"$AI_TEST_IOREG_COUNT"
	printf 'mock-no-usb-devices\n'
	if ((count >= 3)); then
		printf 'reappeared\n' >"$AI_TEST_LINK_STATE"
	fi
	;;
*)
	printf 'mock-no-usb-devices\n'
	;;
esac
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
: "${AI_TEST_LINK_STATE:?}"
case "$(cat "$AI_TEST_LINK_STATE")" in
initial|reappeared) ;;
*) exit 1 ;;
esac
printf '   route to: 10.15.19.82\n'
printf '  interface: en99\n'
EOF
cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
: "${AI_TEST_LINK_STATE:?}"
state=$(cat "$AI_TEST_LINK_STATE")
case "$state" in
initial)
	printf 'absent\n' >"$AI_TEST_LINK_STATE"
	exit 0
	;;
reappeared)
	exit 0
	;;
*)
	exit 1
	;;
esac
EOF
cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
: "${AI_TEST_NC_COUNT:?}"
: "${AI_TEST_NC_MODE:?}"
count=0
if [[ -f "$AI_TEST_NC_COUNT" ]]; then
	read -r count <"$AI_TEST_NC_COUNT"
fi
printf '%s\n' "$((count + 1))" >"$AI_TEST_NC_COUNT"
case "$AI_TEST_NC_MODE" in
reject)
	exit 7
	;;
success)
	: "${AI_TEST_RUNTIME_FIXTURE:?}"
	cat "$AI_TEST_RUNTIME_FIXTURE"
	exit 0
	;;
*)
	exit 92
	;;
esac
EOF
chmod 0700 "$fake_bin/ifconfig" "$fake_bin/ioreg" "$fake_bin/route" \
	"$fake_bin/ping" "$fake_bin/nc"

python3 - "$script_dir" "$runtime_fixture" <<'PY'
import importlib.util
import pathlib
import sys

sys.dont_write_bytecode = True
script_dir = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])

def load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

validator = load(script_dir / "validate-runtime.py", "ai_cycle_success_validator")
tests = load(script_dir / "test-runtime-validator.py", "ai_cycle_success_fixture")
fixture = tests.fixture(validator)
separator = "__AI_HOST_END__\r\n"
if fixture.count(separator) != 1:
    raise RuntimeError("runtime fixture host separator changed")
output.write_bytes(fixture.split(separator, 1)[1].encode("utf-8"))
PY

export AI_TEST_LINK_STATE="$link_state"
export AI_TEST_ABSENCE_COUNT="$absence_count"
export AI_TEST_IOREG_COUNT="$ioreg_count"
export AI_TEST_RUNTIME_FIXTURE="$runtime_fixture"
printf 'initial\n' >"$link_state"
printf '0\n' >"$absence_count"
printf '0\n' >"$ioreg_count"
export AI_TEST_NC_COUNT="$reject_nc_count"
export AI_TEST_NC_MODE=reject
set +e
PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$reject_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 10 \
	>"$control/reject.stdout" 2>"$control/reject.stderr"
watcher_rc=$?
set -e

[[ "$watcher_rc" == 7 ]] || die "one-shot watcher exit was $watcher_rc, expected 7"
[[ -f "$reject_nc_count" ]] || die 'mock nc was never invoked'
[[ "$(cat "$reject_nc_count")" == 1 ]] || die 'collector retried the failed TCP session'

status="$reject_output/status.env"
events="$reject_output/events.txt"
capture="$reject_output/runtime.txt"
[[ -f "$status" && ! -L "$status" ]] || die 'one-shot watcher omitted failure status'
[[ -f "$events" && ! -L "$events" ]] || die 'one-shot watcher omitted event log'
[[ -f "$capture" && ! -L "$capture" ]] || die 'collector did not preserve its partial capture'
output_mode="$(stat -f '%Lp' "$reject_output" 2>/dev/null || stat -c '%a' "$reject_output")"
status_mode="$(stat -f '%Lp' "$status" 2>/dev/null || stat -c '%a' "$status")"
events_mode="$(stat -f '%Lp' "$events" 2>/dev/null || stat -c '%a' "$events")"
capture_mode="$(stat -f '%Lp' "$capture" 2>/dev/null || stat -c '%a' "$capture")"
[[ "$output_mode" == 700 ]] || die 'one-shot private output mode is not 0700'
[[ "$status_mode" == 600 && "$events_mode" == 600 && "$capture_mode" == 600 ]] || \
	die 'one-shot evidence files are not mode 0600'
grep -qx 'candidate_label=AI' "$status" || die 'one-shot status has wrong candidate label'
grep -qx 'operation_status=failed' "$status" || die 'one-shot operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$status" || die 'pre-identity rejection is not inconclusive'
grep -qx 'runtime_subgate=rejected' "$status" || die 'runtime rejection subgate was lost'
grep -qx 'runtime_identity_capture=absent-or-incomplete' "$status" || \
	die 'empty collector response was not recorded as pre-identity'
grep -qx 'exit_code=7' "$status" || die 'one-shot status lost collector exit code'
grep -qx 'phase=runtime-rejected' "$status" || die 'one-shot phase is not runtime-rejected'
grep -qx 'initial_link_verified=yes' "$status" || die 'initial exact link was not verified'
grep -qx 'disconnect_observed=yes' "$status" || die 'cycle disconnect was not verified'
grep -qx 'reappearance_verified=yes' "$status" || die 'cycle reappearance was not verified'
grep -qx 'collector_invocations=1' "$status" || die 'one-shot invocation count changed'
grep -qx 'collector_rc=7' "$status" || die 'one-shot collector result changed'
grep -qx "installed_full_sha256_input=$expected_sha256" "$status" || \
	die 'one-shot status lost installed checksum attestation'
collector_sha256="$(shasum -a 256 "$collector" | awk '{ print $1 }')"
grep -qx "collector_sha256=$collector_sha256" "$status" || \
	die 'one-shot status lost source-pinned collector identity'
awk '
/cycle_disconnect=confirmed/ { disconnect = NR }
/cycle_reappearance=verified/ { reappearance = NR }
/collector_invocations=1/ { collection = NR }
END { exit !(disconnect && reappearance > disconnect && collection > reappearance) }
' "$events" || die 'collector was not ordered after disconnect and exact reappearance'

sleep 1
[[ "$(cat "$reject_nc_count")" == 1 ]] || die 'collector retried after watcher completion'

printf 'initial-absent\n' >"$link_state"
printf '0\n' >"$absence_count"
printf '0\n' >"$ioreg_count"
export AI_TEST_NC_COUNT="$success_nc_count"
export AI_TEST_NC_MODE=success
PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$success_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 10 \
	>"$control/success.stdout" 2>"$control/success.stderr"

[[ -f "$success_nc_count" ]] || die 'successful mock nc was never invoked'
[[ "$(cat "$success_nc_count")" == 1 ]] || die 'successful collector was not one-shot'
success_status="$success_output/status.env"
success_events="$success_output/events.txt"
success_capture="$success_output/runtime.txt"
for evidence in "$success_status" "$success_events" "$success_capture"; do
	[[ -f "$evidence" && ! -L "$evidence" ]] || die 'successful cycle omitted evidence'
done
grep -qx 'operation_status=completed' "$success_status" || \
	die 'successful runtime operation did not complete'
grep -qx 'runtime_subgate=passed' "$success_status" || \
	die 'successful runtime subgate was not recorded'
grep -qx 'oracle=PENDING_NATIVE_REBOOT_AND_CONSOLE' "$success_status" || \
	die 'runtime success was incorrectly promoted to overall PASS'
grep -qx 'native_reboot_subgate=not-run' "$success_status" || \
	die 'runtime collector fabricated native reboot evidence'
grep -qx 'console_subgate=not-observed' "$success_status" || \
	die 'runtime collector fabricated console evidence'
grep -qx 'overall_pass_permitted=no' "$success_status" || \
	die 'runtime-only evidence permits an overall pass'
grep -qx 'runtime_identity_capture=complete' "$success_status" || \
	die 'successful runtime identity was not recorded'
grep -qx 'preflight_path=initially-absent' "$success_status" || \
	die 'successful initially absent preflight path was not recorded'
grep -qx 'initial_link_verified=no' "$success_status" || \
	die 'successful absent path fabricated initial link proof'
grep -qx 'initial_absence_confirmed=yes' "$success_status" || \
	die 'successful cycle omitted initial absence proof'
grep -qx 'disconnect_observed=no' "$success_status" || \
	die 'successful absent path fabricated a disconnect transition'
grep -qx 'reappearance_verified=yes' "$success_status" || \
	die 'successful cycle omitted reappearance proof'
grep -qx 'collector_invocations=1' "$success_status" || \
	die 'successful collector invocation count changed'
if grep -qE '^(result=passed|oracle=PASS)$' "$success_status" "$control/success.stdout"; then
	die 'runtime-only success was labeled as an overall pass'
fi
awk '
/initial_absence=confirmed/ { disconnect = NR }
/cycle_reappearance=verified/ { reappearance = NR }
/collector_invocations=1/ { collection = NR }
END { exit !(disconnect && reappearance > disconnect && collection > reappearance) }
' "$success_events" || die 'successful collector ran before the verified cycle'

success_output_mode="$(stat -f '%Lp' "$success_output" 2>/dev/null || stat -c '%a' "$success_output")"
success_status_mode="$(stat -f '%Lp' "$success_status" 2>/dev/null || stat -c '%a' "$success_status")"
success_events_mode="$(stat -f '%Lp' "$success_events" 2>/dev/null || stat -c '%a' "$success_events")"
success_capture_mode="$(stat -f '%Lp' "$success_capture" 2>/dev/null || stat -c '%a' "$success_capture")"
[[ "$success_output_mode" == 700 ]] || die 'successful private output mode is not 0700'
[[ "$success_status_mode" == 600 && "$success_events_mode" == 600 && \
	"$success_capture_mode" == 600 ]] || die 'successful evidence files are not mode 0600'

sleep 1
[[ "$(cat "$success_nc_count")" == 1 ]] || die 'successful collector retried after completion'

printf 'validation=candidate-ai-collect-cycle-one-shot\n'
printf 'initial_link_disconnect_reappearance=mocked-passed\n'
printf 'collector_invocations=one-per-cycle\n'
printf 'collector_exit=7\n'
printf 'retry=absent\n'
printf 'partial_capture=preserved\n'
printf 'successful_runtime_subgate=passed\n'
printf 'successful_runtime_oracle=PENDING_NATIVE_REBOOT_AND_CONSOLE\n'
printf 'private_modes=0700-directory-0600-files\n'
printf 'device_access=none-network-tools-mocked\n'
