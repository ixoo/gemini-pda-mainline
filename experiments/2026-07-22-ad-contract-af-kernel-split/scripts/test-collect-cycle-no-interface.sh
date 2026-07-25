#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in basename cat chmod dirname expect grep kill mkdir mktemp rm sleep; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
watcher="$script_dir/collect-cycle.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012
control="$(mktemp -d /tmp/candidate-ah-cycle-selftest.XXXXXX)"
fake_bin="$control/bin"
mkdir -m 0700 "$fake_bin"
timeout_output="$private_root/ah-no-interface-timeout-selftest-$$-$RANDOM"
signal_output="$private_root/ah-no-interface-signal-selftest-$$-$RANDOM"
int_output="$private_root/ah-no-interface-int-selftest-$$-$RANDOM"

cleanup() {
	local output
	for output in "$timeout_output" "$signal_output" "$int_output"; do
		if [[ -d "$output" && ! -L "$output" && \
			"$(dirname -- "$output")" == "$private_root" && \
			"$(basename -- "$output")" == ah-no-interface-*-selftest-* ]]; then
			rm -r -- "$output"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -x "$watcher" && ! -L "$watcher" ]] || die 'AH watcher is absent or unsafe'
for output in "$timeout_output" "$signal_output" "$int_output"; do
	[[ ! -e "$output" && ! -L "$output" ]] || die 'self-test output collision'
done

cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
-l)
	printf 'test0\n'
	;;
-a|test0)
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
printf 'mock-no-usb-devices\n'
EOF
chmod 0700 "$fake_bin/ifconfig" "$fake_bin/ioreg"

cat >"$control/send-ctrl-c.exp" <<'EOF'
#!/usr/bin/expect -f
log_user 0
set timeout 15
set watcher [lindex $argv 0]
set output [lindex $argv 1]
set checksum [lindex $argv 2]
set events [lindex $argv 3]
spawn env PATH=$env(PATH) $watcher --output $output \
	--installed-full-sha256 $checksum --wait-seconds 30
set ready 0
set deadline [expr {[clock milliseconds] + 10000}]
while {[clock milliseconds] < $deadline} {
	if {[file exists $events]} {
		set stream [open $events r]
		set contents [read $stream]
		close $stream
		if {[string first "exact_mac_interface=absent" $contents] >= 0} {
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
PATH="$fake_bin:$PATH" "$watcher" \
	--output "$timeout_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 2 \
	>"$control/stdout" 2>"$control/stderr"
watcher_rc=$?
set -e

[[ "$watcher_rc" == 2 ]] || die "no-interface watcher exit was $watcher_rc, expected 2"
status="$timeout_output/status.env"
events="$timeout_output/events.txt"
[[ -f "$status" && ! -L "$status" ]] || die 'watcher did not preserve failure status'
[[ -f "$events" && ! -L "$events" ]] || die 'watcher did not preserve event log'
grep -qx 'experiment=2026-07-22-ad-contract-af-kernel-split' "$status" || \
	die 'failure status has the wrong experiment identity'
grep -qx 'candidate_label=AH' "$status" || die 'failure status has the wrong candidate label'
grep -qx 'result=failed' "$status" || die 'failure status is not failed'
grep -qx 'phase=waiting-for-exact-mac' "$status" || die 'failure phase is not exact-MAC wait'
grep -qx 'collector_invocations=0' "$status" || die 'collector ran without an exact interface'
grep -qx "installed_full_sha256_input=$expected_sha256" "$status" || \
	die 'failure status lost the installed-image checksum input'
grep -q 'exact_mac_interface=absent' "$events" || die 'absence event was not recorded'
[[ ! -e "$timeout_output/runtime.txt" && ! -L "$timeout_output/runtime.txt" ]] || \
	die 'runtime capture exists despite no exact interface'

PATH="$fake_bin:$PATH" "$watcher" \
	--output "$signal_output" \
	--installed-full-sha256 "$expected_sha256" \
	--wait-seconds 30 \
	>"$control/signal.stdout" 2>"$control/signal.stderr" &
watcher_pid=$!
signal_events="$signal_output/events.txt"
ready=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
	if [[ -f "$signal_events" ]] && grep -q 'exact_mac_interface=absent' "$signal_events"; then
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
grep -qx 'result=failed' "$signal_status" || die 'signalled status is not failed'
grep -qx 'exit_code=143' "$signal_status" || die 'signalled status lost exit 143'
grep -qx 'phase=waiting-for-exact-mac' "$signal_status" || \
	die 'signalled failure phase is not exact-MAC wait'
grep -qx 'collector_invocations=0' "$signal_status" || \
	die 'collector ran before the watcher was signalled'
grep -qx 'last_detail=received-signal-TERM' "$signal_status" || \
	die 'signalled status lost the TERM attribution'
[[ ! -e "$signal_output/runtime.txt" && ! -L "$signal_output/runtime.txt" ]] || \
	die 'runtime capture exists after signalled exact-MAC wait'

set +e
PATH="$fake_bin:$PATH" expect "$control/send-ctrl-c.exp" \
	"$watcher" "$int_output" "$expected_sha256" "$int_output/events.txt" \
	>"$control/int.stdout" 2>"$control/int.stderr"
int_rc=$?
set -e
[[ "$int_rc" == 130 ]] || die "Ctrl-C watcher exit was $int_rc, expected 130"
int_status="$int_output/status.env"
[[ -f "$int_status" && ! -L "$int_status" ]] || \
	die 'Ctrl-C watcher did not preserve failure status.env'
grep -qx 'result=failed' "$int_status" || die 'Ctrl-C status is not failed'
grep -qx 'exit_code=130' "$int_status" || die 'Ctrl-C status lost exit 130'
grep -qx 'phase=waiting-for-exact-mac' "$int_status" || \
	die 'Ctrl-C failure phase is not exact-MAC wait'
grep -qx 'collector_invocations=0' "$int_status" || \
	die 'collector ran before the foreground watcher received Ctrl-C'
grep -qx 'last_detail=received-signal-INT' "$int_status" || \
	die 'Ctrl-C status lost the INT attribution'
[[ ! -e "$int_output/runtime.txt" && ! -L "$int_output/runtime.txt" ]] || \
	die 'runtime capture exists after foreground Ctrl-C'

printf 'validation=candidate-ah-collect-cycle-no-interface\n'
printf 'watcher_exit=2\n'
printf 'signalled_watcher_exit=143\n'
printf 'ctrl_c_watcher_exit=130\n'
printf 'collector_invocations=0\n'
printf 'runtime_capture=absent\n'
printf 'device_access=none-ifconfig-and-ioreg-mocked\n'
