# SPDX-License-Identifier: MIT
"""Add the reviewed block-identity guard to the V4 installer derivation only."""
import hashlib

GUARD_SHA256 = '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf'


def derive(source, guard):
    if hashlib.sha256(guard).hexdigest() != GUARD_SHA256:
        raise ValueError('shared boot2 guard identity changed')
    guard = guard.decode()
    begin = '# BOOT2_DEVICE_GUARD_LIBRARY_BEGIN\n'
    end = '# BOOT2_DEVICE_GUARD_LIBRARY_END\n'
    if guard.count(begin) != 1 or guard.count(end) != 1:
        raise ValueError('guard library boundaries')
    library = guard.split(begin)[1].split(end)[0]

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('installer guard anchor changed: ' + old[:60])
        source = source.replace(old, new)

    replace("fail() { printf 'error: %s\\n' \"$*\" >&2; exit 2; }\n",
            "fail() { printf 'error: %s\\n' \"$*\" >&2; exit 2; }\n" + library + r'''
guard_field() {
    local value
    value=$(printf '%s\n' "$2" | awk -F= -v key="$1" '$1 == key {if (NF != 2 || $2 == "") exit 2; value=$2; n++} END {if (n != 1) exit 2; print value}') || return 1
    [[ -n "$value" ]] || return 1
    printf '%s\n' "$value"
}
''')
    start = 'root="$(readlink -f "$(findmnt -n -o SOURCE /)")"\n'
    finish = 'done <<<"$(swapon --noheadings --raw --show=NAME)"\n'
    if source.count(start) != 1 or source.count(finish) != 1:
        raise ValueError('old root gate boundaries')
    old = start + source.split(start)[1].split(finish)[0] + finish
    replace(old, r'''majmin="$(lsblk -dnro MAJ:MIN "$target")"
guard_output=$(boot2_device_guard "$target" "$majmin") || fail 'block identity guard refused'
[[ "$(guard_field boot2_device_guard "$guard_output")" == passed ]] || fail 'guard result missing'
[[ "$(guard_field target_device "$guard_output")" == "$target" &&
   "$(guard_field target_major_minor "$guard_output")" == "$majmin" ]] || fail 'guard target disagrees'
root=$(guard_field root_device "$guard_output") || fail 'guard root missing'
root_major_minor=$(guard_field root_major_minor "$guard_output") || fail 'guard root number missing'
[[ -z "$EXPECTED_ROOT_NUMBER" || "$root_major_minor" == "$EXPECTED_ROOT_NUMBER" ]] || fail 'root changed across deployment stages'
[[ -z "$EXPECTED_TARGET_NUMBER" || "$majmin" == "$EXPECTED_TARGET_NUMBER" ]] || fail 'target changed across deployment stages'
''')
    replace("EXPECTED_STAGE='$expected_stage' /bin/bash -s",
            "EXPECTED_STAGE='$expected_stage' EXPECTED_ROOT_NUMBER='${live_root_number:-}' EXPECTED_TARGET_NUMBER='${live_target_number:-}' /bin/bash -s")
    write = '\tdd if="$EXPECTED_STAGE" of="$target" bs=4M iflag=fullblock count=4 conv=fsync,notrunc status=none\n'
    replace(write, '\tboot2_device_guard "$target" "$majmin" "$root_major_minor" >/dev/null || fail \'pre-write block identity changed\'\n' + write)
    replace("printf 'gate=passed\\nmode=%s\\ntarget=%s\\nroot=%s\\n'",
            "printf '%s\\n' \"$guard_output\"\nprintf 'gate=passed\\nmode=%s\\ntarget=%s\\nroot=%s\\n'")
    anchor = 'live_target="$(single_value target "$probe_output")" || die \'invalid target evidence\'\n'
    replace(anchor, anchor + '''live_root="$(single_value root_device "$probe_output")" || die 'invalid root evidence'
live_root_number="$(single_value root_major_minor "$probe_output")" || die 'invalid root number evidence'
live_target_number="$(single_value target_major_minor "$probe_output")" || die 'invalid target number evidence'
[[ "$live_root" =~ ^/dev/[A-Za-z0-9_.-]+$ && "$live_root_number" =~ ^[1-9][0-9]{0,3}:[0-9]{1,7}$ &&
   "$live_target_number" =~ ^[1-9][0-9]{0,3}:[0-9]{1,7}$ && "$live_root_number" != "$live_target_number" ]] ||
    die 'unsafe block identity evidence'
''')
    replace("printf 'result=%s\\ntarget_logical_name=boot2\\ntarget=%s\\nroot=/dev/mmcblk0p29\\n' \"$result\" \"$live_target\"",
            "printf 'result=%s\\ntarget_logical_name=boot2\\ntarget=%s\\nroot=%s\\n' \"$result\" \"$live_target\" \"$live_root\"\n" +
            "\tprintf 'boot2_device_guard=passed\\nboot2_device_guard_sha256=" + GUARD_SHA256 + "\\ntarget_major_minor=%s\\nroot_major_minor=%s\\n' \"$live_target_number\" \"$live_root_number\"")
    return source
