#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline successor of the consumed P2E client; no runtime is admitted here."""
import runpy
from pathlib import Path

NS = 1_000_000_000
MARGIN_NS = 30 * NS
# The whole existing USB control call is bounded to 15 seconds. Reserve that
# whole bound between precheck and eligibility expiry, including <=1s drift.
CONTROL_NS = 15 * NS


def disconnect_window(end_ns, now_ns, *, margin_ns=MARGIN_NS):
    if not isinstance(end_ns, int) or end_ns < 600 * NS:
        raise ValueError('no completed ten-minute stream endpoint')
    upper = end_ns + margin_ns
    if margin_ns <= CONTROL_NS + NS:
        raise ValueError('disconnect precheck can expire with <=1s drift')
    if not end_ns <= now_ns <= upper - CONTROL_NS:
        raise ValueError('disconnect window unreachable from observed schedule')
    return end_ns, upper


def client():
    """Derive a reviewable helper without changing any consumed input or pin."""
    here = Path(__file__).resolve().parent
    p2e = runpy.run_path(str(here / 'p2-evidence-successor.py'))
    s = p2e['client']((here / 'laptop-wifi-ssh-connected.py').read_text())
    replace = p2e['literal']
    s = replace(s, 'import time\n', 'import time\nimport runpy\n')
    s = replace(s, 'HERE = Path(__file__).resolve().parent',
                "HERE = Path(__file__).resolve().parent\n"
                "_WINDOW = runpy.run_path(str(HERE / 'disconnect-window.py'))\n"
                "disconnect_window = _WINDOW['disconnect_window']\n"
                "disconnect_refusal = _WINDOW['disconnect_refusal']\n"
                "CONTROL_NS = _WINDOW['CONTROL_NS']")
    s = replace(s, 'def disconnect_argument(boot, pm, early_abort=False):',
                'def disconnect_argument(boot, pm, early_abort=False, bounds=None):')
    # Freeze exact integer bounds into the remote script; remote live identity,
    # PM clock, data-window, fatal-state and one-request guards remain intact.
    s = replace(s, "    return r'''set -eu", "    script = r'''set -eu")
    anchor = "        'PM_VALUE', str(pm)).replace('FATAL_PATTERN', shlex.quote(M.FATAL_RE))"
    s = replace(s, anchor, anchor + '''
    if bounds is not None:
        lower, upper = bounds
        script = script.replace('604000000000', str(lower))
        script = script.replace('608000000000', str(upper))
    return script''')
    s = replace(s, "        control['precheck_pm_offset_ns'] = now - pm", '''        upper = 608_000_000_000
        if not early_abort:
            lower, upper = disconnect_window(stream['pm_offsets_ns'][-1], now - pm)
        control['stream_end_pm_ns'] = stream.get('pm_offsets_ns', [None])[-1]
        control['precheck_pm_offset_ns'] = now - pm''')
    s = replace(s, "control['precheck_interval_ns'] = [lower, 608_000_000_000]",
                "control['precheck_interval_ns'] = [lower, upper-(0 if early_abort else CONTROL_NS)]\n"
                "        control['request_interval_ns'] = [lower, upper]")
    s = replace(s, 'if pm+lower <= now <= pm+608_000_000_000 and monotonic() < started+poll-15:',
                'if pm+lower <= now <= pm+upper-(0 if early_abort else CONTROL_NS) and monotonic() < started+poll-(15 if early_abort else 30):')
    s = replace(s, 'disconnect_argument(boot, pm, early_abort)',
                'disconnect_argument(boot, pm, early_abort, (lower, upper))')
    s = replace(s, 'p2e_disconnect_refusal(raw, response.returncode, boot, lower)',
                'disconnect_refusal(raw, response.returncode, boot, lower, upper)')
    s = replace(s, 'lower <= int(before[1]) <= 608_000_000_000',
                'lower <= int(before[1]) <= upper')
    s = replace(s, 'int(before[1]) <= int(after[1]) <= 613_000_000_000',
                'int(before[1]) <= int(after[1]) <= upper+5_000_000_000')
    compile(s, '<offline disconnect-window successor>', 'exec')
    return s


def disconnect_refusal(raw, code, boot, lower, upper):
    import re
    if code != 49:
        return {}
    m = re.fullmatch(rb'P2_DISCONNECT_REFUSED boot=' + re.escape(boot.encode()) +
                     rb' before_pm_offset_ns=(-?[0-9]+) lower_ns=([0-9]+) upper_ns=([0-9]+)\n', raw)
    if not m or (int(m[2]), int(m[3])) != (lower, upper):
        return {'pm_interval_refusal_observed': False}
    offset = int(m[1])
    return {'pm_interval_refusal_observed': True, 'refused_pm_offset_ns': offset,
            'refused_interval_ns': [lower, upper],
            'refusal_outside_interval': not lower <= offset <= upper}
