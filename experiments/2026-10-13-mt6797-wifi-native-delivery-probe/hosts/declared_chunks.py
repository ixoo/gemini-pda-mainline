#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the declared-chunk-count reading to a derived work directory's classifier.

usage: declared_chunks.py <work-dir>   (after bind-candidate rendered hosts/)

The sealed yield classifier pins five chunks per direction and marks any other
count `measurement_censored`; a run whose shorter count was declared in advance
(boot D: two chunks) is not censored. The verdict takes the plan's declared
count and the record says whether a short run is short by declaration or by
fault. The same change is in this experiment's classify-throughput.py.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])
path = work / 'hosts/classify-throughput.py'
s = path.read_text()
old = """    timing = bool(len(directions)==2 and all(d.get('completed') and
                  len(d.get('chunks',[]))==5 and
"""
new = """    declared = measurement.get('chunks_each', 5)   # a predeclared shorter run is not a censored one
    timing = bool(len(directions)==2 and all(d.get('completed') and
                  len(d.get('chunks',[]))==declared and
"""
assert s.count(old) == 1, 'classifier anchor (timing)'
s = s.replace(old, new)
old = """                 measurement_censored=not timing)
"""
new = """                 measurement_censored=not timing,
                 measurement_short_by=None if timing and declared == 5 else ('declaration' if timing else 'fault'),
                 chunks_declared=declared)
"""
assert s.count(old) == 1, 'classifier anchor (censored)'
s = s.replace(old, new)
path.write_text(s)
compile(s, str(path), 'exec')
print('classifier takes the declared chunk count; short by declaration is recorded, not censored')
