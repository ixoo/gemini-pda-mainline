#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The transmit probe and the device's TCP state (boot H, second run).

usage: transmit_probe.py <work-dir>   (after receive_probe.py and the protocol
injection; before prepare)

Device side, in the probe block after the chunks: the receive UDP legs step
aside (they stand on three boots at zero loss) for one ICMP echo leg the
device offers toward the laptop, 1,400-byte payloads at 10 Mbit/s (893
requests at 1.12 ms), timed on the device's clock and summarised by
BusyBox ping (the laptop answers every request, so a missing reply is a
lost request); its own error line is kept if ping fails. The device's
BusyBox has no UDP sender, so the echo leg is the transmit probe this
harness can carry without a new device tool; the return traffic is the
declared deviation.

The 20 and 30 Mbit/s legs (1,786 and 2,679 requests at 0.56 and 0.37 ms)
ended early with no summary in boots M, N and S, their stderr discarded:
they reported nothing and are removed (the transmit chunks measure those
rates). With the device's UDP trigger gone, the laptop's trigger thread
waited for three connections that never came (`completed: false`,
`udp: []` in every run since boot H); it is created with no rates, so
only its laptop pings remain, and the record says the UDP legs are
retired.

One line per transmit chunk, 1.5 s in, from /proc/net/tcp for the socket to
the laptop's transmit port (0xBB81): the congestion window and slow-start
threshold (the last two fields), the retransmit-queue count and the queues;
and the device's TCP retransmission count (/proc/net/snmp, RetransSegs)
before and after the transmit direction.

The leaf's shellcheck comment lines are stripped at render and the console
indicator (not evidence) is left out of this run so the device command stays
under its 4,096-byte bound; the source keeps the comments.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
# 1. the device block: echo legs in place of the receive UDP legs
literal(h, """( u() { $BB awk '/^Udp:/{l=$3}END{print l}' /proc/net/snmp; }
for r in 10 20 30; do
a=$(u)
$BB timeout 5 $BB nc -w2 HOST 48003 </dev/null 2>/dev/null >/dev/null
$BB sleep 2.5; printf 'TP3_UDP %s %s\\n' "$r" "$(($(u)-a))"
done ) 2>/dev/null; printf 'TP3_RC=%s\\n' "$?"; true
""", """( for p in 893:0.00112; do c=${p%:*}
t0=$(clock); $BB ping -q -c $c -i ${p#*:} -s 1400 HOST >/tmp/p 2>&1; t1=$(clock)
printf 'TP3_TXPING %s %s %s\\n' "$c" $((t1-t0)) "$($BB grep -e ted -e ping: /tmp/p)"
done ) 2>/dev/null; printf 'TP3_RC=%s\\n' "$?"; true
""")
# 2. the device's TCP state 1.5 s into each transmit chunk, and its retransmission count around the direction
literal(h, """        rc=0; n=unknown
""", """        rc=0; n=unknown
        [ "$dir" = TX ] && ( $BB sleep 1.5; $BB awk '/:BB81 /{print "TP4_TCP '$i' "$16" "$17" "$7}' /proc/net/tcp ) &
""")
literal(h, """for dir in TX RX; do
    printf 'TP1_%s_CPU_BEFORE ' "$dir"; cpu
""", """rt() { $BB awk '/^Tcp: [0-9]/{print $13}' /proc/net/snmp; }; printf 'TP4_R0=%s\\n' "$(rt)"
for dir in TX RX; do
    printf 'TP1_%s_CPU_BEFORE ' "$dir"; cpu
""")
literal(h, """    [ "$dir" != RX ] || printf 'TP1_RX_BYTES=%s\\n' "$total"
""", """    [ "$dir" != RX ] || printf 'TP1_RX_BYTES=%s\\n' "$total"
    [ "$dir" != TX ] || printf 'TP4_R1=%s\\n' "$(rt)"
""")
# 3. comments stripped at render, and the console indicator's lines when it is off (the validators read the rendered text)
literal(h, """.replace('HOST', shlex.quote(host))
    return script
""", """.replace('HOST', shlex.quote(host))
    script = '\\n'.join(l for l in script.split('\\n') if not l.lstrip().startswith('# shellcheck'))
    if os.environ.get('TP_CONSOLE_PROGRESS') != '1':   # the indicator is off: its dead lines leave the bounded command
        script = '\\n'.join(l for l in script.split('\\n') if not (l.lstrip().startswith("cp '") or l.lstrip().startswith('cp() {')))
    return script
""")
# 4. the laptop side: parse the echo legs, the TCP state lines and the retransmission counts into the probe record
literal(h, """    m = re.search(rb'^TP3_RC=([0-9]+)\\r?$', output, re.M)
    record['probe_rc'] = int(m[1]) if m else None   # None: the block never reached its own status line
""", """    legs = []
    for m in re.finditer(rb'^TP3_TXPING ([0-9]+) ([0-9]+) (.*?)\\r?$', output, re.M):
        count, ns, summary = int(m[1]), int(m[2]), m[3].decode('ascii', 'replace')
        got = re.search(r'([0-9]+) packets received', summary)
        legs.append({'count': count, 'offered_ns': ns, 'payload_bytes': 1400,
                     'offered_mbit_s': count * 1400 * 8000 / ns if ns else None,
                     'received': int(got[1]) if got else None,
                     'delivered_mbit_s': (int(got[1]) * 1400 * 8000 / ns) if (got and ns) else None,
                     'loss_fraction': (1 - int(got[1]) / count) if (got and count) else None,
                     'summary': summary})
    record['tx_ping'] = legs
    record['tcp_state'] = [{'chunk': int(m[1]), 'cwnd': int(m[2]), 'ssthresh': int(m[3]), 'retrans_queue': int(m[4], 16)}
                           for m in re.finditer(rb'^TP4_TCP ([0-9]+) ([0-9]+) (-?[0-9]+) ([0-9A-Fa-f]+)\\r?$', output, re.M)]
    before = re.search(rb'^TP4_R0=([0-9]+)\\r?$', output, re.M); after = re.search(rb'^TP4_R1=([0-9]+)\\r?$', output, re.M)
    record['tcp_retrans_segs'] = {'before': int(before[1]) if before else None, 'after': int(after[1]) if after else None}
    m = re.search(rb'^TP3_RC=([0-9]+)\\r?$', output, re.M)
    record['probe_rc'] = int(m[1]) if m else None   # None: the block never reached its own status line
""")
# 5. the laptop's trigger: no rates (the device no longer triggers), so only its pings run
literal(h, "ProbeTrigger(host,48003,peer,48004,(10,20,30))", "ProbeTrigger(host,48003,peer,48004,())")
literal(h, """    record['tx_ping'] = legs
""", """    record['tx_ping'] = legs
    record['udp_legs'] = 'retired: the transmit probe replaced the device trigger (boot H)'
""")
compile(h.read_text(), str(h), 'exec')
print('transmit probe: one echo leg at 10 Mbit/s (its error kept), the UDP trigger retired, TCP state per transmit chunk, retransmission count, comments stripped at render')
