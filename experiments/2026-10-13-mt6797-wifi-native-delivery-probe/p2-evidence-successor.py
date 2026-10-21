#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P2E host evidence corrections; consumed P2 inputs and device limits stay pinned."""
import hashlib
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
PINS = {'laptop-capture-ccmp-p2.py': '22df3dceee3b50c278f6bf68805f805379a37067228a1d64fa6618d1cdb8a878',
 'laptop-session-ccmp-p2.py': '3c89d332087c73c35c8c157f17628a0ffa44238f8159e9e75b13942e00496eb5',
 'laptop-wifi-ssh-connected-p2.py': '5d25538b7a13f8809fe6a2e87fee4f3772a5d3a658625135b7a194299ea828ef',
 'laptop-wifi-ssh-connected.py': '31b65043570988dc3f9d06cd3269cd98e9c8015d48f45bc6fa838c7b20d4b3bf',
 'passive-host-ccmp-p2.py': '2965249eeaa61fb460761db39c709c03ae92bd17d5da97d734c940242634e471',
 'prepare-ccmp-p2.py': 'a67e17b2818fb58821d674e71a963f0187f551ece62bd39108818de44844c15c',
 'ten-minute-envelope.py': 'dbafdb83b95edf261a99fe118cabe1cbdf799d9e4a949cdcd1f809691d27da62'}


def checked(name, source):
    if hashlib.sha256(source.encode()).hexdigest() != PINS[name]:
        raise ValueError('reviewed P2 source changed: ' + name)
    return source


def literal(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError('P2E source anchor changed: ' + old)
    return source.replace(old, new)


def disconnect_refusal(raw, code, boot, lower):
    """Retain a refused guard's existing scalar; never turn it into acceptance."""
    if code != 49:
        return {}
    match = re.fullmatch(
        rb'P2_DISCONNECT_REFUSED boot=' + re.escape(boot.encode()) +
        rb' before_pm_offset_ns=(-?[0-9]+) lower_ns=([0-9]+) upper_ns=([0-9]+)\n', raw)
    if not match or int(match[2]) != lower or int(match[3]) != 608_000_000_000:
        return {'pm_interval_refusal_observed': False}
    offset = int(match[1])
    return {'pm_interval_refusal_observed': True,
            'refused_pm_offset_ns': offset,
            'refused_interval_ns': [lower, 608_000_000_000],
            'refusal_outside_interval': not lower <= offset <= 608_000_000_000}


def client(source):
    checked('ten-minute-envelope.py', (HERE / 'ten-minute-envelope.py').read_text())
    p2 = runpy.run_path(str(HERE / 'ten-minute-envelope.py'))
    checked('laptop-wifi-ssh-connected.py', source)
    # Keep all old derivation checks, including the original helper identity.
    source = p2['helper'](source)
    source = literal(source, "SESSION = 'session-ccmp-p2'", "SESSION = 'session-ccmp-p2e'")
    source = literal(source, 'if len(ticks) < 244:', 'if len(ticks) < 603:')
    source = literal(source,
        '[ "$o" -ge LOWER_BOUND ] && [ "$o" -le 608000000000 ] || exit 49',
        'if ! { [ "$o" -ge LOWER_BOUND ] && [ "$o" -le 608000000000 ]; }; then\n'
        '    printf \'P2_DISCONNECT_REFUSED boot=%s before_pm_offset_ns=%s lower_ns=%s upper_ns=608000000000\\n\' BOOT_VALUE "$o" LOWER_BOUND\n'
        '    exit 49\nfi')
    source = literal(source,
        "        control['kind'] = 'abort_after_incomplete_stream' if early_abort else 'after_completed_stream'",
        "        control['kind'] = 'abort_after_incomplete_stream' if early_abort else 'after_completed_stream'\n"
        "        control['precheck_pm_offset_ns'] = now - pm\n"
        "        control['precheck_interval_ns'] = [lower, 608_000_000_000]")
    source = literal(source,
        "                control.update(exit=response.returncode, stderr_bytes=len(response.stderr))",
        "                control.update(exit=response.returncode, stderr_bytes=len(response.stderr))\n"
        "                control.update(p2e_disconnect_refusal(raw, response.returncode, boot, lower))")
    source = literal(source,
        "    result['p2_60s_budget_pass_claimed'] = False",
        "    result['p2_60s_budget_pass_claimed'] = False\n"
        "    result['p2e_evidence'] = {'receive_timestamp_cap': 603, 'kernel_unchanged': True}")
    compile(source, '<P2E host evidence>', 'exec')
    return source


def host(source, client_sha):
    source = checked('passive-host-ccmp-p2.py', source)
    source = literal(source, 'laptop-wifi-ssh-connected-p2.py',
                     'laptop-wifi-ssh-connected-p2e.py', 2)
    source = literal(source, PINS['laptop-wifi-ssh-connected-p2.py'], client_sha)
    return fresh_roots(source)


def fresh_roots(source):
    source = literal(source, 'session-ccmp-p2', 'session-ccmp-p2e')
    return literal(source, 'capture-ccmp-p2', 'capture-ccmp-p2e')


def session(source):
    source = checked('laptop-session-ccmp-p2.py', source)
    return literal(source, 'passive-host-ccmp-p2.py', 'passive-host-ccmp-p2e.py')


def prepare(source):
    return fresh_roots(checked('prepare-ccmp-p2.py', source))


def capture(source):
    return fresh_roots(checked('laptop-capture-ccmp-p2.py', source))
