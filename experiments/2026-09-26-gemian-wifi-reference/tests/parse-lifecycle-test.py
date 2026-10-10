#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture for parse-lifecycle.py: schema, completeness verdicts, gaps, duplicates, sanitizing, summary."""
import pathlib
import runpy
import unittest

HERE = pathlib.Path(__file__).resolve().parent
MOD = runpy.run_path(str(HERE.parent / 'lifecycle/parse-lifecycle.py'), run_name='parse_lifecycle')
parse, summarize = MOD['parse'], MOD['summarize']


def kmsg(messages, start=100, prio=7, usec=1000):
    return ['%d,%d,%d,-;%s\n' % (p if p is not None else prio, start + i, usec + i, m) for i, (p, m) in enumerate(messages)]


ARM = (6, 'gwref10 arm: deadline_s=240 caps=512/1024/1024/2048/1024/256')


def seal(records, cmd=(0, 0, 0), event=(0, 0, 0), credit=(0, 0, 0), rxd=(0, 0, 0), txd=(0, 0, 0), state=(0, 0, 0), truncated=0):
    return (6, 'gwref10 seal: reason=explicit records=%d truncated=%d cmd=%d/%d/%d event=%d/%d/%d credit=%d/%d/%d '
               'rxd=%d/%d/%d txd=%d/%d/%d state=%d/%d/%d' % ((records, truncated) + cmd + event + credit + rxd + txd + state))


RXD = 'gwref10 rxd: n=%d type=2 len=%d span=%d off=16 hdrlen=26 pad=0 trans=%d bssid=1 wlan=%d tid=0 sec=%d status=0x%04x mismatch=%d fmt=0 uc2me=%d mc=0 bc=%d grp=%d fc=0x%04x havefc=%d eth=0x%04x'
GOOD = [
    (4, 'some other kernel message'),
    ARM,
    (7, 'gwref10 cmd: n=1 cid=0x81 seq=9 set=0 len=16 bss=0 type=1'),
    (7, 'gwref10 event: n=2 eid=0x02 seq=9 len=20 hif=24'),
    (7, 'gwref10 event: n=3 eid=0x0f seq=0 len=24 hif=24'),
    (7, 'gwref10 cmd: n=4 cid=0x07 seq=10 set=1 len=76 bss=0 type=1'),
    (7, 'gwref10 cmd: n=5 key seq=10 addremove=1 tx=1 keytype=1 auth=0 bss=0 alg=4 keyid=0 keylen=16 wlan=1 peer=bss'),
    (7, 'gwref10 credit: n=6 rel0=0 rel1=0 rel2=0 rel3=0 rel4=1 rel5=0 free0=5 free1=5 free2=5 free3=5 free4=2 free5=0'),
    (7, 'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20'),
    (7, 'gwref10 event: n=8 keydone seq=0 bss=0 sta=bss'),
    (7, RXD % (9, 120, 120, 0, 1, 4, 0x0000, 0, 1, 0, 0, 0x4188, 1, 0)),
    (7, RXD % (10, 60, 60, 1, 0, 4, 0x0000, 0, 0, 1, 1, 0, 0, 0x0806)),
    (7, 'gwref10 txd: n=11 cls=data pid=3 wlan=1 bss=0 sta=0 len=98 fmt=0 tid=0 prot=1 is80211=0 tc=1'),
    (7, 'gwref10 state: n=12 stafree sta=0 wlan=1 bss=0 state=3'),
    (4, 'unrelated message inside the window'),
    seal(12, cmd=(3, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 0, 40), txd=(1, 0, 0), state=(1, 0, 0)),
    (4, 'after'),
]


def variant(replacements, new_seal=None):
    out = []
    for p, m in GOOD:
        for old, new in replacements:
            m = m.replace(old, new)
        out.append((p, m))
    if new_seal is not None:
        out[-2] = new_seal
    return out


class ParseLifecycleTest(unittest.TestCase):
    def test_complete_cycle_parses_and_summarizes(self):
        ledger = parse(kmsg(GOOD))
        self.assertEqual(ledger['problems'], [])
        self.assertTrue(ledger['stream_intact'] and ledger['complete'])
        self.assertEqual(len(ledger['records']), 12)
        self.assertEqual(ledger['records'][4]['subtype'], 'key')
        self.assertEqual(ledger['records'][4]['fields']['peer'], 'bss')
        self.assertEqual(ledger['seal']['counts']['rxd'], {'recorded': 2, 'suppressed': 0, 'filtered': 40})
        summary = summarize(ledger)
        self.assertEqual(summary['key_commands'], [{'seq': 10, 'addremove': 1, 'keytype': 1, 'keyid': 0, 'peer': 'bss'}])
        self.assertEqual(summary['keydone_events'], [{'seq': 0, 'bss': 0, 'sta': 'bss'}])
        self.assertEqual(summary['rxd_protected_unicast'], 1)
        self.assertEqual(summary['rxd_protected_group'], 1)
        self.assertEqual(summary['rxd_security_metadata_unclassified'], 0)
        self.assertEqual(summary['group_downlink_evidence'], 'observed')
        self.assertEqual(summary['txd_protected'], 1)
        self.assertIn('names no key type', summary['keydone_attribution'])

    def test_suppressed_or_truncated_breaks_completeness_but_not_stream(self):
        capped = variant([], seal(12, cmd=(3, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 7, 40), txd=(1, 0, 0), state=(1, 0, 0)))
        ledger = parse(kmsg(capped))
        self.assertTrue(ledger['stream_intact'])
        self.assertFalse(ledger['complete'])
        self.assertEqual(ledger['suppressed'], 7)
        truncated = variant([], seal(12, cmd=(3, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 0, 40), txd=(1, 0, 0), state=(1, 0, 0), truncated=1))
        self.assertFalse(parse(kmsg(truncated))['complete'])

    def test_protected_classification_requires_consistency(self):
        mismatched = variant([(RXD % (9, 120, 120, 0, 1, 4, 0x0000, 0, 1, 0, 0, 0x4188, 1, 0), RXD % (9, 120, 120, 0, 1, 4, 0x0004, 1, 1, 0, 0, 0x4188, 1, 0))])
        summary = summarize(parse(kmsg(mismatched)))
        self.assertEqual(summary['rxd_protected_unicast'], 0)
        self.assertEqual(summary['rxd_security_metadata_unclassified'], 1)
        self.assertEqual(summary['rxd_error_status'], 1)
        # an error status with mismatch 0 (FCS, ICV, MIC, fragment, non-data) is not accepted data either
        for status in (0x0002, 0x0010, 0x0020, 0x0800, 0x2000):
            errored = variant([(RXD % (10, 60, 60, 1, 0, 4, 0x0000, 0, 0, 1, 1, 0, 0, 0x0806), RXD % (10, 60, 60, 1, 0, 4, status, 0, 0, 1, 1, 0, 0, 0x0806))])
            summary = summarize(parse(kmsg(errored)))
            self.assertEqual(summary['rxd_protected_group'], 0, hex(status))
            self.assertEqual(summary['group_downlink_evidence'], 'missing', hex(status))
        # group bit without a group match flag is not group evidence
        odd = variant([(RXD % (10, 60, 60, 1, 0, 4, 0x0000, 0, 0, 1, 1, 0, 0, 0x0806), RXD % (10, 60, 60, 1, 0, 4, 0x0000, 0, 0, 0, 1, 0, 0, 0x0806))])
        summary = summarize(parse(kmsg(odd)))
        self.assertEqual(summary['rxd_protected_group'], 0)
        self.assertEqual(summary['group_downlink_evidence'], 'missing')

    def test_kmsg_gap_inside_the_window_is_a_problem(self):
        lines = kmsg(GOOD)
        del lines[6]
        ledger = parse(lines)
        self.assertFalse(ledger['stream_intact'])
        self.assertTrue(any('sequence gap' in p for p in ledger['problems']))

    def test_count_mismatch_missing_and_duplicate_markers(self):
        bad = variant([], seal(12, cmd=(2, 0, 0), event=(4, 0, 0), credit=(1, 0, 0), rxd=(2, 0, 40), txd=(1, 0, 0), state=(1, 0, 0)))
        self.assertTrue(any('seal cmd recorded=2' in p for p in parse(kmsg(bad))['problems']))
        self.assertIn('no seal line', parse(kmsg(GOOD[:-2]))['problems'])
        self.assertIn('no arm line', parse(kmsg(GOOD[2:]))['problems'])
        twice = GOOD[:-1] + [GOOD[-2]] + [GOOD[-1]]
        self.assertIn('second seal line', parse(kmsg(twice))['problems'])
        rearmed = GOOD[:3] + [ARM] + GOOD[3:]
        self.assertIn('second arm line', parse(kmsg(rearmed))['problems'])
        unknown = GOOD[:3] + [(7, 'gwref10 bogus: n=99 x=1')] + GOOD[3:]
        self.assertIn('unknown gwref10 line', parse(kmsg(unknown))['problems'])

    def test_record_outside_window_and_wrong_level(self):
        late = GOOD[:-1] + [(7, 'gwref10 cmd: n=13 cid=0x81 seq=11 set=0 len=16 bss=0 type=1')]
        self.assertTrue(any('outside the armed window' in p for p in parse(kmsg(late))['problems']))
        loud = [(6 if 'n=1 ' in m else p, m) for p, m in GOOD]
        self.assertTrue(any('not KERN_DEBUG: n=1' in p for p in parse(kmsg(loud))['problems']))

    def test_schema_refuses_identifiers_unexpected_fields_and_duplicates(self):
        cases = {
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 sta=00:11:22:33:44:55': 'unparsable field',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 ssid=MyNetwork': 'unparsable field',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 ssid=mynetwork': 'unexpected field ssid',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 ssid=12345': 'unexpected field ssid',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 key=5a5a5a5a': 'unexpected field key',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16 hif=20 hif=20': 'duplicate field hif',
            'gwref10 event: n=7 eid=0x24 seq=0 len=16': 'incomplete record',
            'gwref10 event: n=7 eid=0x24 seq=0 len=sixteen hif=20': 'field type mismatch len',
            'gwref10 event: n=7 secret seq=0 bss=0 sta=bss': 'unexpected subtype',
            'gwref10 event: n=7 linkq seq=9 rdy=1 speed=866 busy=3': 'unexpected subtype',
            'gwref10 event: n=7 keydone seq=0 bss=0 sta=0x021122': 'field type mismatch sta',
        }
        for message, expected in cases.items():
            leaky = list(GOOD)
            leaky[8] = (7, message)
            ledger = parse(kmsg(leaky))
            self.assertTrue(any(expected in p for p in ledger['problems']), (message, ledger['problems']))
            text = str(ledger)
            for secret in ('00:11', 'MyNetwork', '5a5a', '12345', '021122'):
                self.assertNotIn(secret, text)

    def test_truncated_and_length_refused_records(self):
        trunc = list(GOOD)
        trunc[2] = (7, 'gwref10 cmd: n=1 cid=0x81 seq=9 set=0 len=16 bss=0 type=1 trunc=1')
        self.assertTrue(any('n=1: truncated record' in p for p in parse(kmsg(trunc))['problems']))
        refused = list(GOOD)
        refused[3] = (7, 'gwref10 event: n=2 eid=0x02 seq=9 badlen=1')
        ledger = parse(kmsg(refused))
        self.assertTrue(ledger['complete'] and ledger['length_refusals'] == 1)
        badhdr = list(GOOD)
        badhdr[10] = (7, 'gwref10 rxd: n=9 badhdr=1 declared=40 hif=40')
        self.assertTrue(parse(kmsg(badhdr))['stream_intact'])

    def test_continuation_lines_are_skipped(self):
        lines = kmsg(GOOD)
        lines.insert(3, ' SUBSYSTEM=foo\n')
        self.assertTrue(parse(lines)['complete'])


if __name__ == '__main__':
    unittest.main()
