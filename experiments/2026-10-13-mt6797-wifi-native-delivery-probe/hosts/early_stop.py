#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""An endpoint that stops before its last chunk records why, the measurement
carries the stop, and the classifier names it as the fault.

usage: early_stop.py <work-dir>   (after bind rendered hosts/; before prepare)

Boot H's first run ended after one transmit chunk with the endpoint reporting
completed=false, errors=0, no receive chunks, and the classifier reading
measurement_censored=true with fault=false: the silent-leg class. A run that
ends early must say where and why.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
literal(h, """                if connection is None:
                    if self.cancel.is_set(): return
                    raise TimeoutError('measurement accept deadline')
""", """                if connection is None:
                    if self.cancel.is_set():
                        self.result['stopped'] = {'after_chunk': ordinal - 1, 'reason': 'cancelled while waiting for the device to open chunk %d' % ordinal}
                        return
                    raise TimeoutError('measurement accept deadline')
""")
literal(h, """                    if self.cancel.is_set(): return
                    if not count: raise ValueError('empty chunk; later traffic withheld')
""", """                    if self.cancel.is_set():
                        self.result['stopped'] = {'after_chunk': ordinal, 'reason': 'cancelled after chunk %d' % ordinal}
                        return
                    if not count: raise ValueError('empty chunk; later traffic withheld')
""")
literal(h, """    result['throughput_measurement'] = {'directions':measured,""",
        """    stops = {k: v.get('stopped') for k, v in measured.items() if v.get('stopped')}
    exits = {k: [c.get('device_exit') for c in v.get('chunks', []) if c.get('device_exit') not in (None, 0, 124, 143)] for k, v in measured.items()}
    early_stop = ({'endpoints': stops, 'device_chunk_exits': {k: e for k, e in exits.items() if e},
                   'reason': '; '.join('%s: %s' % (k, s['reason']) for k, s in stops.items())} if stops else None)
    result['throughput_measurement'] = {'early_stop':early_stop,'directions':measured,""")
compile(h.read_text(), str(h), 'exec')
c = work / 'hosts/classify-throughput.py'
literal(c, """                 measurement_short_by=None if timing and declared == 5 else ('declaration' if timing else 'fault'),
""", """                 measurement_short_by=None if timing and declared == 5 else ('declaration' if timing else 'fault'),
                 measurement_fault_reason=(measurement.get('early_stop') or {}).get('reason'),
""")
compile(c.read_text(), str(c), 'exec')
print('early stop: endpoints record why they stopped; the measurement and the classifier carry the reason')
