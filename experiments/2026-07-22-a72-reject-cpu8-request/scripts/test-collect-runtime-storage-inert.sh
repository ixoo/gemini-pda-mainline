#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }

for command in awk bash cat chmod dirname grep mkdir mktemp python3 rm stat; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
private_root="$repo_root/artifacts/runtime-captures"
expected_sha256=8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257
control="$(mktemp -d /tmp/candidate-aj-runtime-storage-inert.XXXXXX)"
fake_bin="$control/bin"
output_dir="$private_root/aj-runtime-storage-inert-selftest-$$-$RANDOM"
output="$output_dir/runtime.txt"
wrong_output_dir="$private_root/aj-runtime-wrong-hash-selftest-$$-$RANDOM"
wrong_output="$wrong_output_dir/runtime.txt"
runtime_fixture="$control/runtime-fixture"
command_capture="$control/device-command.txt"
nc_count="$control/nc-count"
host_tool_count="$control/host-tool-count"

cleanup() {
	local candidate
	for candidate in "$output_dir" "$wrong_output_dir"; do
		if [[ -d "$candidate" && ! -L "$candidate" && \
			"$(dirname -- "$candidate")" == "$private_root" && \
			"$(basename -- "$candidate")" == aj-runtime-*-selftest-* ]]; then
			rm -r -- "$candidate"
		fi
	done
	[[ ! -d "$control" ]] || rm -r -- "$control"
}
trap cleanup EXIT

[[ -f "$collector" && ! -L "$collector" ]] || die 'AJ collector is absent or unsafe'
[[ -d "$private_root" && ! -L "$private_root" ]] || die 'private capture root is absent'
[[ ! -e "$output_dir" && ! -L "$output_dir" ]] || die 'self-test output collision'
[[ ! -e "$wrong_output_dir" && ! -L "$wrong_output_dir" ]] || \
	die 'wrong-hash self-test output collision'

mkdir -m 0700 "$fake_bin"
cat >"$fake_bin/ifconfig" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_HOST_TOOL_COUNT:?}"
printf 'ifconfig\n' >>"$AJ_TEST_HOST_TOOL_COUNT"
[[ "${1:-}" == en99 ]] || exit 1
printf 'en99: flags=8863<UP,BROADCAST,RUNNING> mtu 1500\n'
printf '\tinet 10.15.19.1 netmask 0xffffff00 broadcast 10.15.19.255\n'
printf '\tether 42:00:15:19:82:00\n'
EOF
cat >"$fake_bin/route" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_HOST_TOOL_COUNT:?}"
printf 'route\n' >>"$AJ_TEST_HOST_TOOL_COUNT"
printf '   route to: 10.15.19.82\n'
printf '  interface: en99\n'
EOF
cat >"$fake_bin/ping" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_HOST_TOOL_COUNT:?}"
printf 'ping\n' >>"$AJ_TEST_HOST_TOOL_COUNT"
exit 0
EOF
cat >"$fake_bin/nc" <<'EOF'
#!/usr/bin/env bash
: "${AJ_TEST_COMMAND_CAPTURE:?}"
: "${AJ_TEST_NC_COUNT:?}"
: "${AJ_TEST_RUNTIME_FIXTURE:?}"
count=0
if [[ -f "$AJ_TEST_NC_COUNT" ]]; then
	read -r count <"$AJ_TEST_NC_COUNT"
fi
printf '%s\n' "$((count + 1))" >"$AJ_TEST_NC_COUNT"
cat >"$AJ_TEST_COMMAND_CAPTURE"
cat "$AJ_TEST_RUNTIME_FIXTURE"
EOF
chmod 0700 "$fake_bin/ifconfig" "$fake_bin/route" "$fake_bin/ping" "$fake_bin/nc"

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


validator = load(script_dir / "validate-runtime.py", "aj_storage_inert_validator")
tests = load(script_dir / "test-runtime-validator.py", "aj_storage_inert_fixture")
fixture = tests.fixture(validator)
separator = "__AJ_HOST_END__\r\n"
if fixture.count(separator) != 1:
    raise RuntimeError("runtime fixture host separator changed")
output.write_bytes(fixture.split(separator, 1)[1].encode("utf-8"))
PY

export AJ_TEST_COMMAND_CAPTURE="$command_capture"
export AJ_TEST_NC_COUNT="$nc_count"
export AJ_TEST_RUNTIME_FIXTURE="$runtime_fixture"
export AJ_TEST_HOST_TOOL_COUNT="$host_tool_count"

# The installed-image identity gate precedes output-path inspection and all
# mocked host/network probes.
set +e
PATH="$fake_bin:$PATH" bash "$collector" --interface en99 \
	--output "$wrong_output" \
	--installed-full-sha256 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
	>"$control/wrong-hash.stdout" 2>"$control/wrong-hash.stderr"
wrong_hash_rc=$?
set -e
[[ "$wrong_hash_rc" == 2 ]] || die "wrong-hash collector exit was $wrong_hash_rc"
grep -q 'installed full-partition checksum is not Candidate AJ' \
	"$control/wrong-hash.stderr" || die 'collector accepted a different image hash'
[[ ! -e "$wrong_output_dir" && ! -L "$wrong_output_dir" ]] || \
	die 'wrong installed-image hash touched the capture path'
[[ ! -e "$host_tool_count" && ! -e "$nc_count" ]] || \
	die 'wrong installed-image hash reached a mocked host or network tool'

mkdir -m 0700 "$output_dir"
PATH="$fake_bin:$PATH" bash "$collector" --interface en99 --output "$output" \
	--installed-full-sha256 "$expected_sha256" \
	>"$control/success.stdout" 2>"$control/success.stderr"

[[ -f "$output" && ! -L "$output" ]] || die 'collector omitted runtime capture'
[[ -f "$command_capture" && ! -L "$command_capture" ]] || \
	die 'mock transport omitted its command capture'
[[ "$(cat "$nc_count")" == 1 ]] || die 'runtime collector opened more than one session'
[[ "$(stat -f '%Lp' "$output" 2>/dev/null || stat -c '%a' "$output")" == 600 ]] || \
	die 'runtime capture mode is not 0600'

for section in HOST IDENTITY STAT1 STAT2 STABILITY DMESG; do
	grep -aFq "__AJ_${section}_BEGIN__" "$output" || die "missing AJ $section section"
	grep -aFq "__AJ_${section}_END__" "$output" || die "incomplete AJ $section section"
done
grep -aFq "installed_full_sha256_input=$expected_sha256" "$output" || \
	die 'runtime capture lost installed-image attestation'
grep -aFq 'device_partition_read_during_collection=no' "$output" || \
	die 'runtime capture lost its no-partition-read attestation'

if grep -Eq '(^|[;&|[:space:]])(reboot|poweroff|shutdown|halt|dd|mount|umount)([;&|[:space:]]|$)' \
	"$command_capture"; then
	die 'runtime command requested a reboot, power, mount, or block-copy operation'
fi
if grep -Eq '/dev/(mmc|watchdog)|(^|[;&|[:space:]])(tee|chattr)([;&|[:space:]]|$)' \
	"$command_capture"; then
	die 'runtime command referenced device storage/watchdog or a write helper'
fi
if grep -Eq '(>|>>)[[:space:]]*/sys/devices/system/cpu|tee[[:space:]]+/sys/devices/system/cpu' \
	"$command_capture"; then
	die 'runtime command requested a CPU sysfs write'
fi
grep -Fq "if [ -e \"/sys/devices/system/cpu/cpu\$1/online\" ]" \
	"$command_capture" || die 'runtime command lost its read-only CPU control probe'

printf 'validation=candidate-aj-collect-runtime-storage-inert\n'
printf 'runtime_validator=passed\n'
printf 'runtime_sections=AJ-host-identity-stat1-stat2-stability-dmesg\n'
printf 'stability_window=45-plus-5-seconds\n'
printf 'transport_sessions=one\n'
printf 'partition_reads=none\n'
printf 'device_writes=none\n'
printf 'reboot_requests=none\n'
printf 'device_access=none-network-tools-mocked\n'
