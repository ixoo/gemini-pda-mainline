#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk bash basename cat chmod dirname grep mkdir mktemp python3 rm \
	shasum sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
watcher="$script_dir/collect-cycle.sh"
collector="$script_dir/collect-runtime.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
expected_boot_id=01234567-89ab-cdef-0123-456789abcdef
control="$(mktemp -d /tmp/candidate-aj-cycle-one-shot.XXXXXX)"
fake_bin="$control/bin"
reject_output="$private_root/aj-one-shot-reject-selftest-$$-$RANDOM"
success_output="$private_root/aj-one-shot-success-selftest-$$-$RANDOM"
wrong_output="$private_root/aj-one-shot-wrong-hash-selftest-$$-$RANDOM"
reject_nc_count="$control/reject-nc-count"
success_nc_count="$control/success-nc-count"
link_state="$control/link-state"
absence_count="$control/absence-count"
ioreg_count="$control/ioreg-count"
runtime_fixture="$control/runtime-fixture"

cleanup() {
	local output
	for output in "$reject_output" "$success_output" "$wrong_output"; do
		if [[ -d "$output" && ! -L "$output" && \
			"$(dirname -- "$output")" == "$private_root" && \
			"$(basename -- "$output")" == aj-one-shot-*-selftest-* ]]; then
			rm -r -- "$output"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -f "$watcher" && ! -L "$watcher" ]] || die 'AJ watcher is absent or unsafe'
[[ -f "$collector" && ! -L "$collector" ]] || die 'AJ collector is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private capture root is absent'
for output in "$reject_output" "$success_output" "$wrong_output"; do
	[[ ! -e "$output" && ! -L "$output" ]] || die 'self-test output collision'
done

# The installed-image gate must reject before any capture directory exists.
set +e
bash "$watcher" --output "$wrong_output" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	--wait-seconds 2 >"$control/wrong.stdout" 2>"$control/wrong.stderr"
wrong_rc=$?
set -e
[[ "$wrong_rc" == 2 ]] || die "wrong-hash watcher exit was $wrong_rc"
grep -q -- '--installed-full-sha256 is not Candidate AJ' "$control/wrong.stderr" || \
	die 'cycle watcher accepted a different installed image'
[[ ! -e "$wrong_output" && ! -L "$wrong_output" ]] || \
	die 'wrong installed-image hash created an evidence path'

mkdir -m 0700 "$fake_bin"
cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_LINK_STATE:?}"
: "${AJ_TEST_ABSENCE_COUNT:?}"
state=$(cat "$AJ_TEST_LINK_STATE")
case "${1:-}" in
-l)
	case "$state" in
	initial|reappeared)
		printf 'en99\n'
		;;
	absent)
		count=0
		if [[ -f "$AJ_TEST_ABSENCE_COUNT" ]]; then
			read -r count <"$AJ_TEST_ABSENCE_COUNT"
		fi
		count=$((count + 1))
		printf '%s\n' "$count" >"$AJ_TEST_ABSENCE_COUNT"
		if ((count >= 2)); then
			printf 'reappeared\n' >"$AJ_TEST_LINK_STATE"
		fi
		;;
	initial-absent)
		;;
	*) exit 91 ;;
	esac
	;;
-a)
	[[ "$state" == initial || "$state" == reappeared ]] || exit 0
	printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
en99)
	[[ "$state" == initial || "$state" == reappeared ]] || exit 1
	printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
*) exit 1 ;;
esac
EOF
cat >"$fake_bin/ioreg" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_LINK_STATE:?}"
state=$(cat "$AJ_TEST_LINK_STATE")
case "$state" in
initial|reappeared)
	printf 'USB Serial Number = GEMINI_OBSERVABILITY_20260717_L\n'
	;;
initial-absent)
	: "${AJ_TEST_IOREG_COUNT:?}"
	count=0
	if [[ -f "$AJ_TEST_IOREG_COUNT" ]]; then
		read -r count <"$AJ_TEST_IOREG_COUNT"
	fi
	count=$((count + 1))
	printf '%s\n' "$count" >"$AJ_TEST_IOREG_COUNT"
	printf 'mock-no-usb-devices\n'
	if ((count >= 3)); then
		printf 'reappeared\n' >"$AJ_TEST_LINK_STATE"
	fi
	;;
*) printf 'mock-no-usb-devices\n' ;;
esac
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_LINK_STATE:?}"
case "$(cat "$AJ_TEST_LINK_STATE")" in
initial|reappeared) ;;
*) exit 1 ;;
esac
printf '   route to: 10.15.19.82\n'
printf '  interface: en99\n'
EOF
cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_LINK_STATE:?}"
state=$(cat "$AJ_TEST_LINK_STATE")
case "$state" in
initial)
	printf 'absent\n' >"$AJ_TEST_LINK_STATE"
	exit 0
	;;
reappeared) exit 0 ;;
*) exit 1 ;;
esac
EOF
cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_NC_COUNT:?}"
: "${AJ_TEST_NC_MODE:?}"
count=0
if [[ -f "$AJ_TEST_NC_COUNT" ]]; then
	read -r count <"$AJ_TEST_NC_COUNT"
fi
printf '%s\n' "$((count + 1))" >"$AJ_TEST_NC_COUNT"
case "$AJ_TEST_NC_MODE" in
reject) exit 7 ;;
success)
	: "${AJ_TEST_RUNTIME_FIXTURE:?}"
	cat "$AJ_TEST_RUNTIME_FIXTURE"
	exit 0
	;;
*) exit 92 ;;
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
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load(script_dir / "validate-runtime.py", "aj_cycle_success_validator")
tests = load(script_dir / "test-runtime-validator.py", "aj_cycle_success_fixture")
fixture = tests.fixture(validator)
separator = "__AJ_HOST_END__\r\n"
if fixture.count(separator) != 1:
    raise RuntimeError("runtime fixture host separator changed")
output.write_bytes(fixture.split(separator, 1)[1].encode("utf-8"))
PY

export AJ_TEST_LINK_STATE="$link_state"
export AJ_TEST_ABSENCE_COUNT="$absence_count"
export AJ_TEST_IOREG_COUNT="$ioreg_count"
export AJ_TEST_RUNTIME_FIXTURE="$runtime_fixture"

# Present and packet-ready, then two absent observations, then exact
# reappearance: a rejected TCP response must remain a one-shot failure with all
# partial evidence preserved.
printf 'initial\n' >"$link_state"
printf '0\n' >"$absence_count"
printf '0\n' >"$ioreg_count"
export AJ_TEST_NC_COUNT="$reject_nc_count"
export AJ_TEST_NC_MODE=reject
set +e
PATH="$fake_bin:$PATH" bash "$watcher" --output "$reject_output" \
	--installed-full-sha256 "$expected_sha256" --wait-seconds 10 \
	>"$control/reject.stdout" 2>"$control/reject.stderr"
reject_rc=$?
set -e

[[ "$reject_rc" == 7 ]] || die "one-shot watcher exit was $reject_rc, expected 7"
[[ -f "$reject_nc_count" && "$(cat "$reject_nc_count")" == 1 ]] || \
	die 'watcher omitted or retried the rejected TCP session'
reject_status="$reject_output/status.env"
reject_events="$reject_output/events.txt"
reject_capture="$reject_output/runtime.txt"
for evidence in "$reject_status" "$reject_events" "$reject_capture" \
	"$reject_output/collector.stdout" "$reject_output/collector.stderr"; do
	[[ -f "$evidence" && ! -L "$evidence" ]] || die 'rejected cycle omitted evidence'
done
grep -qx 'candidate_label=AJ' "$reject_status" || die 'failure status has wrong label'
grep -qx 'operation_status=failed' "$reject_status" || die 'rejection is not failed'
grep -qx 'phase=runtime-rejected' "$reject_status" || die 'rejection phase changed'
grep -qx 'runtime_subgate=rejected' "$reject_status" || die 'rejection subgate changed'
grep -qx 'collector_invocations=1' "$reject_status" || die 'invocation count changed'
grep -qx 'collector_rc=7' "$reject_status" || die 'collector exit code was lost'
grep -qx 'initial_link_verified=yes' "$reject_status" || \
	die 'initial exact link was not verified'
grep -qx 'disconnect_observed=yes' "$reject_status" || die 'disconnect was not witnessed'
grep -qx 'reappearance_verified=yes' "$reject_status" || \
	die 'reappearance was not witnessed'
grep -qx 'runtime_boot_id_match=partial-or-invalid' "$reject_status" || \
	die 'partial capture fabricated a stable boot ID'
grep -qx 'overall_pass_permitted=no' "$reject_status" || \
	die 'rejected runtime permits an overall pass'
awk '
/cycle_disconnect=confirmed/ { disconnect = NR }
/cycle_reappearance=verified/ { reappearance = NR }
/collector_invocations=1/ { collection = NR }
END { exit !(disconnect && reappearance > disconnect && collection > reappearance) }
' "$reject_events" || die 'collector was not ordered after disconnect and reappearance'
sleep 1
[[ "$(cat "$reject_nc_count")" == 1 ]] || die 'watcher retried after rejection'

# Beginning before boot2 selection with two clean absences is the alternate
# cycle boundary. A successful capture must bind both samples to one exact boot
# ID while leaving all independent overall gates unresolved.
printf 'initial-absent\n' >"$link_state"
printf '0\n' >"$absence_count"
printf '0\n' >"$ioreg_count"
export AJ_TEST_NC_COUNT="$success_nc_count"
export AJ_TEST_NC_MODE=success
PATH="$fake_bin:$PATH" bash "$watcher" --output "$success_output" \
	--installed-full-sha256 "$expected_sha256" --wait-seconds 10 \
	>"$control/success.stdout" 2>"$control/success.stderr"

[[ -f "$success_nc_count" && "$(cat "$success_nc_count")" == 1 ]] || \
	die 'successful collector was not one-shot'
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
grep -qx 'oracle=PENDING_CONSOLE_REBOOT_RECOVERY_AND_BOOT2_INTEGRITY' \
	"$success_status" || die 'runtime success was promoted or lost independent gates'
grep -qx "runtime_boot_id_before=$expected_boot_id" "$success_status" || \
	die 'identity boot ID was not recorded exactly'
grep -qx "runtime_boot_id_after=$expected_boot_id" "$success_status" || \
	die 'stability boot ID was not recorded exactly'
grep -qx 'runtime_boot_id_match=yes' "$success_status" || \
	die 'exact stable boot-ID binding was not recorded'
grep -qx 'native_reboot_subgate=not-run' "$success_status" || \
	die 'watcher fabricated native reboot evidence'
grep -qx 'console_subgate=not-observed' "$success_status" || \
	die 'watcher fabricated console evidence'
grep -qx 'overall_pass_permitted=no' "$success_status" || \
	die 'runtime-only evidence permits an overall pass'
grep -qx 'preflight_path=initially-absent' "$success_status" || \
	die 'initially absent preflight path was not recorded'
grep -qx 'initial_absence_confirmed=yes' "$success_status" || \
	die 'clean pre-selection absence was not confirmed'
grep -qx 'disconnect_observed=no' "$success_status" || \
	die 'initially absent path fabricated a disconnect'
grep -qx 'reappearance_verified=yes' "$success_status" || \
	die 'successful cycle omitted exact reappearance'
if grep -qE '^(result=passed|oracle=PASS)$' "$success_status" \
	"$control/success.stdout"; then
	die 'runtime-only success was labeled as an overall pass'
fi
awk -v boot_id="$expected_boot_id" '
/initial_absence=confirmed/ { absence = NR }
/cycle_reappearance=verified/ { reappearance = NR }
/collector_invocations=1/ { collection = NR }
index($0, "runtime_boot_id=" boot_id) { binding = NR }
END {
	exit !(absence && reappearance > absence && collection > reappearance &&
	       binding > collection)
}
' "$success_events" || die 'boot-ID capture was not bound after the verified cycle'

for path in "$reject_output" "$success_output"; do
	[[ "$(stat -f '%Lp' "$path" 2>/dev/null || stat -c '%a' "$path")" == 700 ]] || \
		die 'private output directory mode is not 0700'
	for evidence in "$path/status.env" "$path/events.txt" "$path/runtime.txt"; do
		[[ "$(stat -f '%Lp' "$evidence" 2>/dev/null || stat -c '%a' "$evidence")" == 600 ]] || \
			die 'evidence file mode is not 0600'
	done
done

sleep 1
[[ "$(cat "$success_nc_count")" == 1 ]] || die 'successful watcher retried after completion'

printf 'validation=candidate-aj-collect-cycle-one-shot\n'
printf 'disconnect_reappearance=mocked-passed\n'
printf 'initial_absence_reappearance=mocked-passed\n'
printf 'collector_invocations=one-per-cycle\n'
printf 'failure_evidence=preserved\n'
printf 'stable_boot_id=%s\n' "$expected_boot_id"
printf 'overall_gates=not-fabricated\n'
printf 'private_modes=0700-directory-0600-files\n'
printf 'device_access=none-network-tools-mocked\n'
