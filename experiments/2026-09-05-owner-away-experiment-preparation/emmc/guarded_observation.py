# SPDX-License-Identifier: MIT
"""Inert generation of the fixed eMMC logger guard and observation dispatch.

No files, credentials, processes or transports are opened. The caller supplies
the already generated, source-pinned baseline program; admissions cannot supply
shell fragments. Generated programs remain subject to separate physical gates.
"""
import re

SHA = re.compile(r'[0-9a-f]{64}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
RELEASE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,127}')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(value):
    require(type(value) is str and SHA.fullmatch(value), 'member digest')
    return value


def observer_guard(candidate):
    lines = ['BB=/bin/busybox']
    for member in ('bin/busybox', 'bin/emmc-observe', 'bin/kmsg-capture'):
        value = digest(candidate['members'][member]['sha256'])
        lines += [f'h=$($BB sha256sum /{member}) || exit 1', f'[ "${{h%% *}}" = {value} ] || exit 1']
    # A live precondition only. Full sequence-zero-through-seal evidence is
    # independently required; this neither seals nor restarts the logger.
    lines += ['for path in /run/a53/kmsg.status /run/a53/kmsg-exit; do',
              '  [ ! -e "$path" ] && [ ! -L "$path" ] || exit 1', 'done',
              '[ -f /run/a53/kmsg.log ] && [ ! -L /run/a53/kmsg.log ] || exit 1',
              '[ -f /run/a53/kmsg-pid ] && [ ! -L /run/a53/kmsg-pid ] || exit 1',
              'pid=$($BB cat /run/a53/kmsg-pid) || exit 1',
              'case "$pid" in ""|0*|1|*[!0-9]*) exit 1;; esac',
              '[ "${#pid}" -le 10 ] || exit 1',
              'held=$($BB stat -Lc "%d:%i" "/proc/$pid/exe") || exit 1',
              'expected=$($BB stat -Lc "%d:%i" /bin/kmsg-capture) || exit 1',
              '[ "$held" = "$expected" ] || exit 1']
    return ('\n'.join(lines) + '\n').encode()


def script_for(prepared, phase, boot, baseline_script, release):
    require(phase in ('pre', 'read', 'post'), 'observation phase')
    require(type(baseline_script) is bytes and len(baseline_script) <= 65536, 'baseline program bytes/bound')
    require(type(release) is str and RELEASE.fullmatch(release), 'safe kernel release token')
    require(boot is None or type(boot) is str and UUID.fullmatch(boot), 'boot UUID')
    candidate = prepared['candidate']
    prefix = observer_guard(candidate)
    if phase in ('pre', 'post'):
        require(baseline_script, 'baseline program required')
        return prefix + baseline_script
    require(type(boot) is str and UUID.fullmatch(boot), 'read boot UUID')
    padded = digest(candidate['files']['boot2-padded.img'])
    busybox = digest(candidate['members']['bin/busybox']['sha256'])
    return prefix + (f'exec /bin/busybox sh /bin/emmc-observe {boot} {release} {padded} {busybox}\n').encode()
