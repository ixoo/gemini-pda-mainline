#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk bash chmod cp git grep mkdir mktemp python3 rm shasum stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
watcher="$script_dir/collect-unit-bound-cycle.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
expected_boot_id=01234567-89ab-cdef-0123-456789abcdef
control="$(mktemp -d /tmp/candidate-aj-unit-cycle.XXXXXX)"
control="$(cd -- "$control" && pwd -P)"
fake_bin="$control/bin"
success_output="$private_root/aj-unit-success-selftest-$$-$RANDOM"
return_output="$private_root/aj-unit-return-selftest-$$-$RANDOM"
reject_output="$private_root/aj-unit-reject-selftest-$$-$RANDOM"
runtime_fixture="$control/runtime-fixture"

cleanup() {
	local path
	for path in "$success_output" "$return_output" "$reject_output"; do
		if [[ -d "$path" && ! -L "$path" && "$(dirname -- "$path")" == "$private_root" &&
			"$(basename -- "$path")" == aj-unit-*-selftest-* ]]; then
			rm -r -- "$path"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -f "$watcher" && ! -L "$watcher" ]] || die 'unit-bound watcher is absent or unsafe'
mkdir -m 0700 "$fake_bin"

cat >"$fake_bin/ssh" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_SSH_COUNT:?}"
: "${AJ_TEST_SSH_MODE:?}"
cat >/dev/null
count=0
[[ ! -f "$AJ_TEST_SSH_COUNT" ]] || read -r count <"$AJ_TEST_SSH_COUNT"
count=$((count + 1))
printf '%s\n' "$count" >"$AJ_TEST_SSH_COUNT"
exact_state() {
	printf 'kernel=3.18.41+\narchitecture=aarch64\nroot_source=/dev/mmcblk0p29\n'
	printf 'boot_id=01234567-89ab-cdef-0123-456789abcdef\n'
}
case "$AJ_TEST_SSH_MODE" in
success-down) ((count <= 2)) && exact_state || exit 255 ;;
never-disconnect|early-mac) exact_state ;;
source-return)
	if ((count <= 2 || count >= 7)); then exact_state; else exit 255; fi
	;;
mutate-key)
	if ((count <= 2)); then
		exact_state
	else
		: "${AJ_TEST_MUTATE_KEY:?}"
		printf 'rotation-during-gate\n' >>"$AJ_TEST_MUTATE_KEY"
		exit 255
	fi
	;;
*) exit 96 ;;
esac
EOF

cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_USB_MODE:?}"
: "${AJ_TEST_SSH_COUNT:?}"
: "${AJ_TEST_DELEGATED:?}"
: "${AJ_TEST_USB_COUNT:?}"
: "${AJ_TEST_READY:?}"

list_interfaces() {
	local count=0 ssh_count=0
	case "$AJ_TEST_USB_MODE" in
	exact-already) printf 'en99\n' ;;
	ambiguous) printf 'en97 en99\n' ;;
	stale-address|stale-route|wrong-only) printf 'en98\n' ;;
	early)
		[[ ! -f "$AJ_TEST_SSH_COUNT" ]] || read -r ssh_count <"$AJ_TEST_SSH_COUNT"
		if ((ssh_count >= 3)); then printf 'en99\n'; else printf 'en98\n'; fi
		;;
	success)
		if [[ ! -f "$AJ_TEST_DELEGATED" ]]; then
			printf 'en98\n'
		else
			[[ ! -f "$AJ_TEST_USB_COUNT" ]] || read -r count <"$AJ_TEST_USB_COUNT"
			count=$((count + 1)); printf '%s\n' "$count" >"$AJ_TEST_USB_COUNT"
			if ((count >= 5)); then : >"$AJ_TEST_READY"; printf 'en98 en99\n'; else printf 'en98\n'; fi
		fi
		;;
	*) exit 95 ;;
	esac
}

show_interface() {
	case "$1:$AJ_TEST_USB_MODE" in
	en97:ambiguous|en99:ambiguous|en99:exact-already|en99:early)
		printf '%s: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n' "$1"
		printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
		printf '\tether 42:00:15:19:82:00\n'
		;;
	en99:success)
		[[ -f "$AJ_TEST_READY" ]] || exit 1
		printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
		printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
		printf '\tether 42:00:15:19:82:00\n'
		;;
	en98:stale-address)
		printf 'en98: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
		printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
		printf '\tether 02:00:00:00:00:98\n'
		;;
	en98:*)
		printf 'en98: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
		printf '\tether 02:00:00:00:00:98\n'
		;;
	*) exit 1 ;;
	esac
}

case "${1:-}" in
-l) list_interfaces ;;
-a)
	for interface in $(list_interfaces); do show_interface "$interface" || true; done
	;;
en97|en98|en99) show_interface "$1" ;;
*) exit 1 ;;
esac
EOF

cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_USB_MODE:?}"
: "${AJ_TEST_READY:?}"
if [[ "$AJ_TEST_USB_MODE" == stale-route ]]; then
	interface=en98
elif [[ -f "$AJ_TEST_READY" ]]; then
	interface=en99
else
	exit 1
fi
printf '   route to: 10.15.19.82\n'
printf '  interface: %s\n' "$interface"
EOF

cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_READY:?}"
[[ -f "$AJ_TEST_READY" ]]
EOF

cat >"$fake_bin/ioreg" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_DELEGATED:?}"
: "${AJ_TEST_READY:?}"
: >"$AJ_TEST_DELEGATED"
printf 'USB Serial Number = DO-NOT-PERSIST-PLAINTEXT-SERIAL\n'
[[ ! -f "$AJ_TEST_READY" ]] || \
	printf 'USB Serial Number = GEMINI_OBSERVABILITY_20260717_L\n'
EOF

cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_NC_COUNT:?}"
: "${AJ_TEST_RUNTIME_FIXTURE:?}"
count=0
[[ ! -f "$AJ_TEST_NC_COUNT" ]] || read -r count <"$AJ_TEST_NC_COUNT"
printf '%s\n' "$((count + 1))" >"$AJ_TEST_NC_COUNT"
cat "$AJ_TEST_RUNTIME_FIXTURE"
EOF
chmod 0700 "$fake_bin/ssh" "$fake_bin/ifconfig" "$fake_bin/route" \
	"$fake_bin/ping" "$fake_bin/ioreg" "$fake_bin/nc"

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

validator = load(script_dir / "validate-runtime.py", "aj_unit_cycle_validator")
tests = load(script_dir / "test-runtime-validator.py", "aj_unit_cycle_fixture")
fixture = tests.fixture(validator)
separator = "__AJ_HOST_END__\r\n"
if fixture.count(separator) != 1:
    raise RuntimeError("runtime fixture host separator changed")
output.write_bytes(fixture.split(separator, 1)[1].encode("utf-8"))
PY

ssh_count="$control/ssh-count"
usb_count="$control/usb-count"
delegated="$control/delegated"
ready="$control/ready"
nc_count="$control/nc-count"
export AJ_TEST_SSH_COUNT="$ssh_count" AJ_TEST_USB_COUNT="$usb_count"
export AJ_TEST_DELEGATED="$delegated" AJ_TEST_READY="$ready"
export AJ_TEST_NC_COUNT="$nc_count" AJ_TEST_RUNTIME_FIXTURE="$runtime_fixture"

reset_state() {
	rm -f -- "$ssh_count" "$usb_count" "$delegated" "$ready" "$nc_count"
}

run_reject() {
	local label=$1 expected=$2 output_path=$3
	shift 3
	set +e
	PATH="$fake_bin:$PATH" bash "$watcher" --output "$output_path" \
		--installed-full-sha256 "$expected_sha256" "$@" \
		>"$control/$label.stdout" 2>"$control/$label.stderr"
	rc=$?
	set -e
	[[ "$rc" == 2 ]] || die "$label exit was $rc"
	if ! grep -q -- "$expected" "$control/$label.stderr"; then
		sed -n '1,20p' "$control/$label.stderr" >&2
		die "$label rejection reason changed"
	fi
}

# Wrong image identity is rejected before any transport or evidence path.
wrong_output="$private_root/aj-unit-wrong-selftest-$$-$RANDOM"
set +e
PATH="$fake_bin:$PATH" bash "$watcher" --output "$wrong_output" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	>"$control/wrong.stdout" 2>"$control/wrong.stderr"
wrong_rc=$?
set -e
[[ "$wrong_rc" == 2 && ! -e "$wrong_output" ]] || die 'wrong image identity was not fail-closed'

# Another fixed-MAC unit, two matching interfaces, and stale host network state
# all fail before source probing or runtime collection.
reset_state; export AJ_TEST_USB_MODE=exact-already AJ_TEST_SSH_MODE=never-disconnect
run_reject existing-mac 'fixed MAC is present' "$reject_output" --wait-seconds 3
reset_state; export AJ_TEST_USB_MODE=ambiguous AJ_TEST_SSH_MODE=never-disconnect
run_reject ambiguous 'fixed MAC is present' "$reject_output" --wait-seconds 3
reset_state; export AJ_TEST_USB_MODE=stale-address AJ_TEST_SSH_MODE=never-disconnect
run_reject stale-address 'stale Candidate AJ host address' "$reject_output" --wait-seconds 3
reset_state; export AJ_TEST_USB_MODE=stale-route AJ_TEST_SSH_MODE=never-disconnect
run_reject stale-route 'stale Candidate AJ device route' "$reject_output" --wait-seconds 3
[[ ! -f "$nc_count" ]] || die 'preflight rejection invoked runtime collection'

# A target that stays up cannot be confused with a candidate cycle.
reset_state; export AJ_TEST_USB_MODE=wrong-only AJ_TEST_SSH_MODE=never-disconnect
run_reject never-disconnect 'did not produce two SSH failures' \
	"$reject_output" --wait-seconds 3
[[ ! -f "$nc_count" ]] || die 'never-disconnected target invoked runtime collection'

# The shared fixed MAC appearing before the second source failure is fatal.
reset_state; export AJ_TEST_USB_MODE=early AJ_TEST_SSH_MODE=early-mac
run_reject early-mac 'fixed MAC is present before the exact source disconnect' \
	"$reject_output" --wait-seconds 4
[[ ! -f "$nc_count" ]] || die 'early fixed-MAC appearance invoked runtime collection'

# A source return while the delegated watcher is active invalidates the unit
# binding and terminates it before a runtime session. The wrong-MAC en98
# interface remains present throughout, proving that unrelated USB is not an
# acceptable candidate appearance.
reset_state; export AJ_TEST_USB_MODE=wrong-only AJ_TEST_SSH_MODE=source-return
run_reject source-return 'exact Gemian source returned' "$return_output" --wait-seconds 8
[[ ! -f "$nc_count" ]] || die 'returned source allowed runtime collection'
grep -qx 'unit_binding_status=invalid-source-returned' \
	"$return_output/unit-binding-final.env" || die 'source return was not preserved as invalid'

# Exact source confirmation -> two failures -> clean fixed-MAC appearance is
# the sole successful path. The raw ioreg serial must not reach any evidence.
reset_state; export AJ_TEST_USB_MODE=success AJ_TEST_SSH_MODE=success-down
set +e
PATH="$fake_bin:$PATH" bash "$watcher" --output "$success_output" \
	--installed-full-sha256 "$expected_sha256" --wait-seconds 15 \
	>"$control/success.stdout" 2>"$control/success.stderr"
success_rc=$?
set -e
if ((success_rc != 0)); then
	sed -n '1,80p' "$control/success.stderr" >&2
	die "unit-bound success path exited $success_rc"
fi
[[ -f "$nc_count" && "$(<"$nc_count")" == 1 ]] || die 'unit-bound runtime was not one-shot'
grep -qx 'runtime_subgate=passed' "$success_output/status.env" || \
	die 'unit-bound runtime subgate did not pass'
grep -qx 'source_disconnect_confirmed=yes' "$success_output/unit-binding.env" || \
	die 'source disconnect binding is absent'
grep -qx 'source_state_confirmations=2' "$success_output/unit-binding.env" || \
	die 'exact source was not confirmed twice'
grep -qx 'source_boot_id_recorded=no' "$success_output/unit-binding.env" || \
	die 'source boot ID privacy policy changed'
grep -qx 'ssh_identity_content_recorded=no' "$success_output/unit-binding.env" || \
	die 'SSH identity privacy policy changed'
grep -qx 'unit_binding_status=valid' "$success_output/unit-binding-final.env" || \
	die 'valid final source binding is absent'
grep -qx 'source_unreachable_until_cycle_watcher_exit=yes' \
	"$success_output/unit-binding-final.env" || die 'source reachability final gate is absent'
if grep -R -Fq 'DO-NOT-PERSIST-PLAINTEXT-SERIAL' "$success_output"; then
	die 'raw USB serial reached unit-bound evidence'
fi
grep -qF 'candidate_mainline_marker=GEMINI_OBSERVABILITY_20260717_L' \
	"$success_output/ioreg-ready.txt" || die 'sanitized generic marker state was lost'
grep -qx "runtime_boot_id_before=$expected_boot_id" "$success_output/status.env" || \
	die 'candidate runtime boot ID binding changed'

# Executable pin mutations fail before any target probe. A rotated client key
# is accepted only if it authenticates the exact source; changing it after that
# authenticated boundary is covered by assert_live_pins on every probe.
mutation_repo="$control/mutation-repo"
mutation_scripts="$mutation_repo/experiments/2026-07-22-a72-reject-cpu8-request/scripts"
mkdir -p "$mutation_scripts" "$mutation_repo/artifacts/credentials"
cp "$watcher" "$script_dir/collect-cycle.sh" "$script_dir/candidate_aj.py" \
	"$script_dir/sanitize-unit-bound-ioreg.sh" "$mutation_scripts/"
printf '\n# mutation\n' >>"$mutation_scripts/collect-cycle.sh"
printf 'dummy-private-key\n' >"$mutation_repo/artifacts/credentials/gemini_ed25519"
chmod 0600 "$mutation_repo/artifacts/credentials/gemini_ed25519"
git -C "$mutation_repo" init -q
printf 'artifacts/\n' >"$mutation_repo/.gitignore"
set +e
PATH="$fake_bin:$PATH" bash "$mutation_scripts/collect-unit-bound-cycle.sh" \
	--output artifacts/runtime-captures/mutation \
	--installed-full-sha256 "$expected_sha256" \
	>"$control/mutation.stdout" 2>"$control/mutation.stderr"
mutation_rc=$?
set -e
[[ "$mutation_rc" == 2 ]] || die 'mutated source watcher did not fail closed'
grep -q 'cycle watcher source identity changed' "$control/mutation.stderr" || \
	die 'mutated source watcher rejection reason changed'

key_repo="$control/key-rotation-repo"
key_scripts="$key_repo/experiments/2026-07-22-a72-reject-cpu8-request/scripts"
key_identity="$key_repo/artifacts/credentials/gemini_ed25519"
mkdir -p "$key_scripts" "$key_repo/artifacts/credentials" \
	"$key_repo/artifacts/runtime-captures"
cp "$watcher" "$script_dir/collect-cycle.sh" "$script_dir/candidate_aj.py" \
	"$script_dir/sanitize-unit-bound-ioreg.sh" "$key_scripts/"
printf 'offline-dummy-private-key\n' >"$key_identity"
chmod 0600 "$key_identity"
chmod 0700 "$key_repo/artifacts" "$key_repo/artifacts/credentials" \
	"$key_repo/artifacts/runtime-captures"
git -C "$key_repo" init -q
printf 'artifacts/\n' >"$key_repo/.gitignore"
reset_state
export AJ_TEST_USB_MODE=wrong-only AJ_TEST_SSH_MODE=mutate-key
export AJ_TEST_MUTATE_KEY="$key_identity"
set +e
PATH="$fake_bin:$PATH" bash "$key_scripts/collect-unit-bound-cycle.sh" \
	--output artifacts/runtime-captures/key-rotation \
	--installed-full-sha256 "$expected_sha256" --wait-seconds 5 \
	>"$control/key-rotation.stdout" 2>"$control/key-rotation.stderr"
key_rotation_rc=$?
set -e
unset AJ_TEST_MUTATE_KEY
[[ "$key_rotation_rc" == 2 ]] || die 'mid-gate SSH-key change did not fail closed'
grep -q 'SSH private key changed during the unit-bound gate' \
	"$control/key-rotation.stderr" || die 'mid-gate SSH-key mutation reason changed'

printf 'validation=candidate-aj-unit-bound-cycle\n'
printf 'exact_source_confirmations=2\n'
printf 'disconnect_failures=2-before-fixed-mac\n'
printf 'existing_or_ambiguous_fixed_mac=rejected\n'
printf 'never_disconnected_target=rejected\n'
printf 'unrelated_usb_and_stale_network=rejected\n'
printf 'source_return_during_watch=rejected\n'
printf 'runtime_collection=one-shot-after-unit-binding\n'
printf 'raw_ioreg_and_plaintext_serial=not-persisted\n'
printf 'source_mutation=rejected\n'
printf 'mid_gate_ssh_key_mutation=rejected\n'
printf 'device_access=none-network-tools-mocked\n'
