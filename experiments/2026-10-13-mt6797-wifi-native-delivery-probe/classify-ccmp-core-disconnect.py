#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1: planned core disconnect at PM+55 s, never a full 60 s budget pass."""
import importlib.util
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location('s1_channel_release',
                                            Path(__file__).with_name('classify-ccmp-channel-release.py'))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
read_protocol = BASE.read_protocol


def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    result = BASE.classify(kmsg, ssh_receipt, verified_boot, protocol)
    lines = kmsg.splitlines()
    clocks = [m for line in lines if (m := BASE.CLOCK.search(line))]
    ends = [m for line in lines if (m := BASE.BASE.END.search(line))]
    starts = [m for line in lines if (m := BASE.BASE.START.search(line))]
    beacons = [m for line in lines if (m := re.search(
        rb'one-shot WLAN data-end beacons: observed_ns=(\d+) count=\d+ known=[01] age_ns=\d+ '
        rb'since_pm_known=[01] since_pm=\d+ interval_tu=\d+$', line))]
    receipt = ssh_receipt or {}
    stream, control = receipt.get('s1_stream', {}), receipt.get('s1_core_disconnect', {})
    remote = receipt.get('s1_remote_stream_quiescence', {})
    offset = int(beacons[0][1]) - int(clocks[0][1]) if len(beacons) == len(clocks) == 1 else None
    planned_stop = (len(ends) == len(starts) == 1 and
                    tuple(map(int, starts[0].groups())) == (60000, 5000, 1) and
                    sum(b'one-shot WLAN data-end beacons:' in line for line in lines) == 1 and
                    sum(b'one-shot WLAN join data phase end:' in line for line in lines) == 1 and
                    sum(b'one-shot WLAN join data phase:' in line for line in lines) == 1 and
                    ends[0][1] == b'disconnect' and offset is not None and
                    55_000_000_000 <= offset < 58_000_000_000)
    before, after = control.get('before_pm_offset_ns'), control.get('after_pm_offset_ns')
    attributable = bool(planned_stop and isinstance(before, int) and isinstance(after, int) and
                        before <= offset <= after)
    passed = bool(result['finite_capability_pass'] and result['healthy_cleanup'] and
                  result['connected_channel_release_credited'] and result['periodic_after_release_pass'] and
                  receipt.get('all_pass') is True and stream.get('pass') is True and
                  remote.get('quiesced') is True and
                  control.get('attempted') is True and control.get('accepted') is True and attributable)
    result.update(core_disconnect_trial_pass=passed, planned_stop_pm_offset_ns=55_000_000_000,
                  actual_stop_pm_offset_ns=offset, core_disconnect_planned_stop_observed=planned_stop,
                  ssh_stream=stream, core_disconnect=control, remote_stream_quiescence=remote,
                  provisional_ccmp_compatibility_pass=passed,
                  full_60s_budget_pass_claimed=False)
    return result
