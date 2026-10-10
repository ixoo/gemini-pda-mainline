#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay the Gemian reference ledgers' metadata against the contracts the C2/C3 proposals encode.

The ledgers (experiments/2026-09-26-gemian-wifi-reference/results/run*-v10/ledger.json) carry
command and event identifiers, sequences, descriptor classes, lengths and flags, never packet
bytes. This fixture checks order and class facts only: which commands the vendor sends, with
which key fields and WLAN indices, how its add-key-done events follow, what the receive and
transmit descriptor classes look like, and how the stock association's teardown is shaped. No
packet content is replayed and no network function is validated; decoder, sequence and ledger
logic has its own synthetic fixtures.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2] / '2026-09-26-gemian-wifi-reference' / 'results'


def ledger(run):
    return json.loads((ROOT / ('run%d-v10' % run) / 'ledger.json').read_text())


def records(data, category, subtype=None):
    return [r for r in data['records'] if r['category'] == category and (subtype is None or r.get('subtype') == subtype)]


class ReferenceReplay(unittest.TestCase):
    def test_run3_group_key_under_the_declared_broadcast_entry(self):
        data = ledger(3)
        keys = [r for r in records(data, 'cmd', 'key') if r['fields']['addremove'] == 1]
        self.assertEqual(len(keys), 2)
        pairwise, group = keys
        self.assertEqual((pairwise['fields']['keytype'], pairwise['fields']['keyid'], pairwise['fields']['wlan'],
                          pairwise['fields']['alg'], pairwise['fields']['keylen'], pairwise['fields']['tx'], pairwise['fields']['peer']),
                         (1, 0, 1, 4, 16, 1, 'bss'))
        self.assertEqual((group['fields']['keytype'], group['fields']['keyid'], group['fields']['wlan'],
                          group['fields']['alg'], group['fields']['keylen'], group['fields']['tx'], group['fields']['peer']),
                         (0, 1, 2, 4, 16, 0, 'bss'))
        self.assertLess(pairwise['seq'], group['seq'])
        # Every station record update before the keys declares WLAN index 1 and BMC index 2 (0164).
        stations = [r for r in records(data, 'cmd', 'sta') if r['seq'] < pairwise['seq']]
        self.assertTrue(stations)
        self.assertTrue(all(r['fields']['wlan'] == 1 and r['fields']['bmcwlan'] == 2 for r in stations))
        # The BSS payloads keep the BSS's own entry 0 after association.
        bss = [r for r in records(data, 'cmd', 'bssinfo') if r['fields']['connstate'] == 0]
        self.assertTrue(bss and all(r['fields']['bmcwlan'] == 0 for r in bss))

    def test_run3_two_key_done_events_each_after_a_key_command(self):
        data = ledger(3)
        keys = [r for r in records(data, 'cmd', 'key') if r['fields']['addremove'] == 1]
        done = records(data, 'event', 'keydone')
        self.assertEqual(len(done), 2)
        for key, event in zip(keys, done):
            self.assertGreater(event['seq'], key['seq'])
            self.assertLess(event['usec'] - key['usec'], 2000)   # observed within 1 ms; order only, no key named
            self.assertEqual((event['fields']['seq'], event['fields']['sta']), (0, 'bss'))
        self.assertLess(done[0]['seq'], keys[1]['seq'])        # first before the group command (0163's first window)
        self.assertGreater(done[1]['seq'], keys[1]['seq'])     # second after it (0163's second window, now required)

    def test_run3_channel_privilege_released_after_the_join_with_data_continuing(self):
        data = ledger(3)
        privilege = [r for r in records(data, 'cmd') if r['fields'].get('cid') == 0x1c]
        self.assertEqual(len(privilege), 2)            # request, then the release
        keys = [r for r in records(data, 'cmd', 'key') if r['fields']['addremove'] == 1]
        self.assertLess(privilege[0]['seq'], keys[0]['seq'])
        self.assertGreater(privilege[1]['seq'], keys[1]['seq'])
        after = [r for r in records(data, 'rxd') if r['seq'] > privilege[1]['seq'] and r['fields']['sec'] == 4]
        self.assertTrue(after)                          # protected data keeps arriving without a privilege (0165)

    def test_run3_receive_classes_and_the_aggregation_polarity(self):
        data = ledger(3)
        protected = [r['fields'] for r in records(data, 'rxd') if r['fields']['sec'] == 4]
        unicast = [f for f in protected if f['grp'] == 0]
        group = [f for f in protected if f['grp'] == 1]
        self.assertEqual((len(unicast), len(group)), (962, 131))
        self.assertTrue(all(f['uc2me'] == 1 and f['bc'] == 0 and f['mc'] == 0 and f['wlan'] == 1 and f['trans'] == 1 and
                            f['hdrlen'] == 14 and f['bssid'] == 1 and f['status'] == 0 for f in unicast))
        self.assertTrue(all(f['uc2me'] == 0 and f['bc'] == 1 and f['wlan'] == 2 and f['trans'] == 1 and
                            f['hdrlen'] == 14 and f['bssid'] == 1 and f['status'] == 0xc000 for f in group))
        # The vendor station is HT: its unicast frames are A-MPDU sub-frames (status bits 14/15
        # clear is "aggregated" in the pinned inverse macros); the group frames are not. The
        # mainline legacy station admits only the non-aggregated 0xc000 shape (0166).
        self.assertTrue(all(f['status'] & 0xc000 == 0 for f in unicast))
        self.assertTrue(all(f['status'] & 0xc000 == 0xc000 for f in group))

    def test_run3_transmit_descriptor_classes(self):
        data = ledger(3)
        tx = [r['fields'] for r in records(data, 'txd')]
        data_tx = [f for f in tx if f['cls'] == 'data']
        self.assertEqual(len(data_tx), 10)
        self.assertTrue(all(f['prot'] == 1 and f['fmt'] == 0 and f['is80211'] == 0 and f['wlan'] == 1 and f['bss'] == 0
                            for f in data_tx))
        self.assertEqual(sorted({f['tc'] for f in data_tx}), [1, 3])      # the vendor's WMM station; mainline uses TC1 only
        eapol = [f for f in tx if f['cls'] == 'eapol']
        self.assertEqual(len(eapol), 2)
        self.assertTrue(all(f['prot'] == 0 and f['fmt'] == 0 and f['tc'] == 0 for f in eapol))
        done = records(data, 'event', 'txdone')
        pids = {f['pid'] for f in tx if f['cls'] != 'data' or f['pid']}
        self.assertTrue(pids <= {d['fields']['pid'] for d in done} | {0})

    def test_stock_teardown_shape_is_the_supplicant_s_index_based_deletion(self):
        for run in (1, 2, 3):
            data = ledger(run)
            removals = [r['fields'] for r in records(data, 'cmd', 'key') if r['fields']['addremove'] == 0]
            self.assertEqual(len(removals), 6, run)
            self.assertEqual([f['keyid'] for f in removals], [0, 1, 2, 3, 4, 5])
            self.assertTrue(all(f['keytype'] == 0 and f['peer'] == 'zero' and f['wlan'] == 255 for f in removals), run)
            first_removal = min(r['seq'] for r in records(data, 'cmd', 'key') if r['fields']['addremove'] == 0)
            teardown = [r for r in records(data, 'cmd') if r['seq'] > first_removal and r.get('subtype') in ('bssinfo', 'starm', 'bss')]
            kinds = [r.get('subtype') for r in teardown[:3]]
            self.assertEqual(kinds, ['bssinfo', 'starm', 'bss'], run)
            self.assertEqual(teardown[2]['fields']['active'], 0)


if __name__ == '__main__':
    unittest.main()
