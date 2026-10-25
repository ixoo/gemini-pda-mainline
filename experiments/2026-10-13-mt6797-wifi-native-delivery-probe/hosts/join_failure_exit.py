#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A failed join ends the leaf, so the seal and the reviewed return proceed.

usage: join_failure_exit.py <work-dir>   (after bind rendered hosts/; before prepare)

Boot O's join failed at the four-way handshake (the access point
deauthenticated with reason 15 ten seconds after the association), and the
leaf went on waiting for the data phase's record against its 720 s wall. The
host's 300 s run clock fired first; the device leaf and its supplicant were
still alive, so the session refused to seal the log ("owned supplicant not
confirmed quiesced") and the reviewed preservation and return refused on the
same quiescence proof. The kernel record that explains the failure was lost
with the owner's manual restart.

The leaf already ends its own supplicant on every exit path (quiesce_owned
after the cycle loop and in its EXIT trap); it only has to stop waiting. While
it waits for the data phase's record, and only then, the wait now fails:

- at once when the supplicant's own log shows the join has ended (a
  deauthentication or disconnection notification, or auto-connect disabled):
  in a healthy run these appear only at the lifetime's end, after the data
  phase opened (boots L, M and N);
- after 90 s from the wait's start without the data phase (a healthy join
  opens it in about 10-15 s).

The cycle then breaks as any data-phase fault does (`data_phase=
fault_or_timeout rc=5` or `rc=6`), the supplicant is quiesced, the leaf exits,
the host seals the kernel record, and the watcher's reviewed return runs. The
terminal and acknowledgement waits are unchanged.
"""
import sys
from pathlib import Path

JOIN_BOUND_S = 90

ANCHOR = '''        n=$(printf '%s\\n' "$log" | $BB grep -Ec "$pat" || true)
        [ -n "$n" ] || n=0
        [ "$n" -ge "$want" ] && return 0
'''
ADDED = '''        # A failed join ends the data-phase wait (join_failure_exit.py): the
        # supplicant's own end-of-join notifications, or the join bound.
        if [ "$pat" = "$data_re" ]; then
            if [ -f "$wpa_log" ] && $BB grep -qE 'CTRL-EVENT-DISCONNECTED|Deauthentication notification|Auto connect disabled' "$wpa_log"; then
                $BB printf 'join_failure_exit reason=supplicant elapsed_s=%s\\n' "$(($(now_s) - wr_start))"
                return 5
            fi
            if [ "$(($(now_s) - wr_start))" -ge "${join_bound_s:-@BOUND@}" ]; then
                $BB printf 'join_failure_exit reason=bound elapsed_s=%s\\n' "$(($(now_s) - wr_start))"
                return 6
            fi
        fi
'''.replace('@BOUND@', str(JOIN_BOUND_S))


def apply(prepare):
    s = prepare.read_text()
    old = "    leaf = retained.replace(old,b'    pc_result=0 # throughput: no periodic probes during measurement')\n"
    assert s.count(old) == 1, 'prepare anchor (periodic leaf replacement)'
    new = old + ("    # a failed join ends the data-phase wait so the leaf quiesces its supplicant and exits\n"
                 "    join_anchor = %r.encode()\n"
                 "    if leaf.count(join_anchor) != 1:\n"
                 "        raise ValueError('leaf anchor (data-record wait) changed')\n"
                 "    leaf = leaf.replace(join_anchor, join_anchor + %r.encode())\n" % (ANCHOR, ADDED))
    s = s.replace(old, new)
    compile(s, str(prepare), 'exec')
    prepare.write_text(s)


if __name__ == '__main__':
    apply(Path(sys.argv[1]) / 'hosts/throughput-prepare.py')
    print('join failure exit: the data-phase wait ends on the supplicant\'s end of join or after %d s (prepare, leaf)' % JOIN_BOUND_S)
