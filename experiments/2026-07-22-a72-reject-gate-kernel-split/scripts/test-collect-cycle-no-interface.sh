#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in basename cat chmod dirname expect grep kill mkdir mktemp rm sleep stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
watcher="$script_dir/collect-cycle.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86
control="$(mktemp -d /tmp/candidate-ai-cycle-selftest.XXXXXX)"
fake_bin="$control/bin"
mkdir -m 0700 "$fake_bin"
absent_output="$private_root/ai-initial-interface-absent-selftest-$$-$RANDOM"
default_route_output="$private_root/ai-default-route-absence-selftest-$$-$RANDOM"
mismatch_output="$private_root/ai-initial-interface-mismatch-selftest-$$-$RANDOM"
direct_route_mismatch_output="$private_root/ai-direct-route-mismatch-selftest-$$-$RANDOM"
timeout_output="$private_root/ai-no-cycle-timeout-selftest-$$-$RANDOM"
signal_output="$private_root/ai-no-interface-signal-selftest-$$-$RANDOM"
int_output="$private_root/ai-no-interface-int-selftest-$$-$RANDOM"
wrong_hash_output="$private_root/ai-wrong-hash-selftest-$$-$RANDOM"

cleanup() {
	local candidate
	for candidate in "$absent_output" "$default_route_output" "$mismatch_output" \
		"$direct_route_mismatch_output" "$timeout_output" "$signal_output" \
		"$int_output" "$wrong_hash_output"; do
		if [[ -d "$candidate" && ! -L "$candidate" && \
			"$(dirname -- "$candidate")" == "$private_root" && \
			"$(basename -- "$candidate")" == ai-*-selftest-* ]]; then
			rm -r -- "$candidate"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -f "$watcher" && ! -L "$watcher" ]] || die 'AI watcher is absent or unsafe'
for candidate in "$absent_output" "$default_route_output" "$mismatch_output" \
	"$direct_route_mismatch_output" "$timeout_output" "$signal_output" \
	"$int_output" "$wrong_hash_output"; do
	[[ ! -e "$candidate" && ! -L "$candidate" ]] || die 'self-test output collision'
done

set +e
PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$wrong_hash_output" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	--wait-seconds 1 \
	>"$control/wrong-hash.stdout" 2>"$control/wrong-hash.stderr"
wrong_hash_rc=$?
set -e
[[ "$wrong_hash_rc" == 2 ]] || die "wrong-hash watcher exit was $wrong_hash_rc, expected 2"
grep -q -- '--installed-full-sha256 is not Candidate AI' "$control/wrong-hash.stderr" || \
	die 'well-formed wrong installed-image hash was not rejected'
[[ ! -e "$wrong_hash_output" && ! -L "$wrong_hash_output" ]] || \
	die 'wrong installed-image hash created evidence'

cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
mode=${AI_TEST_LINK_MODE:-absent}
case "${1:-}" in
-l)
	if [[ "$mode" == stuck || "$mode" == direct-route-mismatch ]]; then
		printf 'en99\n'
	elif [[ "$mode" == mismatch ]]; then
		printf 'en98\n'
	else
		printf 'test0\n'
	fi
	;;
-a)
	if [[ "$mode" == stuck || "$mode" == direct-route-mismatch ]]; then
		printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
		printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
		printf '\tether 42:00:15:19:82:00\n'
	elif [[ "$mode" == mismatch ]]; then
		printf 'en98: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
		printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
		printf '\tether 42:00:15:19:82:77\n'
	else
		printf 'test0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384\n'
		printf '\tinet 127.0.0.1 netmask 0xff000000\n'
	fi
	;;
en99)
	[[ "$mode" == stuck || "$mode" == direct-route-mismatch ]] || exit 1
	printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:00\n'
	;;
en98)
	[[ "$mode" == mismatch ]] || exit 1
	printf 'en98: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
	printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
	printf '\tether 42:00:15:19:82:77\n'
	;;
test0)
	[[ "$mode" != stuck ]] || exit 1
	printf 'test0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384\n'
	printf '\tinet 127.0.0.1 netmask 0xff000000\n'
	;;
*)
	exit 1
	;;
esac
EOF
cat >"$fake_bin/ioreg" <<'EOF'
#!/usr/bin/env bash
if [[ "${AI_TEST_LINK_MODE:-absent}" == stuck ]]; then
	printf 'USB Serial Number = GEMINI_OBSERVABILITY_20260717_L\n'
else
	printf 'mock-no-usb-devices\n'
fi
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
case "${AI_TEST_LINK_MODE:-absent}" in
stuck)
	printf '   route to: 10.15.19.82\n'
	printf 'destination: 10.15.19.0\n'
	printf '       mask: 255.255.255.0\n'
	printf '  interface: en99\n'
	printf '      flags: <UP,DONE,CLONING,STATIC,IFSCOPE>\n'
	;;
direct-route-mismatch)
	printf '   route to: 10.15.19.82\n'
	printf 'destination: 10.15.19.0\n'
	printf '       mask: 255.255.255.0\n'
	printf '  interface: en88\n'
	printf '      flags: <UP,DONE,CLONING,STATIC,IFSCOPE>\n'
	;;
default-route)
	printf '   route to: 10.15.19.82\n'
	printf 'destination: default\n'
	printf '       mask: default\n'
	printf '    gateway: 192.168.1.1\n'
	printf '  interface: en0\n'
	printf '      flags: <UP,GATEWAY,DONE,STATIC,PRCLONING,GLOBAL>\n'
	;;
*)
	exit 1
	;;
esac
EOF
cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod 0700 "$fake_bin/ifconfig" "$fake_bin/ioreg" "$fake_bin/route" \
	"$fake_bin/ping"

cat >"$control/send-ctrl-c.exp" <<'EOF'
#!/usr/bin/expect -f
log_user 0
set timeout 15
set watcher [lindex $argv 0]
set output [lindex $argv 1]
set checksum [lindex $argv 2]
set events [lindex $argv 3]
spawn env PATH=$env(PATH) bash $watcher --output $output \
	--installed-full-sha256 $checksum --wait-seconds 30
set ready 0
set deadline [expr {[clock milliseconds] + 10000}]
while {[clock milliseconds] < $deadline} {
	if {[file exists $events]} {
		set stream [open $events r]
		set contents [read $stream]
		close $stream
			if {[string first "cycle_disconnect=pending" $contents] >= 0} {
			set ready 1
			break
		}
	}
	after 100
}
if {!$ready} {
	exit 97
}
send -- "\003"
expect eof
set result [wait]
exit [lindex $result 3]
EOF
chmod 0700 "$control/send-ctrl-c.exp"

set +e
PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$absent_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 4 \
	>"$control/stdout" 2>"$control/stderr"
watcher_rc=$?
set -e

[[ "$watcher_rc" == 2 ]] || die "no-interface watcher exit was $watcher_rc, expected 2"
status="$absent_output/status.env"
events="$absent_output/events.txt"
[[ -f "$status" && ! -L "$status" ]] || die 'watcher did not preserve failure status'
[[ -f "$events" && ! -L "$events" ]] || die 'watcher did not preserve event log'
grep -qx 'experiment=2026-07-22-a72-reject-gate-kernel-split' "$status" || \
	die 'failure status has the wrong experiment identity'
grep -qx 'candidate_label=AI' "$status" || die 'failure status has the wrong candidate label'
grep -qx 'operation_status=failed' "$status" || die 'failure operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$status" || die 'pre-identity oracle is not inconclusive'
grep -qx 'runtime_subgate=not-run' "$status" || die 'runtime subgate ran without preflight'
grep -qx 'phase=waiting-for-reappearance' "$status" || \
	die 'initial-absence timeout phase is not reappearance wait'
grep -qx 'preflight_path=initially-absent' "$status" || \
	die 'initially absent preflight path was not recorded'
grep -qx 'initial_link_verified=no' "$status" || die 'absent initial link was marked verified'
grep -qx 'initial_absence_confirmed=yes' "$status" || \
	die 'two clean initial absences were not confirmed'
grep -qx 'disconnect_observed=no' "$status" || die 'disconnect was fabricated'
grep -qx 'collector_invocations=0' "$status" || die 'collector ran without an exact interface'
grep -qx "installed_full_sha256_input=$expected_sha256" "$status" || \
	die 'failure status lost the installed-image checksum input'
[[ ! -e "$absent_output/runtime.txt" && ! -L "$absent_output/runtime.txt" ]] || \
	die 'runtime capture exists despite no exact interface'
grep -q 'initial_absence=confirmed' "$events" || \
	die 'initial absence confirmation event was not recorded'

set +e
AI_TEST_LINK_MODE=default-route PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$default_route_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 4 \
	>"$control/default-route.stdout" 2>"$control/default-route.stderr"
default_route_rc=$?
set -e
[[ "$default_route_rc" == 2 ]] || \
	die "default-route watcher exit was $default_route_rc, expected 2"
default_route_status="$default_route_output/status.env"
default_route_events="$default_route_output/events.txt"
grep -qx 'operation_status=failed' "$default_route_status" || \
	die 'default-route timeout operation is not failed'
grep -qx 'phase=waiting-for-reappearance' "$default_route_status" || \
	die 'default route was not ignored during initial absence'
grep -qx 'initial_absence_confirmed=yes' "$default_route_status" || \
	die 'default route prevented clean initial absence confirmation'
grep -qx 'collector_invocations=0' "$default_route_status" || \
	die 'collector ran for an ordinary default route'
grep -q 'initial_absence=confirmed' "$default_route_events" || \
	die 'default-route absence confirmation event is absent'
[[ ! -e "$default_route_output/runtime.txt" && \
	! -L "$default_route_output/runtime.txt" ]] || \
	die 'default route produced a runtime capture'

set +e
AI_TEST_LINK_MODE=mismatch PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$mismatch_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 2 \
	>"$control/mismatch.stdout" 2>"$control/mismatch.stderr"
mismatch_rc=$?
set -e
[[ "$mismatch_rc" == 2 ]] || die "mismatched-link exit was $mismatch_rc, expected 2"
mismatch_status="$mismatch_output/status.env"
grep -qx 'operation_status=failed' "$mismatch_status" || \
	die 'mismatched-link operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$mismatch_status" || \
	die 'mismatched pre-identity link is not inconclusive'
grep -qx 'initial_absence_confirmed=no' "$mismatch_status" || \
	die 'mismatched link was accepted as clean initial absence'
grep -qx 'collector_invocations=0' "$mismatch_status" || \
	die 'collector ran on a mismatched initial link'
grep -q 'exact host address is present without the exact Gemini MAC' \
	"$control/mismatch.stderr" || die 'mismatched MAC/address did not fail closed'

set +e
AI_TEST_LINK_MODE=direct-route-mismatch PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$direct_route_mismatch_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 2 \
	>"$control/direct-route-mismatch.stdout" \
	2>"$control/direct-route-mismatch.stderr"
direct_route_mismatch_rc=$?
set -e
[[ "$direct_route_mismatch_rc" == 2 ]] || \
	die "direct-route mismatch exit was $direct_route_mismatch_rc, expected 2"
direct_route_mismatch_status="$direct_route_mismatch_output/status.env"
grep -qx 'operation_status=failed' "$direct_route_mismatch_status" || \
	die 'direct-route mismatch operation is not failed'
grep -qx 'initial_link_verified=no' "$direct_route_mismatch_status" || \
	die 'mismatched direct route was accepted as an exact initial link'
grep -qx 'route_interface=en88' "$direct_route_mismatch_status" || \
	die 'mismatched direct route interface was not preserved'
grep -qx 'collector_invocations=0' "$direct_route_mismatch_status" || \
	die 'collector ran on a mismatched direct route'
grep -q 'pre-cycle Gemini USB route is not the exact interface' \
	"$control/direct-route-mismatch.stderr" || \
	die 'mismatched direct route did not fail closed'

set +e
AI_TEST_LINK_MODE=stuck PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$timeout_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 2 \
	>"$control/timeout.stdout" 2>"$control/timeout.stderr"
timeout_rc=$?
set -e
[[ "$timeout_rc" == 2 ]] || die "no-cycle watcher exit was $timeout_rc, expected 2"
timeout_status="$timeout_output/status.env"
timeout_events="$timeout_output/events.txt"
grep -qx 'operation_status=failed' "$timeout_status" || die 'no-cycle operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$timeout_status" || die 'no-cycle oracle is not inconclusive'
grep -qx 'phase=waiting-for-disconnect' "$timeout_status" || \
	die 'no-cycle phase is not waiting for disconnect'
grep -qx 'initial_link_verified=yes' "$timeout_status" || \
	die 'no-cycle preflight was not verified'
grep -qx 'preflight_path=present-then-disconnected' "$timeout_status" || \
	die 'present preflight path was not recorded'
grep -qx 'initial_absence_confirmed=no' "$timeout_status" || \
	die 'present path fabricated initial absence proof'
grep -qx 'disconnect_observed=no' "$timeout_status" || die 'no-cycle disconnect was fabricated'
grep -qx 'collector_invocations=0' "$timeout_status" || die 'collector ran without a cycle'
grep -q 'cycle_disconnect=pending' "$timeout_events" || die 'cycle wait event is absent'

for evidence_dir in "$absent_output" "$default_route_output" "$mismatch_output" \
	"$direct_route_mismatch_output" "$timeout_output"; do
	[[ "$(stat -f '%Lp' "$evidence_dir" 2>/dev/null || stat -c '%a' "$evidence_dir")" == 700 ]] || \
		die 'failure evidence directory mode is not 0700'
	for evidence_file in "$evidence_dir/status.env" "$evidence_dir/events.txt"; do
		[[ "$(stat -f '%Lp' "$evidence_file" 2>/dev/null || stat -c '%a' "$evidence_file")" == 600 ]] || \
			die 'failure evidence file mode is not 0600'
	done
done

AI_TEST_LINK_MODE=stuck PATH="$fake_bin:$PATH" bash "$watcher" \
	--output "$signal_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 30 \
	>"$control/signal.stdout" 2>"$control/signal.stderr" &
watcher_pid=$!
signal_events="$signal_output/events.txt"
ready=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
	if [[ -f "$signal_events" ]] && grep -q 'cycle_disconnect=pending' "$signal_events"; then
		ready=1
		break
	fi
	sleep 1
done
((ready == 1)) || die 'signal self-test watcher did not enter exact-MAC wait'
kill -TERM "$watcher_pid"
set +e
wait "$watcher_pid"
signal_rc=$?
set -e
[[ "$signal_rc" == 143 ]] || die "signalled watcher exit was $signal_rc, expected 143"
signal_status="$signal_output/status.env"
[[ -f "$signal_status" && ! -L "$signal_status" ]] || \
	die 'signalled watcher did not preserve failure status'
grep -qx 'operation_status=failed' "$signal_status" || die 'signalled operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$signal_status" || die 'signalled oracle is not inconclusive'
grep -qx 'exit_code=143' "$signal_status" || die 'signalled status lost exit 143'
grep -qx 'phase=waiting-for-disconnect' "$signal_status" || \
	die 'signalled failure phase is not disconnect wait'
grep -qx 'collector_invocations=0' "$signal_status" || \
	die 'collector ran before the watcher was signalled'
grep -qx 'last_detail=received-signal-TERM' "$signal_status" || \
	die 'signalled status lost the TERM attribution'

set +e
AI_TEST_LINK_MODE=stuck PATH="$fake_bin:$PATH" expect "$control/send-ctrl-c.exp" \
	"$watcher" "$int_output" "$expected_sha256" "$int_output/events.txt" \
	>"$control/int.stdout" 2>"$control/int.stderr"
int_rc=$?
set -e
[[ "$int_rc" == 130 ]] || die "Ctrl-C watcher exit was $int_rc, expected 130"
int_status="$int_output/status.env"
[[ -f "$int_status" && ! -L "$int_status" ]] || \
	die 'Ctrl-C watcher did not preserve failure status.env'
grep -qx 'operation_status=failed' "$int_status" || die 'Ctrl-C operation is not failed'
grep -qx 'oracle=INCONCLUSIVE' "$int_status" || die 'Ctrl-C oracle is not inconclusive'
grep -qx 'exit_code=130' "$int_status" || die 'Ctrl-C status lost exit 130'
grep -qx 'collector_invocations=0' "$int_status" || \
	die 'collector ran before foreground Ctrl-C'
grep -qx 'last_detail=received-signal-INT' "$int_status" || \
	die 'Ctrl-C status lost the INT attribution'

printf 'validation=candidate-ai-collect-cycle-no-interface\n'
printf 'initial_interface_absent=INCONCLUSIVE\n'
printf 'ordinary_default_gateway_route=ignored-as-clean-initial-absence\n'
printf 'mismatched_initial_link=fail-closed\n'
printf 'direct_mismatched_route=fail-closed\n'
printf 'no_cycle_timeout=INCONCLUSIVE\n'
printf 'signalled_watcher_exit=143\n'
printf 'ctrl_c_watcher_exit=130\n'
printf 'collector_invocations=0\n'
printf 'runtime_capture=absent\n'
printf 'device_access=none-host-network-tools-mocked\n'
