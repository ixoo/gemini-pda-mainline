#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture for parse-lifecycle.py: completeness, gaps, counts, sanitizing, summary."""
import pathlib
import runpy
import unittest

HERE = pathlib.Path(__file__).resolve().parent
MOD = runpy.run_path(str(HERE.parent / 'lifecycle/parse-lifecycle.py'), run_name='parse_lifecycle')
parse, summarize = MOD['parse'], MOD['summarize']


def kmsg(messages, start=100, prio=7, usec=1000):
    lines = []
    for i, (p, message) in enumerate(messages):
        lines.append('%d,%d,%d,-;%s\n' % (p if p is not None else prio, start + i, usec + i, message))
    return lines


ARM = (6, 'gwref10 arm: deadline_s=240 caps=512/1024/1024/2048/1024/256')


def seal(records, cmd=(0, 0, 0), event=(0, 0, 0), credit=(0, 0, 0), rxd=(0, 0, 0), txd=(0, 0, 0), state=(0, 0, 0)):
    return (6, 'gwref10 seal: reason=explicit records=%d truncated=0 cmd=%d/%d/%d event=%d/%d/%d credit=%d/%d/%d '
               'rxd=%d/%d/%d txd=%d/%d/%d state=%d/%d/%d' % ((records,) + cmd + event + credit + rxd + txd + state))


GOOD = [
    (4, 'some other kernel message'),
    ARM,
    (7, 'gwref10 cmd: n=1 cid=0x81 seq=9 set=0 len=16 bss=0 type=1'),
    (7, 'gwref10 event: n=2 eid=0x02 seq=9 len=20 hif=24'),
    (7, 'gwref10 event: n=3 linkq seq=9 rdy=1 speed=866 busy=3'),
    (7, 'gwref10 cmd: n=4 cid=0x07 seq=10 set=1 len=76 bss=0 type=1'),
    (7, 'gwref10 cmd: n=5 key seq=10 addremove=1 tx=1 keytype=1 auth=0 bss=0 alg=4 keyid=0 keylen=16 wlan=1 peer=bss'),
    (7, 'gwref10 credit: n=6 rel0=0 rel1=0 rel2=0 rel3=0 rel4=1 rel5=0 free0=5 free1=5 free2=5 free3=5 free4=2 free5=0'),
    (7, 'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20'),
    (7, 'gwref10 event: n=8 keydone seq=0 bss=0 sta=bss'),
    (7, 'gwref10 rxd: n=9 type=2 len=120 hdrlen=26 pad=0 trans=0 bssid=1 wlan=1 tid=0 sec=4 mismatch=0 fmt=0 uc2me=1 mc=0 bc=0 grp=0 fc=0x0088 havefc=1 eth=0x0000'),
    (7, 'gwref10 rxd: n=10 type=2 len=60 hdrlen=14 pad=0 trans=1 bssid=1 wlan=0 tid=0 sec=4 mismatch=0 fmt=0 uc2me=0 mc=0 bc=1 grp=1 fc=0x0000 havefc=0 eth=0x0806'),
    (7, 'gwref10 txd: n=11 cls=data pid=3 wlan=1 bss=0 sta=0 len=98 fmt=0 tid=0 prot=1 is80211=0 tc=1'),
    (7, 'gwref10 state: n=12 stafree sta=0 wlan=1 bss=0 state=3'),
    (4, 'unrelated message inside the window'),
    seal(12, cmd=(3, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 0, 40), txd=(1, 0, 0), state=(1, 0, 0)),
    (4, 'after'),
]


class ParseLifecycleTest(unittest.TestCase):
    def test_complete_cycle_parses_and_summarizes(self):
        ledger = parse(kmsg(GOOD))
        self.assertEqual(ledger['problems'], [])
        self.assertTrue(ledger['complete'])
        self.assertEqual(len(ledger['records']), 12)
        self.assertEqual(ledger['records'][4]['subtype'], 'key')
        self.assertEqual(ledger['records'][4]['fields']['peer'], 'bss')
        self.assertEqual(ledger['seal']['counts']['rxd'], {'recorded': 2, 'suppressed': 0, 'filtered': 40})
        summary = summarize(ledger)
        self.assertEqual(summary['key_commands'], [{'seq': 10, 'addremove': 1, 'keytype': 1, 'keyid': 0, 'peer': 'bss'}])
        self.assertEqual(summary['keydone_events'], [{'seq': 0, 'bss': 0, 'sta': 'bss'}])
        self.assertEqual(summary['rxd_protected_unicast'], 1)
        self.assertEqual(summary['rxd_protected_group'], 1)
        self.assertEqual(summary['group_downlink_evidence'], 'observed')
        self.assertEqual(summary['txd_protected'], 1)
        self.assertIn('names no key type', summary['keydone_attribution'])

    def test_missing_group_evidence_is_named(self):
        without = [m for m in GOOD if 'n=10 ' not in m[1]]
        without[-2] = seal(11, cmd=(3, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(1, 0, 40), txd=(1, 0, 0), state=(1, 0, 0))
        # record numbers must stay contiguous: renumber n=11,12 -> 10,11
        without = [(p, m.replace('n=11 ', 'n=10 ').replace('n=12 ', 'n=11 ')) for p, m in without]
        ledger = parse(kmsg(without))
        self.assertTrue(ledger['complete'], ledger['problems'])
        self.assertEqual(summarize(ledger)['group_downlink_evidence'], 'missing')

    def test_kmsg_gap_inside_the_window_is_a_problem(self):
        lines = kmsg(GOOD)
        del lines[6]  # drop one kernel line between arm and seal
        ledger = parse(lines)
        self.assertFalse(ledger['complete'])
        self.assertTrue(any('sequence gap' in p for p in ledger['problems']))

    def test_count_mismatch_and_missing_seal(self):
        bad = list(GOOD)
        bad[-2] = seal(12, cmd=(2, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 0, 40), txd=(1, 0, 0), state=(1, 0, 0))
        self.assertTrue(any('seal cmd recorded=2' in p for p in parse(kmsg(bad))['problems']))
        truncated = GOOD[:-2]
        self.assertIn('no seal line', parse(kmsg(truncated))['problems'])
        self.assertIn('no arm line', parse(kmsg(GOOD[2:]))['problems'])

    def test_record_outside_window_and_wrong_level(self):
        late = GOOD[:-1] + [(7, 'gwref10 cmd: n=13 cid=0x81 seq=11 set=0 len=16 bss=0 type=1')]
        problems = parse(kmsg(late))['problems']
        self.assertTrue(any('outside the armed window' in p for p in problems))
        loud = [(6 if 'n=1 ' in m else p, m) for p, m in GOOD]
        self.assertTrue(any('not KERN_DEBUG: n=1' in p for p in parse(kmsg(loud))['problems']))

    def test_unsanitizable_field_is_refused(self):
        leaky = list(GOOD)
        leaky[8] = (7, 'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 sta=00:11:22:33:44:55')
        ledger = parse(kmsg(leaky))
        self.assertTrue(any('not sanitizable: sta' in p for p in ledger['problems']))
        self.assertFalse(any('00:11' in str(r) for r in ledger['records']))
        named = list(GOOD)
        named[8] = (7, 'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 ssid=MyNetwork')
        self.assertTrue(any('not sanitizable: ssid' in p for p in parse(kmsg(named))['problems']))

    def test_truncated_and_length_refused_records(self):
        trunc = list(GOOD)
        trunc[2] = (7, 'gwref10 cmd: n=1 cid=0x81 seq=9 set=0 len=16 bss=0 type=1 trunc=1')
        self.assertTrue(any('n=1 truncated' in p for p in parse(kmsg(trunc))['problems']))
        counted = list(GOOD)
        counted[-2] = (6, counted[-2][1].replace('truncated=0', 'truncated=1'))
        self.assertIn('1 truncated records', parse(kmsg(counted))['problems'])
        refused = list(GOOD)
        refused[3] = (7, 'gwref10 event: n=2 eid=0x02 seq=9 badlen=1')
        ledger = parse(kmsg(refused))
        self.assertTrue(ledger['complete'] and ledger['length_refusals'] == 1)

    def test_continuation_lines_are_skipped(self):
        lines = kmsg(GOOD)
        lines.insert(3, ' SUBSYSTEM=foo\n')
        self.assertTrue(parse(lines)['complete'])


if __name__ == '__main__':
    unittest.main()
