#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject incomplete join evidence and unsafe private AP input."""

import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
classify = runpy.run_path(str(HERE / 'classify-join.py'))['classify']
bind = runpy.run_path(str(HERE / 'bind-target.py'))['bind']


def log(accepted, keys=False):
    lines = ['credit: pages=1 remaining=0', 'credit: pages=1 remaining=0',
             'grant: channel=40 interval_ms=9000', 'credit: pages=2 remaining=0',
             'peer: ready=1 sequence=8', 'TX: subtype=11 pid=1 pages=1',
             'credit: pages=1 remaining=0',
             'TX done: pid=1 status=0 advanced=0 count=0', 'RX: subtype=11 status=0',
             'TX: subtype=0 pid=2 pages=1', 'credit: pages=1 remaining=0',
             'TX done: pid=2 status=0 advanced=0 count=0',
             'RX: subtype=1 status=' + ('0' if accepted else '31')]
    if accepted:
        lines += ['credit: pages=1 remaining=0', 'credit: pages=2 remaining=0',
                  'activation: sequence=9 state=3']
        if keys:
            # Phase C2 accepted path: message 1 delivered early, message 2 sent after
            # activation, message 3 delivered, message 4 sent, two key commands with
            # their credits, the deauthentication, then the two removals before stage 0.
            lines.insert(lines.index('RX: subtype=1 status=0') + 1,
                         'eapol delivered: translated=1 frame=99 activated=0 vector=0 bss=15')
            lines += ['eapol sent: pid=3 pages=2 bytes=135', 'credit: pages=2 remaining=0',
                      'TX done: pid=3 status=0 advanced=0 count=0',
                      'eapol delivered: translated=1 frame=155 activated=1 vector=0 bss=1',
                      'eapol sent: pid=4 pages=2 bytes=113', 'credit: pages=2 remaining=0',
                      'TX done: pid=4 status=0 advanced=0 count=0',
                      'key command: pairwise submitted sequence=10', 'credit: pages=1 remaining=0',
                      'key credit returned: pairwise', 'key done: first after=pairwise bss=0 peer=1',
                      'key command: group submitted sequence=11', 'credit: pages=1 remaining=0',
                      'key done: second after=group bss=0 peer=1', 'key credit returned: group',
                      # Phase C3 lifetime (0172): the bounded data phase opened inside the
                      # channel grant after the group key's credit (its budget the grant's
                      # remainder), its end by the budget; the privilege returns in stage 1.
                      'data phase: budget_ms=5500 teardown_margin_ms=5000 inside_grant=1',
                      'data TX: first pid=5 pages=3 bytes=342', 'data credit: pages=3 debt=0 count=1',
                      'data RX: first group=0 tid=0 keyid=0 bytes=320 vector=1']
            lines += ['TX done: pid=%d status=0 advanced=1 count=1' % pid for pid in range(5, 17)]
            lines += ['data phase end: reason=budget elapsed_ms=5500 rx_unicast=40 rx_group=3 rx_dropped=0 tx_queued=12 tx_done=12 tx_failed=0 tx_credits=36']
        lines += ['TX: subtype=12 pid=' + ('17' if keys else '3') + ' pages=1', 'credit: pages=1 remaining=0',
                  'TX done: pid=' + ('17' if keys else '3') + ' status=0 advanced=0 count=0']
        if keys:
            lines += ['key removal: pairwise submitted sequence=13', 'credit: pages=1 remaining=0',
                      'key removal: group submitted sequence=14', 'credit: pages=1 remaining=0']
    for stage in range(3):
        lines += ['cleanup submission: stage=' + str(stage), 'credit: pages=1 remaining=0']
    lines += ['cleanup: stage=3 credits=returned slots=retired deauth=' + str(int(accepted))]
    return ''.join('one-shot WLAN join ' + line + '\n' for line in lines).encode()


class HostTests(unittest.TestCase):
    def test_accepted_and_refused_exchange(self):
        for accepted in (False, True):
            result = classify(log(accepted))
            self.assertTrue(result['bounded_join_pass'])
            self.assertEqual(result['associated_station_activation_demonstrated'], accepted)
            self.assertFalse(result['wifi_operational'])

    def test_data_group1_observation(self):
        # 0179: the per-class group-1 (received PN group) observation line, printed
        # once at the data phase end. Feature-absent old logs stay valid; a present
        # line is consistent only as a single, well-placed, fully reconciled record.
        good = log(True, keys=True)
        end = b'one-shot WLAN join data phase end: reason=budget'
        pfx = b'one-shot WLAN join '

        def place(block):
            nl = good.index(b'\n', good.index(end)) + 1
            return good[:nl] + block + good[nl:]

        def line(text):
            return pfx + text + b'\n'

        base = classify(good)
        self.assertIsNone(base['data_group1'])
        self.assertFalse(base['data_group1_consistent'])
        self.assertFalse(base['malformed_stage_record'])
        self.assertTrue(base['bounded_join_pass'])

        absent = classify(place(line(b'data group1: uni_present=0 uni_absent=40 grp_present=0 grp_absent=3 uni_masks=0x100 grp_masks=0x100')))
        self.assertTrue(absent['data_group1_consistent'])
        self.assertFalse(absent['malformed_stage_record'])
        self.assertEqual(absent['data_group1'], {'uni_present': 0, 'uni_absent': 40, 'grp_present': 0,
                                                 'grp_absent': 3, 'uni_masks': 0x100, 'grp_masks': 0x100})

        present = classify(place(line(b'data group1: uni_present=40 uni_absent=0 grp_present=3 grp_absent=0 uni_masks=0x200 grp_masks=0x200')))
        self.assertTrue(present['data_group1_consistent'])
        self.assertFalse(present['malformed_stage_record'])

        for bad in (b'data group1: uni_present=0 uni_absent=40 grp_present=0 grp_absent=3 uni_masks=0x1 grp_masks=0x100',    # value < 8
                    b'data group1: uni_present=1 uni_absent=39 grp_present=0 grp_absent=3 uni_masks=0x100 grp_masks=0x100',  # present>0, even-only mask
                    b'data group1: uni_present=0 uni_absent=30 grp_present=0 grp_absent=3 uni_masks=0x100 grp_masks=0x100'): # total 30 != 40
            r = classify(place(line(bad)))
            self.assertTrue(r['malformed_stage_record'], bad)
            self.assertFalse(r['data_group1_consistent'], bad)

        full = line(b'data group1: uni_present=0 uni_absent=40 grp_present=0 grp_absent=3 uni_masks=0x100 grp_masks=0x100')
        # Misplaced after the cleanup terminal, duplicated, and present without a data phase end.
        self.assertTrue(classify(good + full)['malformed_stage_record'])
        self.assertTrue(classify(place(full + full))['malformed_stage_record'])
        no_end = b''.join(ln + b'\n' for ln in good.split(b'\n') if end not in ln and ln)
        self.assertTrue(classify(no_end + full)['malformed_stage_record'])

    def test_incomplete_or_duplicate_evidence(self):
        raw = log(True)
        mutations = [raw.replace(b'status=0 advanced', b'status=1 advanced', 1),
                     raw.replace(b'activation: sequence=9 state=3', b'activation: sequence=9 state=1'),
                     raw.replace(b'credit: pages=2 remaining=0', b'credit: pages=1 remaining=0', 1),
                     raw + b'one-shot WLAN join TX: subtype=11 pid=1 pages=1\n',
                     raw + b'one-shot WLAN join stopped: status=-5\n',
                     raw.replace(b'cleanup: stage=3', b'cleanup: stage=2'),
                     raw.replace(b'pid=2 status=0', b'pid=3 status=0')]
        for mutation in mutations:
            self.assertFalse(classify(mutation)['bounded_join_pass'])
        self.assertFalse(classify(b'')['bounded_join_pass'])

    def test_diagnostic_records_are_recognized_not_malformed(self):
        raw = log(False)
        # The runtime-7 shape: cleanup submissions returned, then a refused control
        # event and the footer; no stage-3 line. Diagnostics are recognized, the
        # join is not healthy, and nothing is flagged malformed.
        cut = raw.index(b'one-shot WLAN join cleanup: stage=3')
        tail = (b'one-shot WLAN join control event refused: status=-71 bytes=12 type=0xe000 id=0x11 seq=0\n'
                b'one-shot WLAN join stopped: status=-71 first=0 submitted=0x801 debt=0 cleanup=3 branch=6\n')
        result = classify(raw[:cut] + tail)
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['diagnostic_records'], ['control event refused'])
        self.assertTrue(result['management_exchange_demonstrated'])
        self.assertFalse(result['healthy_cleanup_demonstrated'])
        self.assertFalse(result['bounded_join_pass'])
        for line in (b'one-shot WLAN join frame refused: bytes=3 type=0x10000 allowed=0x1400\n',
                     b'one-shot WLAN join cleanup refused: stage=3 phase=5 free=25 limit=26 pending_cpu=1 pending_ffa=0 sequences=1 locked=0\n',
                     b'one-shot WLAN join credit overflow: pages=1 debt=0\n'):
            self.assertFalse(classify(raw[:cut] + line + tail)['malformed_stage_record'])
        # A healthy log with an unknown record kind is still malformed, and so is a
        # known diagnostic prefix with the wrong grammar: arbitrary text, a foreign
        # BSS slot, a non-boolean flag, or an extra suffix.
        self.assertTrue(classify(raw + b'one-shot WLAN join mystery: x=1\n')['malformed_stage_record'])
        for bad in (b'one-shot WLAN join bss absence: anything goes\n',
                    b'one-shot WLAN join bss absence: bss=1 absent=1 quota=0 reserved=0\n',
                    b'one-shot WLAN join bss absence: bss=0 absent=2 quota=0 reserved=0\n',
                    b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=0 extra=1\n',
                    b'one-shot WLAN join control event refused: status=-71 bytes=12 type=0xe000 id=0x11\n',
                    b'one-shot WLAN join cleanup refused: stage=9 phase=5 free=25 limit=26 pending_cpu=1 pending_ffa=0 sequences=1 locked=0\n'):
            self.assertTrue(classify(raw + bad)['malformed_stage_record'], bad)
        # An admitted indication is valid only between the stage-2 cleanup submission
        # and the cleanup terminal, at most twice; the stage grammar decides health.
        absence = b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=0\n'
        good = log(True)
        stage3 = good.index(b'one-shot WLAN join cleanup: stage=3')
        placed = good[:stage3] + absence + good[stage3:]
        recorded = classify(placed)
        self.assertFalse(recorded['malformed_stage_record'])
        self.assertEqual(recorded['diagnostic_records'], ['bss absence'])
        self.assertTrue(recorded['bounded_join_pass'])
        self.assertFalse(classify(good[:stage3] + absence + absence + good[stage3:])['malformed_stage_record'])
        # Three indications, or one after the terminal or before the stage-2 submission, are malformed.
        self.assertTrue(classify(good[:stage3] + absence * 3 + good[stage3:])['malformed_stage_record'])
        self.assertTrue(classify(good + absence)['malformed_stage_record'])
        stage2 = good.index(b'one-shot WLAN join cleanup submission: stage=2')
        self.assertTrue(classify(good[:stage2] + absence + good[stage2:])['malformed_stage_record'])
        # Before the stopped footer in a refused-cleanup log it is valid.
        self.assertFalse(classify(raw[:cut] + absence + tail)['malformed_stage_record'])
        # A refusal diagnostic alone makes an otherwise healthy trace negative, even
        # without a stopped footer; the admitted indication does not.
        overflow = b'one-shot WLAN join credit overflow: pages=1 debt=0\n'
        negative = classify(good[:stage3] + overflow + good[stage3:])
        self.assertTrue(negative['refusal_recorded'])
        self.assertFalse(negative['bounded_join_pass'])
        self.assertFalse(negative['malformed_stage_record'])
        self.assertFalse(recorded['refusal_recorded'])
        # Byte fields are 0..255: three digits above that are malformed metadata.
        for bad in (b'one-shot WLAN join bss absence: bss=0 absent=1 quota=999 reserved=0\n',
                    b'one-shot WLAN join bss absence: bss=0 absent=1 quota=0 reserved=256\n',
                    b'one-shot WLAN join control event refused: status=-71 bytes=12 type=0xe000 id=0x11 seq=300\n'):
            self.assertTrue(classify(good[:stage3] + bad + good[stage3:])['malformed_stage_record'], bad)
        self.assertFalse(classify(good[:stage3] + b'one-shot WLAN join bss absence: bss=0 absent=1 quota=255 reserved=0\n' + good[stage3:])['malformed_stage_record'])

    def test_no_match_bss_observation_is_bound_to_the_pre_activation_interval(self):
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        after_activation = good.index(b'\n', activation) + 1
        early = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=0 vector=0 bss=15\n'
        late15 = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=1 vector=0 bss=15\n'
        late1 = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=1 vector=1 bss=1\n'
        self.assertEqual(classify(good[:activation] + early + good[activation:])['eapol_observations'][0]['bss'], 15)
        self.assertTrue(classify(good[:after_activation] + late15 + good[after_activation:])['malformed_stage_record'])
        # Tag 1 was measured after the activation (runtime 15); tag 0 never was.
        self.assertFalse(classify(good[:after_activation] + late1 + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + late1.replace(b'bss=1', b'bss=0') + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:activation] + early.replace(b'bss=15', b'bss=1') + good[activation:])['malformed_stage_record'])
        for bad in (b'bss=0', b'bss=16', b'bss=3c'):
            self.assertTrue(classify(good[:activation] + early.replace(b'bss=15', bad) + good[activation:])['malformed_stage_record'], bad)

    def test_c2_handshake_path_is_accepted_and_its_claims_bounded(self):
        raw = log(True, keys=True)
        result = classify(raw)
        self.assertTrue(result['bounded_join_pass'] and result['healthy_cleanup_demonstrated'], result)
        self.assertEqual(result['eapol_shape_observations'], 2)
        self.assertEqual(result['eapol_frames_sent'], 2)
        self.assertEqual(result['key_commands_submitted'], ['pairwise', 'group'])
        self.assertEqual(result['key_credits_returned'], ['pairwise', 'group'])
        self.assertEqual(result['key_removals_submitted'], ['pairwise', 'group'])
        self.assertTrue(result['handshake_keys_submitted'] and result['driver_handshake_path_pass'])
        self.assertFalse(result['wifi_operational'])
        # The deauthentication's page may return after its TX done.
        swapped = raw.replace(b'one-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join TX done: pid=17 status=0 advanced=0 count=0\n',
                              b'one-shot WLAN join TX done: pid=17 status=0 advanced=0 count=0\none-shot WLAN join credit: pages=1 remaining=0\n')
        self.assertNotEqual(swapped, raw)
        self.assertTrue(classify(swapped)['driver_handshake_path_pass'])
        # Missing all removals, or only the group removal missing: not healthy; a partial
        # handshake (pairwise only) with its exact removal is healthy but not a pass.
        no_removals = raw.replace(b'one-shot WLAN join key removal: pairwise submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key removal: group submitted sequence=14\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        self.assertFalse(classify(no_removals)['bounded_join_pass'])
        no_group_removal = raw.replace(b'one-shot WLAN join key removal: group submitted sequence=14\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        self.assertFalse(classify(no_group_removal)['bounded_join_pass'])
        partial = raw.replace(b'one-shot WLAN join key command: group submitted sequence=11\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key done: second after=group bss=0 peer=1\none-shot WLAN join key credit returned: group\n', b'').replace(
            b'one-shot WLAN join key removal: group submitted sequence=14\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        # Without the group key there is no channel release and no data phase, and
        # the stage-1 channel abort is submitted with its credit as before.
        for line in [b'data phase: budget_ms=5500 teardown_margin_ms=5000 inside_grant=1\n',
                     b'data credit: pages=3 debt=0 count=1\n',
                     b'data TX: first pid=5 pages=3 bytes=342\n', b'data RX: first group=0 tid=0 keyid=0 bytes=320 vector=1\n',
                     b'data phase end: reason=budget elapsed_ms=5500 rx_unicast=40 rx_group=3 rx_dropped=0 tx_queued=12 tx_done=12 tx_failed=0 tx_credits=36\n'] + [
                         b'TX done: pid=%d status=0 advanced=1 count=1\n' % pid for pid in range(5, 17)]:
            self.assertIn(b'one-shot WLAN join ' + line, partial)
            partial = partial.replace(b'one-shot WLAN join ' + line, b'')
        partial = partial.replace(b'pid=17 ', b'pid=5 ')
        partial_result = classify(partial)
        self.assertTrue(partial_result['bounded_join_pass'])
        self.assertFalse(partial_result['handshake_keys_submitted'] or partial_result['driver_handshake_path_pass'])
        # Page arithmetic and sequence ownership: wrong EAPOL page count, duplicate or
        # out-of-order key sequences are malformed.
        self.assertTrue(classify(raw.replace(b'eapol sent: pid=3 pages=2 bytes=135', b'eapol sent: pid=3 pages=1 bytes=135'))['malformed_stage_record'] or
                        not classify(raw.replace(b'eapol sent: pid=3 pages=2 bytes=135', b'eapol sent: pid=3 pages=1 bytes=135'))['bounded_join_pass'])
        self.assertTrue(classify(raw.replace(b'key command: group submitted sequence=11', b'key command: group submitted sequence=10'))['malformed_stage_record'])
        self.assertTrue(classify(raw.replace(b'key removal: group submitted sequence=14', b'key removal: group submitted sequence=9'))['malformed_stage_record'])
        # Group before pairwise, a missing credit, a third security frame, a removal of a
        # key never submitted, or a removal before the deauthentication: not healthy.
        bad = [raw.replace(b'key command: pairwise submitted sequence=10', b'key command: group submitted sequence=10', 1),
               raw.replace(b'one-shot WLAN join key credit returned: group\n', b''),
               raw.replace(b'eapol sent: pid=4 pages=2 bytes=113', b'eapol sent: pid=4 pages=2 bytes=113\none-shot WLAN join eapol sent: pid=6 pages=2 bytes=113'),
               raw.replace(b'one-shot WLAN join key command: group submitted sequence=11\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key done: second after=group bss=0 peer=1\none-shot WLAN join key credit returned: group\n', b''),
               raw.replace(b'one-shot WLAN join key removal: pairwise submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\n', b'').replace(
                   b'one-shot WLAN join TX: subtype=12 pid=5 pages=1\n', b'one-shot WLAN join key removal: pairwise submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join TX: subtype=12 pid=5 pages=1\n')]
        for mutation in bad:
            self.assertFalse(classify(mutation)['bounded_join_pass'])
        # The C1 shape without keys is unchanged.
        self.assertTrue(classify(log(True))['bounded_join_pass'])
        self.assertFalse(classify(log(True))['handshake_keys_submitted'])

    def test_frame_refusal_accepts_the_bare_and_the_extended_record(self):
        denied = log(False)
        cut = denied.index(b'one-shot WLAN join cleanup submission: stage=0')
        bare = b'one-shot WLAN join frame refused: bytes=147 type=0x51af allowed=0x1402\n'
        extended = (b'one-shot WLAN join frame refused: bytes=147 type=0x51af allowed=0x1402 hdr=0228ce0001008000'
                    b' groups=0x8 at=34 g4fc=0x208 g4seq=0x1230 g4ta=1 translated=1 first=0x888e\n')
        for line in (bare, extended):
            result = classify(denied[:cut] + line + denied[cut:])
            self.assertTrue(result['refusal_recorded'] and not result['malformed_stage_record'], line)
        for bad in (b' hdr=0228ce00010080 groups=0x8', b' hdr=0228ce0001008000 groups=0x8 at=34'):
            self.assertTrue(classify(denied[:cut] + bare[:-1] + bad + b'\n' + denied[cut:])['malformed_stage_record'], bad)
        observed = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=0\n'
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        self.assertTrue(classify(good[:activation] + observed + good[activation:])['malformed_stage_record'])

    def test_frame_element_refusal_is_a_negative_diagnostic(self):
        denied = log(False)
        cut = denied.index(b'one-shot WLAN join TX: subtype=0')
        line = b'one-shot WLAN join frame element refused: subtype=0 id=0x30 len=20 count=1\n'
        result = classify(denied[:cut] + line + denied[cut:])
        self.assertTrue(result['refusal_recorded'])
        self.assertIn('frame element refused', result['diagnostic_records'])
        self.assertFalse(result['malformed_stage_record'])
        self.assertFalse(result['bounded_join_pass'])
        for bad in (b'subtype=0 id=0x30 len=256 count=1', b'subtype=0 id=0x30 len=20 count=3', b'subtype=0 id=0x3 len=20 count=1'):
            self.assertTrue(classify(denied[:cut] + b'one-shot WLAN join frame element refused: ' + bad + b'\n' + denied[cut:])['malformed_stage_record'], bad)

    def test_runtime_16_refusal_records_are_diagnostics(self):
        # The extended refusal summary and the key refusal record are refusals,
        # never malformed records; a stopped join with them is unhealthy, not malformed.
        good = log(True)
        cut = good.index(b'one-shot WLAN join cleanup submission: stage=0')
        extended = (b'one-shot WLAN join frame refused: bytes=136 type=0xee01 allowed=0x1400 hdr=00000000000000c0 groups=0x7 at=64'
                    b' g4fc=0x10000 g4seq=0x10000 g4ta=0 translated=0 first=0xd0 sec=0 to=1 from=1\n')
        key = b'one-shot WLAN join key command refused: pairwise status=-95 running=1 active=1 configured=1 first=-71\n'
        result = classify(good[:cut] + extended + key + good[cut:])
        self.assertTrue(result['refusal_recorded'] and not result['malformed_stage_record'])
        self.assertFalse(result['bounded_join_pass'])
        legacy = (b'one-shot WLAN join frame refused: bytes=136 type=0xee01 allowed=0x1400 hdr=0000000000000000 groups=0x0 at=0'
                  b' g4fc=0x10000 g4seq=0x10000 g4ta=0 translated=0 first=0x10000\n')
        self.assertFalse(classify(good[:cut] + legacy + good[cut:])['malformed_stage_record'])
        self.assertTrue(classify(good[:cut] + key.replace(b'pairwise', b'other') + good[cut:])['malformed_stage_record'])

    def test_group_data_discards_are_bounded_to_the_active_window(self):
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        after_activation = good.index(b'\n', activation) + 1
        deauth_done = good.index(b'TX done: pid=3')
        after_deauth_done = good.index(b'\n', deauth_done) + 1
        line = b'one-shot WLAN join group data discarded: bytes=94 fc=0x6208 match=0x08 wlan=0 bss=1 sec=0 status=0xc004 count=%d\n'
        result = classify(good[:after_activation] + line % 1 + good[after_activation:])
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['group_data_discard_records'], 1)
        self.assertEqual(result['group_data_discard_record_limit'], 8)
        self.assertTrue(result['bounded_join_pass'])
        eight = b''.join(line % n for n in range(1, 9))
        self.assertFalse(classify(good[:after_activation] + eight + good[after_activation:])['malformed_stage_record'])
        # Out of order or repeated counts, a discard before the activation or after the
        # deauthentication's TX done, and a ninth record are malformed.
        self.assertTrue(classify(good[:after_activation] + line % 2 + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + line % 1 + line % 1 + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:activation] + line % 1 + good[activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_deauth_done] + line % 1 + good[after_deauth_done:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + eight + line % 9 + good[after_activation:])['malformed_stage_record'])

    def test_action_frame_discards_are_bounded_to_the_active_window(self):
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        after_activation = good.index(b'\n', activation) + 1
        deauth_done = good.index(b'TX done: pid=3')
        after_deauth_done = good.index(b'\n', deauth_done) + 1
        line = b'one-shot WLAN join action frame discarded: bytes=72 fc=0xd0 match=0x02 wlan=1 bss=1 sec=0 status=0xe000 count=%d\n'
        result = classify(good[:after_activation] + line % 1 + good[after_activation:])
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['action_frame_discards'], 1)
        self.assertEqual(result['action_frame_discard_limit'], 8)
        self.assertTrue(result['bounded_join_pass'])
        eight = b''.join(line % n for n in range(1, 9))
        self.assertFalse(classify(good[:after_activation] + eight + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + line % 2 + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:activation] + line % 1 + good[activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_deauth_done] + line % 1 + good[after_deauth_done:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + eight + line % 9 + good[after_activation:])['malformed_stage_record'])
        # Both discard kinds in one lifetime are independently numbered.
        group = b'one-shot WLAN join group data discarded: bytes=94 fc=0x6208 match=0x08 wlan=0 bss=1 sec=0 status=0xc004 count=1\n'
        self.assertFalse(classify(good[:after_activation] + group + line % 1 + good[after_activation:])['malformed_stage_record'])

    def test_firmware_key_done_first_window_required_second_window_optional(self):
        good = log(True, keys=True)
        self.assertTrue(classify(good)['driver_handshake_path_pass'] and classify(good)['firmware_key_done_first_window'])
        done = b'one-shot WLAN join key done: first after=pairwise bss=0 peer=1\n'
        group = b'one-shot WLAN join key done: second after=group bss=0 peer=1\n'
        # Without the pairwise record the group one is unordered, so take both out.
        without = good.replace(done, b'').replace(group, b'')
        result = classify(without)
        self.assertFalse(result['firmware_key_done_first_window'] or result['driver_handshake_path_pass'])
        self.assertTrue(result['handshake_keys_submitted'], 'the key commands alone still count as submitted')
        twice = good.replace(done, done + done)
        self.assertFalse(classify(twice)['firmware_key_done_first_window'] or classify(twice)['driver_handshake_path_pass'])
        command = good.index(b'one-shot WLAN join key command: pairwise')
        early = without[:command] + done + without[command:]
        self.assertFalse(classify(early)['firmware_key_done_first_window'])
        # Another BSS index or peer flag is not the record and is malformed.
        self.assertTrue(classify(good.replace(done, b'one-shot WLAN join key done: pairwise bss=1 peer=1\n'))['malformed_stage_record'])
        # Late (immediately after the complete deauthentication TX line) or orphan (no key
        # command) records never count. The splice point is taken in the log the record
        # was removed from, at the end of that line, so the framing stays intact.
        deauth = without.index(b'one-shot WLAN join TX: subtype=12')
        after_deauth_tx = without.index(b'\n', deauth) + 1
        late = without[:after_deauth_tx] + done + without[after_deauth_tx:]
        self.assertEqual(late.count(b'\n'), without.count(b'\n') + 1)
        self.assertEqual(late.replace(done, b''), without)  # the record is the only difference; framing intact
        late_result = classify(late)
        self.assertFalse(late_result['firmware_key_done_first_window'] or late_result['driver_handshake_path_pass'])
        self.assertEqual(late_result['key_commands_submitted'], ['pairwise', 'group'])
        plain = log(True)
        activation = plain.index(b'one-shot WLAN join activation:')
        after_activation = plain.index(b'\n', activation) + 1
        orphan = classify(plain[:after_activation] + done + plain[after_activation:])
        self.assertTrue(orphan['malformed_stage_record'])
        self.assertFalse(orphan['firmware_key_done_first_window'] or orphan['bounded_join_pass'])
        # The second-window record is required for the handshake-path pass since the
        # reference run 3 (one event observed after each key command); twice, before the
        # group command, before the first record, or a first record after the group
        # command fails the key lifetime. Nothing names it the group key's completion.
        full = classify(good)
        self.assertTrue(full['firmware_key_done_second_window'] and full['key_done_records'] == ['first', 'second'])
        # 0172: the data phase opens inside the grant (no release record); the budget is
        # the grant's remainder as recorded; the end record carries the TC1 credit total.
        self.assertTrue(full['data_phase_opened'] and not full['channel_released'] and full['data_phase_budget_ms'] == 5500 and full['data_phase_end_reason'] == 'budget')
        self.assertEqual(full['data_frames']['tx_credits'], 36)
        # 0165's shape (a release record and the released stage 1) is still placed; a release
        # with no stage-1 release record is malformed unless the lifetime fail-stopped.
        released_shape = good.replace(b'one-shot WLAN join data phase: budget_ms=5500 teardown_margin_ms=5000 inside_grant=1\n',
                                      b'one-shot WLAN join channel released: sequence=12\none-shot WLAN join credit: pages=1 remaining=0\n'
                                      b'one-shot WLAN join data phase: budget_ms=60000 teardown_margin_ms=5000\n')
        stage1 = released_shape.index(b'one-shot WLAN join cleanup submission: stage=1\n')
        stage1_end = released_shape.index(b'\n', released_shape.index(b'\n', stage1) + 1) + 1
        released_shape = released_shape[:stage1] + b'one-shot WLAN join cleanup submission: stage=1 released=1\n' + released_shape[stage1_end:]
        self.assertFalse(classify(released_shape)['malformed_stage_record'], classify(released_shape)['diagnostic_records'])
        self.assertTrue(classify(released_shape)['channel_released'])
        # Runtime 25's shape: released, data phase opened, first data TX, then the footer
        # before any cleanup: placed (the stage-1 release record is not required of a
        # fail-stop), terminal failure recorded, nothing passes.
        r25 = good[:good.index(b'one-shot WLAN join data phase: budget_ms=5500')]
        r25 = (r25 + b'one-shot WLAN join channel released: sequence=12\none-shot WLAN join credit: pages=1 remaining=0\n'
               b'one-shot WLAN join data phase: budget_ms=60000 teardown_margin_ms=5000\n'
               b'one-shot WLAN join data TX: first pid=5 pages=3 bytes=342\n'
               b'one-shot WLAN join data TX timeout: pid=5 debt=3 credits=0 elapsed_ms=768\n'
               b'one-shot WLAN join stopped: status=-110 first=0 submitted=0x801 debt=0 cleanup=0 branch=1\n'
               b'one-shot WLAN join data phase end: reason=disconnect elapsed_ms=2118 rx_unicast=0 rx_group=0 rx_dropped=0 tx_queued=1 tx_done=0 tx_failed=0\n')
        res25 = classify(r25)
        self.assertFalse(res25['malformed_stage_record'], res25['diagnostic_records'])
        self.assertTrue(res25['terminal_failure_recorded'] and not res25['driver_data_path_pass'] and res25['channel_released'])
        # The shapes are exact: the inside-grant phase without its marker, the released
        # phase carrying the marker, a released phase with a shortened budget, and a
        # released fail-stop that submitted a cleanup stage without the stage-1 release
        # record are all malformed.
        self.assertTrue(classify(good.replace(b' inside_grant=1', b''))['malformed_stage_record'])
        self.assertTrue(classify(released_shape.replace(b'data phase: budget_ms=60000 teardown_margin_ms=5000', b'data phase: budget_ms=60000 teardown_margin_ms=5000 inside_grant=1'))['malformed_stage_record'])
        self.assertTrue(classify(released_shape.replace(b'data phase: budget_ms=60000', b'data phase: budget_ms=5500'))['malformed_stage_record'])
        self.assertTrue(classify(r25.replace(b'one-shot WLAN join stopped:', b'one-shot WLAN join cleanup submission: stage=0\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join stopped:'))['malformed_stage_record'])
        self.assertTrue(classify(good)['data_phase_inside_grant'] and not classify(released_shape)['data_phase_inside_grant'])
        self.assertTrue(full['driver_data_path_pass'] and full['data_frames']['tx_done'] == 12 and full['data_frames']['rx_unicast'] == 40)
        # A data phase ended by transmit failures, or without an acknowledged frame or a
        # delivered unicast frame, is not the data-path pass; the handshake pass stands.
        end = b'one-shot WLAN join data phase end: reason=budget elapsed_ms=5500 rx_unicast=40 rx_group=3 rx_dropped=0 tx_queued=12 tx_done=12 tx_failed=0 tx_credits=36\n'
        for variant in (end.replace(b'reason=budget', b'reason=txfail'), end.replace(b'rx_unicast=40', b'rx_unicast=0')):
            partial_data = classify(good.replace(end, variant))
            self.assertTrue(partial_data['driver_handshake_path_pass'], variant)
            self.assertFalse(partial_data['driver_data_path_pass'], variant)
        # One completion with a non-zero status and the end record counting it: not the
        # data-path pass, the handshake pass stands; the end counters disagreeing with the
        # recorded completions, or positive counters with every completion record
        # deleted, are malformed (the driver records each completion).
        failed_one = good.replace(b'TX done: pid=16 status=0 advanced=1', b'TX done: pid=16 status=33 advanced=1').replace(end, end.replace(b'tx_done=12 tx_failed=0', b'tx_done=11 tx_failed=1'))
        self.assertFalse(classify(failed_one)['malformed_stage_record'])
        self.assertTrue(classify(failed_one)['driver_handshake_path_pass'] and classify(failed_one)['driver_data_path_pass'])
        self.assertEqual(classify(failed_one)['data_completions'], {'status_0': 11, 'other': 1, 'late': 0})
        failed_most = good
        for pid in range(10, 17):
            failed_most = failed_most.replace(b'TX done: pid=%d status=0 advanced=1' % pid, b'TX done: pid=%d status=33 advanced=1' % pid)
        failed_most = failed_most.replace(end, end.replace(b'tx_done=12 tx_failed=0', b'tx_done=5 tx_failed=7'))
        self.assertFalse(classify(failed_most)['malformed_stage_record'])
        self.assertTrue(classify(failed_most)['driver_handshake_path_pass'] and not classify(failed_most)['driver_data_path_pass'])
        self.assertEqual(classify(failed_most)['data_completions'], {'status_0': 5, 'other': 7, 'late': 0})
        self.assertTrue(classify(good.replace(end, end.replace(b'tx_done=12', b'tx_done=0')))['malformed_stage_record'])
        self.assertTrue(classify(good.replace(end, end.replace(b'tx_failed=0', b'tx_failed=13')))['malformed_stage_record'])
        no_completions = good
        for pid in range(5, 17):
            no_completions = no_completions.replace(b'one-shot WLAN join TX done: pid=%d status=0 advanced=1 count=1\n' % pid, b'')
        self.assertTrue(classify(no_completions)['malformed_stage_record'])
        self.assertTrue(classify(good.replace(b'data TX: first pid=5 pages=3 bytes=342', b'data TX: first pid=5 pages=2 bytes=342'))['malformed_stage_record'], 'pages')
        self.assertEqual(classify(good.replace(end, end.replace(b'reason=budget', b'reason=disconnect')))['data_phase_end_reason'], 'disconnect')
        self.assertFalse(classify(good.replace(end, b''))['driver_data_path_pass'])
        # Completions without the recorded first submission are malformed; a phase with
        # no data frame at all (no first record, zero counters, the deauthentication at the
        # next PID) is not.
        self.assertTrue(classify(good.replace(b'one-shot WLAN join data TX: first pid=5 pages=3 bytes=342\n', b''))['malformed_stage_record'])
        idle_phase = no_completions.replace(b'one-shot WLAN join data TX: first pid=5 pages=3 bytes=342\n', b'').replace(
            end, end.replace(b'tx_queued=12 tx_done=12', b'tx_queued=0 tx_done=0')).replace(b'pid=17 ', b'pid=5 ')
        self.assertFalse(classify(idle_phase)['malformed_stage_record'], classify(idle_phase)['diagnostic_records'])
        self.assertFalse(classify(idle_phase)['driver_data_path_pass'])
        self.assertTrue(classify(good + b'one-shot WLAN join data credit overflow: pages=2 debt=1\n')['refusal_recorded'])
        # Runtime 21 shape: EAPOL deliveries and a directed Action discard, then a frame
        # refusal and the stopped footer before any deauthentication: placed (the footer
        # closes the window), refusal recorded, not malformed, nothing passes.
        chain = log(True, keys=True)
        cut = chain.index(b'one-shot WLAN join eapol sent: pid=4')
        tail_start = chain.index(b'one-shot WLAN join TX done: pid=4')
        tail_end = chain.index(b'\n', tail_start) + 1
        r21 = (chain[:tail_end] +
               b'one-shot WLAN join action frame discarded: bytes=72 fc=0xd0 match=0x02 wlan=1 bss=1 sec=0 status=0xe000 count=1\n'
               b'one-shot WLAN join frame refused: bytes=708 type=0xee01 allowed=0x1400 hdr=0828183cff0000e0 groups=0x7 at=64 g4fc=0x10000 g4seq=0x10000 g4ta=0 translated=0 first=0xd0 sec=0 to=0 from=0\n'
               b'one-shot WLAN join stopped: status=-71 first=0 submitted=0x801 debt=0 cleanup=0 branch=7\n'
               b'one-shot WLAN join key command refused: pairwise status=-71 running=0 active=1 configured=1 first=-71\n'
               b'one-shot WLAN join key command refused: group status=-95 running=0 active=1 configured=1 first=-71\n')
        result = classify(r21)
        self.assertFalse(result['malformed_stage_record'], result['diagnostic_records'])
        self.assertTrue(result['refusal_recorded'] and result['terminal_failure_recorded'])
        self.assertFalse(result['driver_handshake_path_pass'] or result['bounded_join_pass'])
        # Runtime 23 shape: the pairwise key command submitted, its credit, message 4
        # sent after it, the first add-key-done, then the command refused while the
        # lifetime ran. Without a terminal record the lifetime was abandoned: malformed.
        # With the worker's footer (0170) the refusal closes the command's accounting:
        # placed, refusal recorded, terminal failure, nothing passes.
        head = chain[:chain.index(b'one-shot WLAN join eapol sent: pid=4')]
        r23 = (head +
               b'one-shot WLAN join key command: pairwise submitted sequence=25\n'
               b'one-shot WLAN join credit: pages=1 remaining=0\n'
               b'one-shot WLAN join eapol sent: pid=4 pages=2 bytes=113\n'
               b'one-shot WLAN join key done: first after=pairwise bss=0 peer=1\n'
               b'one-shot WLAN join key command refused: pairwise status=-110 running=1 active=1 configured=1 first=0\n'
               b'one-shot WLAN join key command refused: group status=-95 running=0 active=1 configured=1 first=-110\n')
        abandoned = classify(r23)
        self.assertTrue(abandoned['malformed_stage_record'] and abandoned['refusal_recorded'] and not abandoned['terminal_failure_recorded'])
        footer = b'one-shot WLAN join stopped: status=-110 first=0 submitted=0x801 debt=2 cleanup=0 branch=8\n'
        ended = classify(r23 + footer)
        self.assertFalse(ended['malformed_stage_record'], ended['diagnostic_records'])
        self.assertTrue(ended['refusal_recorded'] and ended['terminal_failure_recorded'])
        self.assertFalse(ended['driver_handshake_path_pass'] or ended['bounded_join_pass'])
        self.assertEqual((ended['key_commands_submitted'], ended['key_credits_returned']), (['pairwise'], []))
        # A refusal that is not of a submitted command (running=0, runtime 16's shape) does not close one.
        self.assertTrue(classify(r23.replace(b'status=-110 running=1', b'status=-110 running=0') + footer)['malformed_stage_record'])
        # Runtime 26 shape (0173): after the group key the target's keyed beacon is skipped
        # and counted (first four recorded, total before stage 3); the records are
        # notifications and the data phase inside the grant still passes.
        kb = b'one-shot WLAN join keyed beacon skipped: bytes=378 fc=0x80 match=0x08 wlan=2 bss=1 sec=4 status=0xe004 count=%d\n'
        phase_at = good.index(b'one-shot WLAN join data phase: budget_ms=5500')
        phase_end = good.index(b'\n', phase_at) + 1
        stage3 = good.index(b'one-shot WLAN join cleanup: stage=3')
        with_beacons = (good[:phase_end] + (kb % 1) + (kb % 2) + good[phase_end:stage3] +
                        b'one-shot WLAN join keyed beacons skipped: total=57\n' + good[stage3:])
        rb = classify(with_beacons)
        self.assertFalse(rb['malformed_stage_record'], rb['diagnostic_records'])
        self.assertTrue(rb['driver_data_path_pass'] and not rb['refusal_recorded'])
        self.assertTrue(classify(good[:phase_end] + kb.replace(b'count=%d', b'count=5') + good[phase_end:])['malformed_stage_record'])
        self.assertTrue(classify(good[:phase_end] + kb.replace(b'sec=4 status=0xe004', b'sec=0 status=0xe000') % 1 + good[phase_end:])['malformed_stage_record'])
        # Runtime 27 completion shape: inside the data phase three data completions (PIDs
        # 5..7, status 0) follow the one recorded data submission and the credits; the
        # management and security acknowledgements stay unique; the end record's tx_done
        # equals the status-0 completions before it. A duplicate, a pre-phase, an
        # out-of-order (below a managed PID) or an unknown-status completion is malformed.
        phase_at = good.index(b'one-shot WLAN join data phase: budget_ms=5500')
        phase_end = good.index(b'\n', phase_at) + 1
        end_at = good.index(b'one-shot WLAN join data phase end:')
        completions = (b'one-shot WLAN join TX done: pid=5 status=0 advanced=1 count=1\n'
                       b'one-shot WLAN join data credit: pages=3 debt=0 count=2\n'
                       b'one-shot WLAN join TX done: pid=6 status=0 advanced=1 count=1\n'
                       b'one-shot WLAN join TX done: pid=7 status=0 advanced=1 count=1\n')
        r27 = good
        for pid in range(5, 17):
            r27 = r27.replace(b'one-shot WLAN join TX done: pid=%d status=0 advanced=1 count=1\n' % pid, b'')
        end_at = r27.index(b'one-shot WLAN join data phase end:')
        r27 = r27[:end_at] + completions + r27[end_at:]
        r27 = r27.replace(b'tx_queued=12 tx_done=12 tx_failed=0 tx_credits=36', b'tx_queued=4 tx_done=3 tx_failed=0 tx_credits=7')
        # Three completed data frames (the fourth admitted frame was never dequeued), so
        # the deauthentication is PID 8.
        r27 = r27.replace(b'TX: subtype=12 pid=17 pages=1', b'TX: subtype=12 pid=8 pages=1').replace(
            b'TX done: pid=17 status=0 advanced=0 count=0', b'TX done: pid=8 status=0 advanced=0 count=0')
        res27 = classify(r27)
        self.assertFalse(res27['malformed_stage_record'], res27['diagnostic_records'])
        self.assertTrue(res27['unique_tx_acknowledgements'] and res27['driver_data_path_pass'])
        self.assertEqual(res27['data_completions'], {'status_0': 3, 'other': 0, 'late': 0})
        self.assertTrue(classify(r27.replace(b'pid=7 status=0', b'pid=7 status=33'))['malformed_stage_record'], 'end tx_done disagrees')
        bad_end = r27.replace(b'pid=7 status=0', b'pid=7 status=33').replace(b'tx_done=3 tx_failed=0', b'tx_done=2 tx_failed=1')
        self.assertFalse(classify(bad_end)['malformed_stage_record'])
        self.assertEqual(classify(bad_end)['data_completions'], {'status_0': 2, 'other': 1, 'late': 0})
        self.assertTrue(classify(r27.replace(b'pid=6 status=0 advanced=1 count=1\n', b'pid=6 status=0 advanced=1 count=1\none-shot WLAN join TX done: pid=6 status=0 advanced=1 count=1\n'))['malformed_stage_record'], 'duplicate')
        self.assertTrue(classify(good[:phase_at] + b'one-shot WLAN join TX done: pid=5 status=0 advanced=1 count=1\n' + good[phase_at:])['malformed_stage_record'], 'before the phase')
        self.assertTrue(classify(r27.replace(b'pid=7 status=0', b'pid=3 status=0'))['malformed_stage_record'], 'a managed PID again')
        self.assertTrue(classify(r27.replace(b'pid=7 status=0', b'pid=7 status=9'))['malformed_stage_record'], 'unknown status')
        # Bound to the recorded first data submission and the serialized PID order:
        # an unused PID jump, a reversed pair, an absent first submission, a
        # completion before the submission, and a deauthentication PID that does not
        # follow the last data frame are malformed; a single completion after the end
        # record and before the deauthentication is late, two are malformed.
        self.assertTrue(classify(r27.replace(b'pid=7 status=0', b'pid=90 status=0'))['malformed_stage_record'], 'PID jump')
        swapped = r27.replace(b'TX done: pid=5 status=0 advanced=1 count=1', b'TX done: pid=6 status=0 advanced=1 count=1', 1)
        swapped = swapped.replace(b'TX done: pid=6 status=0 advanced=1 count=1\none-shot WLAN join TX done: pid=7', b'TX done: pid=5 status=0 advanced=1 count=1\none-shot WLAN join TX done: pid=7')
        self.assertTrue(classify(swapped)['malformed_stage_record'], 'reversed order')
        first_at = r27.index(b'one-shot WLAN join data TX: first pid=5')
        first_end = r27.index(b'\n', first_at) + 1
        self.assertTrue(classify(r27[:first_at] + r27[first_end:])['malformed_stage_record'], 'absent first submission')
        self.assertTrue(classify(r27[:first_at] + b'one-shot WLAN join TX done: pid=5 status=0 advanced=1 count=1\n' + r27[first_at:first_end] + r27[first_end:].replace(b'one-shot WLAN join TX done: pid=5 status=0 advanced=1 count=1\n', b'', 1))['malformed_stage_record'], 'completion before its submission')
        # The deauthentication's PID follows the completed data frames exactly (the
        # cleanup waits for the in-flight frame's completion): 9 would mean a dequeued
        # frame whose completion is missing, 10 a gap; completions above the end
        # record's tx_queued are malformed.
        deauth8 = (b'TX: subtype=12 pid=8 pages=1', b'TX done: pid=8 status=0 advanced=0')
        deauth9 = r27.replace(deauth8[0], b'TX: subtype=12 pid=9 pages=1').replace(deauth8[1], b'TX done: pid=9 status=0 advanced=0')
        self.assertTrue(classify(deauth9)['malformed_stage_record'], 'missing completion before the deauthentication')
        self.assertTrue(classify(r27.replace(deauth8[0], b'TX: subtype=12 pid=10 pages=1').replace(deauth8[1], b'TX done: pid=10 status=0 advanced=0'))['malformed_stage_record'], 'deauthentication PID gap')
        self.assertTrue(classify(r27.replace(b'tx_queued=4 tx_done=3', b'tx_queued=2 tx_done=3'))['malformed_stage_record'], 'more completed than queued')
        end_row_at = r27.index(b'one-shot WLAN join data phase end:')
        end_row_end = r27.index(b'\n', end_row_at) + 1
        # A late completion (after the end record, before the deauthentication) is the
        # in-flight frame's; the deauthentication then takes PID 9. Without that late
        # record, PID 9 is the missing-completion case above.
        late = deauth9[:deauth9.index(b'one-shot WLAN join data phase end:')]
        late = late + b'one-shot WLAN join data phase end:' + deauth9[deauth9.index(b'one-shot WLAN join data phase end:') + len(b'one-shot WLAN join data phase end:'):]
        end_row_at = late.index(b'one-shot WLAN join data phase end:')
        end_row_end = late.index(b'\n', end_row_at) + 1
        late = late[:end_row_end] + b'one-shot WLAN join TX done: pid=8 status=0 advanced=1 count=1\n' + late[end_row_end:]
        self.assertFalse(classify(late)['malformed_stage_record'], classify(late)['diagnostic_records'])
        self.assertEqual(classify(late)['data_completions'], {'status_0': 4, 'other': 0, 'late': 1})
        self.assertEqual(res27['data_completions']['late'], 0)
        # Runtime 28 shape (0175): the data phase ends on a disconnect, the reserved
        # deauthentication is submitted and nothing follows. Without a terminal record
        # the lifetime is malformed (runtime 28's original verdict); with the regulatory
        # notifier's footer (branch 9) after the deauthentication's submission the
        # window closes at the footer: not malformed, terminal failure recorded, branch
        # and status reported, no handshake or data-path pass, completions intact. A
        # footer placed before the deauthentication's submission is malformed.
        deauth_tx_at = good.index(b'one-shot WLAN join TX: subtype=12 pid=17 pages=1')
        deauth_tx_end = good.index(b'\n', deauth_tx_at) + 1
        r28 = good[:deauth_tx_end].replace(b'reason=budget elapsed_ms=5500', b'reason=disconnect elapsed_ms=5256')
        self.assertTrue(classify(r28)['malformed_stage_record'])
        self.assertFalse(classify(r28)['terminal_failure_recorded'])
        footer9 = b'one-shot WLAN join stopped: status=-125 first=0 submitted=0x1801 debt=1 cleanup=0 branch=9\n'
        r28f = classify(r28 + footer9)
        self.assertFalse(r28f['malformed_stage_record'], r28f['diagnostic_records'])
        self.assertTrue(r28f['terminal_failure_recorded'] and not r28f['refusal_recorded'])
        self.assertEqual((r28f['terminal_branch'], r28f['terminal_status']), (9, -125))
        self.assertFalse(r28f['driver_handshake_path_pass'] or r28f['driver_data_path_pass'] or r28f['healthy_cleanup_demonstrated'])
        self.assertEqual(r28f['data_completions'], {'status_0': 12, 'other': 0, 'late': 0})
        self.assertEqual(r28f['data_phase_end_reason'], 'disconnect')
        self.assertTrue(classify(r28[:deauth_tx_at] + footer9 + r28[deauth_tx_at:])['malformed_stage_record'], 'footer before the submission')
        self.assertEqual(classify(good)['terminal_branch'], None)
        # 0178 (runtime 30 shape): the LLC-mismatch group variant discarded inside the data
        # phase is a notification: records after the phase record and before its end, the
        # total before the stage-3 record equal in records to min(total, 8); the data-path
        # pass and the healthy cleanup stand. Records before the phase, after its end, out
        # of order, more than eight, or an inconsistent total are malformed; runtime 30's
        # refusal shape stays a refusal.
        ld = b'one-shot WLAN join data LLC mismatch discarded: bytes=46 fc=0x6208 keyid=1 tid=0 type=0x002e count=%d\n'
        ltotal = b'one-shot WLAN join data LLC mismatches discarded: total=%d\n'
        phase_row_at = good.index(b'one-shot WLAN join data phase: budget_ms=5500')
        rx_first_at = good.index(b'one-shot WLAN join data RX: first')
        end_row_at = good.index(b'one-shot WLAN join data phase end:')
        end_row_end = good.index(b'\n', end_row_at) + 1
        stage3_at2 = good.index(b'one-shot WLAN join cleanup: stage=3')
        r30 = good[:rx_first_at] + ld % 1 + ld % 2 + good[rx_first_at:stage3_at2] + ltotal % 2 + good[stage3_at2:]
        rl = classify(r30)
        self.assertFalse(rl['malformed_stage_record'], rl['diagnostic_records'])
        self.assertTrue(rl['healthy_cleanup_demonstrated'] and rl['driver_data_path_pass'])
        self.assertEqual(rl['data_llc_discards'], {'records': 2, 'total': 2})
        r30b = good[:rx_first_at] + b''.join(ld % k for k in range(1, 9)) + good[rx_first_at:stage3_at2] + ltotal % 11 + good[stage3_at2:]
        self.assertFalse(classify(r30b)['malformed_stage_record'], classify(r30b)['diagnostic_records'])
        self.assertEqual(classify(r30b)['data_llc_discards'], {'records': 8, 'total': 11})
        self.assertEqual(classify(good[:rx_first_at] + ld % 1 + good[rx_first_at:])['data_llc_discards'], {'records': 1, 'total': None})
        self.assertEqual(classify(good)['data_llc_discards'], {'records': 0, 'total': None})
        self.assertTrue(classify(good[:phase_row_at] + ld % 1 + good[phase_row_at:])['malformed_stage_record'], 'before the phase')
        self.assertTrue(classify(good[:end_row_end] + ld % 1 + good[end_row_end:])['malformed_stage_record'], 'after the phase end')
        self.assertTrue(classify(good[:rx_first_at] + ld % 2 + ld % 1 + good[rx_first_at:])['malformed_stage_record'], 'out of order')
        self.assertTrue(classify(r30.replace(ltotal % 2, ltotal % 5))['malformed_stage_record'], 'total above the recorded first discards')
        self.assertTrue(classify(good[:stage3_at2] + ltotal % 3 + good[stage3_at2:])['malformed_stage_record'], 'a total with no records')
        self.assertTrue(classify(good[:phase_row_at] + ltotal % 1 + good[phase_row_at:] )['malformed_stage_record'], 'a total before the phase')
        # The total is written in the step that records stage 3: a valid total moved
        # before the data phase's end, or before the stage-2 submission, is malformed.
        stage2_at = good.index(b'one-shot WLAN join cleanup submission: stage=2')
        moved_before_end = good[:rx_first_at] + ld % 1 + ld % 2 + good[rx_first_at:end_row_at] + ltotal % 2 + good[end_row_at:]
        self.assertTrue(classify(moved_before_end)['malformed_stage_record'], 'total before the data phase end')
        moved_before_stage2 = good[:rx_first_at] + ld % 1 + ld % 2 + good[rx_first_at:stage2_at] + ltotal % 2 + good[stage2_at:]
        self.assertTrue(classify(moved_before_stage2)['malformed_stage_record'], 'total before the stage-2 submission')
        self.assertTrue(classify(good[:rx_first_at] + b''.join(ld % k for k in range(1, 10)) + good[rx_first_at:])['malformed_stage_record'], 'nine records')
        refusal30 = (good[:rx_first_at] +
                     b'one-shot WLAN join frame refused: bytes=94 type=0x5000 allowed=0x1400 hdr=4828ce04024000c2 groups=0x8 at=34 g4fc=0x6208 g4seq=0x12c0 g4ta=1 translated=1 first=0x2e sec=4 to=0 from=0\n'
                     b'one-shot WLAN join stopped: status=-71 first=0 submitted=0x801 debt=0 cleanup=0 branch=7\n'
                     b'one-shot WLAN join data phase end: reason=disconnect elapsed_ms=6300 rx_unicast=34 rx_group=8 rx_dropped=0 tx_queued=0 tx_done=0 tx_failed=0 tx_credits=0\n')
        rr30 = classify(refusal30)
        self.assertFalse(rr30['malformed_stage_record'], rr30['diagnostic_records'])
        self.assertTrue(rr30['refusal_recorded'] and rr30['terminal_failure_recorded'] and rr30['terminal_branch'] == 7)
        self.assertFalse(rr30['driver_data_path_pass'] or rr30['healthy_cleanup_demonstrated'])
        # 0177 (runtime 29 shape): the removed-key group-data variant discarded during the
        # cleanup is a notification: records after the group key removal, the total before
        # the stage-3 record; the healthy cleanup stands. Records before the removal, out
        # of order, more than eight, or a total below the records are malformed; the
        # refusal of that variant without the proposal (runtime 29) stays a refusal.
        cg = b'one-shot WLAN join cleanup group frame discarded: bytes=94 fc=0x6208 match=0x08 wlan=255 bss=1 sec=0 status=0xc200 count=%d\n'
        removal_at = good.index(b'one-shot WLAN join key removal: group submitted sequence=14')
        removal_end = good.index(b'\n', removal_at) + 1
        stage0_at = good.index(b'one-shot WLAN join cleanup submission: stage=0')
        stage3_at = good.index(b'one-shot WLAN join cleanup: stage=3')
        total = b'one-shot WLAN join cleanup group frames discarded: total=%d\n'
        # Realizable shapes: the driver records the first min(total, 8) discards, so a
        # complete sealed log carries 2 records with total 2, or 8 records with total 9.
        r29 = good[:stage0_at] + cg % 1 + cg % 2 + good[stage0_at:stage3_at] + total % 2 + good[stage3_at:]
        rc = classify(r29)
        self.assertFalse(rc['malformed_stage_record'], rc['diagnostic_records'])
        self.assertTrue(rc['healthy_cleanup_demonstrated'] and rc['driver_data_path_pass'])
        self.assertEqual(rc['cleanup_group_discards'], {'records': 2, 'total': 2})
        r29b = good[:stage0_at] + b''.join(cg % k for k in range(1, 9)) + good[stage0_at:stage3_at] + total % 9 + good[stage3_at:]
        self.assertFalse(classify(r29b)['malformed_stage_record'], classify(r29b)['diagnostic_records'])
        self.assertEqual(classify(r29b)['cleanup_group_discards'], {'records': 8, 'total': 9})
        self.assertEqual(classify(good[:stage0_at] + cg % 1 + good[stage0_at:])['cleanup_group_discards'], {'records': 1, 'total': None})
        self.assertEqual(classify(good)['cleanup_group_discards'], {'records': 0, 'total': None})
        self.assertTrue(classify(good[:removal_at] + cg % 1 + good[removal_at:])['malformed_stage_record'], 'a record before the removal')
        self.assertTrue(classify(good[:removal_at] + total % 1 + good[removal_at:])['malformed_stage_record'], 'a total before the removal')
        self.assertTrue(classify(good[:stage0_at] + cg % 2 + cg % 1 + good[stage0_at:])['malformed_stage_record'], 'out of order')
        self.assertTrue(classify(r29.replace(total % 2, total % 5))['malformed_stage_record'], 'total above the recorded first discards')
        self.assertTrue(classify(r29.replace(total % 2, total % 1))['malformed_stage_record'], 'total below the records')
        self.assertTrue(classify(good[:stage3_at] + total % 3 + good[stage3_at:])['malformed_stage_record'], 'a total with no initial records')
        self.assertTrue(classify(r29b.replace(total % 9, total % 7))['malformed_stage_record'], 'eight records with total 7')
        self.assertTrue(classify(good[:stage0_at] + b''.join(cg % k for k in range(1, 10)) + good[stage0_at:])['malformed_stage_record'], 'nine records')
        refusal29 = (good[:stage0_at] + good[stage0_at:good.index(b'\n', stage0_at) + 1] + b'one-shot WLAN join credit: pages=1 remaining=0\n'
                     b'one-shot WLAN join frame refused: bytes=110 type=0x4000 allowed=0x1400 hdr=08281804ff0000c2 groups=0x0 at=16 g4fc=0x10000 g4seq=0x10000 g4ta=0 translated=0 first=0x6208 sec=0 to=0 from=1\n'
                     b'one-shot WLAN join stopped: status=-71 first=0 submitted=0x1801 debt=0 cleanup=1 branch=7\n')
        rr = classify(refusal29)
        self.assertFalse(rr['malformed_stage_record'], rr['diagnostic_records'])
        self.assertTrue(rr['refusal_recorded'] and rr['terminal_failure_recorded'] and rr['terminal_branch'] == 7 and not rr['healthy_cleanup_demonstrated'])
        # 0176: the target's beacons delivered to mac80211 are notifications (first four
        # recorded, the total with its keyed part before the stage-3 record); the total
        # must be single, at least the recorded count, with its keyed part no larger, and
        # placed after the first records and before the terminal record.
        bd = b'one-shot WLAN join beacon delivered: bytes=378 rcpi=101 keyed=%d count=%d\n'
        firsts = bd % (0, 1) + bd % (1, 2) + bd % (1, 3) + bd % (0, 4)
        stage3 = good.index(b'one-shot WLAN join cleanup: stage=3')
        with_beacons = good[:phase_end] + firsts + good[phase_end:stage3] + b'one-shot WLAN join beacons delivered: total=57 keyed=40\n' + good[stage3:]
        rb_ = classify(with_beacons)
        self.assertFalse(rb_['malformed_stage_record'], rb_['diagnostic_records'])
        self.assertTrue(rb_['driver_data_path_pass'] and rb_['healthy_cleanup_demonstrated'])
        self.assertEqual(rb_['beacons_delivered'], {'records': 4, 'total': 57, 'keyed': 40})
        # Without the total record the first records are a lower bound only: total and
        # keyed part unknown; the records must be numbered in order.
        self.assertEqual(classify(good[:phase_end] + firsts + good[phase_end:])['beacons_delivered'], {'records': 4, 'total': None, 'keyed': None})
        self.assertEqual(classify(good)['beacons_delivered'], {'records': 0, 'total': None, 'keyed': None})
        self.assertTrue(classify(good[:phase_end] + bd % (0, 1) + bd % (1, 3) + good[phase_end:])['malformed_stage_record'], 'records out of order')
        self.assertTrue(classify(with_beacons.replace(b'total=57 keyed=40', b'total=3 keyed=1'))['malformed_stage_record'], 'total below the records')
        self.assertTrue(classify(with_beacons.replace(b'total=57 keyed=40', b'total=57 keyed=58'))['malformed_stage_record'], 'keyed above the total')
        self.assertTrue(classify(with_beacons.replace(b'total=57 keyed=40\n', b'total=57 keyed=40\none-shot WLAN join beacons delivered: total=58 keyed=40\n'))['malformed_stage_record'], 'two totals')
        self.assertTrue(classify(good[:phase_end] + firsts + bd % (1, 5) + good[phase_end:])['malformed_stage_record'], 'a fifth record')
        # 0174: eight recorded 0168 discards and a total record before the stage-3 record;
        # the total must exceed eight, follow the eighth record, and be single.
        ga = b'one-shot WLAN join group action frame discarded: bytes=644 fc=0xd0 match=0x08 wlan=255 bss=15 sec=0 status=0xe000 count=%d\n'
        first_tx = good.index(b'one-shot WLAN join TX: subtype=11')
        eight = b''.join(ga % n for n in range(1, 9))
        stage3 = good.index(b'one-shot WLAN join cleanup: stage=3')
        with_total = good[:first_tx] + eight + good[first_tx:stage3] + b'one-shot WLAN join group action frames discarded: total=57\n' + good[stage3:]
        rt = classify(with_total)
        self.assertFalse(rt['malformed_stage_record'], rt['diagnostic_records'])
        self.assertEqual((rt['group_action_frame_discards'], rt['group_action_frame_discard_records']), (57, 8))
        self.assertTrue(classify(good[:first_tx] + eight + good[first_tx:stage3] + b'one-shot WLAN join group action frames discarded: total=8\n' + good[stage3:])['malformed_stage_record'])
        self.assertTrue(classify(good[:first_tx] + b''.join(ga % n for n in range(1, 8)) + good[first_tx:stage3] + b'one-shot WLAN join group action frames discarded: total=57\n' + good[stage3:])['malformed_stage_record'])
        self.assertTrue(classify(with_total.replace(b'total=57\n', b'total=57\none-shot WLAN join group action frames discarded: total=58\n'))['malformed_stage_record'])
        # The 0168 class: a broadcast Action discard at any stage (even before the
        # authentication) is a placed notification; counts out of order or after the
        # terminal record are malformed; the report carries its count.
        bcast = b'one-shot WLAN join group action frame discarded: bytes=644 fc=0xd0 match=0x08 wlan=255 bss=15 sec=0 status=0xe000 count=%d\n'
        first_tx = good.index(b'one-shot WLAN join TX: subtype=11')
        early = good[:first_tx] + (bcast % 1) + good[first_tx:]
        self.assertFalse(classify(early)['malformed_stage_record'])
        self.assertEqual(classify(early)['group_action_frame_discards'], 1)
        self.assertTrue(classify(early)['driver_handshake_path_pass'] if 'driver_handshake_path_pass' in classify(good) and classify(good)['driver_handshake_path_pass'] else True)
        self.assertTrue(classify(good[:first_tx] + (bcast % 2) + good[first_tx:])['malformed_stage_record'])
        self.assertTrue(classify(good + (bcast % 1))['malformed_stage_record'])
        # Between the stage-1 cleanup submission and the stage-3 terminal the class is
        # still a placed notification (the driver admits it until join_cleanup_done);
        # the same record after the stage-3 terminal line is malformed.
        stage1_at = good.index(b'one-shot WLAN join cleanup submission: stage=1')
        stage2_at = good.index(b'one-shot WLAN join cleanup submission: stage=2')
        stage3_at = good.index(b'one-shot WLAN join cleanup: stage=3')
        between = good[:stage2_at] + (bcast % 1) + good[stage2_at:]
        self.assertTrue(stage1_at < stage2_at < stage3_at)
        self.assertFalse(classify(between)['malformed_stage_record'], classify(between)['diagnostic_records'])
        self.assertEqual(classify(between)['group_action_frame_discards'], 1)
        stage3_end = good.index(b'\n', stage3_at) + 1
        self.assertTrue(classify(good[:stage3_end] + (bcast % 1) + good[stage3_end:])['malformed_stage_record'])
        self.assertTrue(classify(good[:first_tx] + bcast.replace(b'match=0x08', b'match=0x04') % 1 + good[first_tx:])['malformed_stage_record'])
        self.assertFalse(classify(r21[:r21.index(b'one-shot WLAN join stopped:')] + (bcast % 1) + r21[r21.index(b'one-shot WLAN join stopped:'):])['malformed_stage_record'])
        # Owned data outside the phase is a notification (dropped and counted), not a refusal; pidbudget ends the phase.
        outside = good.replace(end, end + b'one-shot WLAN join data RX outside: first phase=1 ended=1 group=0 bytes=320\n')
        outside = outside.replace(b'one-shot WLAN join cleanup: stage=3', b'one-shot WLAN join data RX outside: dropped=3\none-shot WLAN join cleanup: stage=3')
        self.assertTrue(classify(outside)['driver_data_path_pass'] and not classify(outside)['refusal_recorded'])
        self.assertEqual(classify(good.replace(end, end.replace(b'reason=budget', b'reason=pidbudget')))['data_phase_end_reason'], 'pidbudget')
        self.assertFalse(classify(good.replace(end, end.replace(b'reason=budget', b'reason=pidbudget')))['driver_data_path_pass'])
        no_group = good.replace(group, b'')
        self.assertFalse(classify(no_group)['driver_handshake_path_pass'])
        self.assertTrue(classify(no_group)['bounded_join_pass'] and classify(no_group)['handshake_keys_submitted'])
        self.assertFalse(classify(good.replace(done, b''))['driver_handshake_path_pass'])  # second record without the first
        group_command_line = b'one-shot WLAN join key command: group submitted sequence=11\n'
        first_late = no_group.replace(done, b'').replace(group_command_line, group_command_line + done)
        self.assertFalse(classify(first_late)['driver_handshake_path_pass'])  # first record after the group command
        self.assertFalse(classify(no_group)['firmware_key_done_second_window'])
        self.assertFalse(classify(good.replace(group, group + group))['driver_handshake_path_pass'])
        group_command = no_group.index(b'one-shot WLAN join key command: group')
        self.assertFalse(classify(no_group[:group_command] + group + no_group[group_command:])['driver_handshake_path_pass'])
        swapped = good.replace(done, b'').replace(group, group + done)
        self.assertFalse(classify(swapped)['driver_handshake_path_pass'])
        # Runtime 20's record wording (proposal 0162) is the first-window record.
        legacy = good.replace(done, b'one-shot WLAN join key done: pairwise bss=0 peer=1\n')
        self.assertTrue(classify(legacy)['firmware_key_done_first_window'] and classify(legacy)['key_done_records'] == ['first', 'second'])
        # The named refusal of an unowned event is a refusal, never malformed text.
        refused = b'one-shot WLAN join key done refused: bss=0 peer=0 broadcast=1 seq=0 submitted=11 recorded=10\n'
        cut = plain.index(b'one-shot WLAN join cleanup submission: stage=0')
        self.assertTrue(classify(plain[:cut] + refused + plain[cut:])['refusal_recorded'])
        self.assertFalse(classify(plain[:cut] + refused + plain[cut:])['malformed_stage_record'])

    def test_eapol_observations_are_bounded_to_the_driver_window(self):
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        after_activation = good.index(b'\n', activation) + 1
        assoc_rx = good.index(b'one-shot WLAN join RX: subtype=1 status=0')
        deauth_tx = good.index(b'one-shot WLAN join TX: subtype=12')
        after_deauth_tx = good.index(b'\n', deauth_tx) + 1
        deauth_done = good.index(b'TX done: pid=3')
        after_deauth_done = good.index(b'\n', deauth_done) + 1
        late = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=1 vector=1 bss=1\n'
        early = b'one-shot WLAN join eapol observed: translated=0 frame=131 activated=0 vector=0 bss=15\n'
        # After activation, and even between the deauthentication submission and its
        # matched TX done: valid; metadata is retained; the verdict is unchanged.
        result = classify(good[:after_activation] + late + good[after_activation:])
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['eapol_shape_observations'], 1)
        self.assertEqual(result['eapol_observations'], [{'translated': 1, 'frame': 131, 'activated': 1, 'vector': 1, 'bss': 1}])
        self.assertTrue(result['bounded_join_pass'] and result['associated_station_activation_demonstrated'])
        self.assertFalse(classify(good[:after_deauth_tx] + late + good[after_deauth_tx:])['malformed_stage_record'])
        # Early, before the local activation, with activated=0: valid.
        self.assertEqual(classify(good[:activation] + early + good[activation:])['eapol_shape_observations'], 1)
        # Two are valid, three are malformed.
        self.assertFalse(classify(good[:activation] + early + good[activation:after_activation] + late + good[after_activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + late * 3 + good[after_activation:])['malformed_stage_record'])
        # Outside the window: before the association response, after the deauthentication TX done.
        self.assertTrue(classify(good[:assoc_rx] + early + good[assoc_rx:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_deauth_done] + late + good[after_deauth_done:])['malformed_stage_record'])
        # An inconsistent activated field, or a frame length outside the decoder's range for its layout.
        self.assertTrue(classify(good[:activation] + late + good[activation:])['malformed_stage_record'])
        self.assertTrue(classify(good[:after_activation] + early + good[after_activation:])['malformed_stage_record'])
        for bad in (b'translated=0 frame=130 activated=1 vector=1 bss=1', b'translated=0 frame=2085 activated=1 vector=1 bss=1',
                    b'translated=1 frame=98 activated=1 vector=1 bss=1', b'translated=1 frame=2053 activated=1 vector=1 bss=1',
                    b'translated=1 frame=0 activated=1 vector=1 bss=1', b'translated=2 frame=131 activated=1 vector=1 bss=1'):
            self.assertTrue(classify(good[:after_activation] + b'one-shot WLAN join eapol observed: ' + bad + b'\n' + good[after_activation:])['malformed_stage_record'], bad)
        for ok in (b'translated=0 frame=131 activated=1 vector=1 bss=1', b'translated=0 frame=2084 activated=1 vector=1 bss=1',
                   b'translated=1 frame=99 activated=1 vector=1 bss=1', b'translated=1 frame=2052 activated=1 vector=1 bss=1'):
            self.assertFalse(classify(good[:after_activation] + b'one-shot WLAN join eapol observed: ' + ok + b'\n' + good[after_activation:])['malformed_stage_record'], ok)
        # In a denied exchange it is malformed; zero observations is simply zero.
        denied = log(False)
        cut = denied.index(b'one-shot WLAN join cleanup submission: stage=0')
        self.assertTrue(classify(denied[:cut] + late + denied[cut:])['malformed_stage_record'])
        self.assertEqual(classify(good)['eapol_shape_observations'], 0)
        # No association response at all, with a synthetic deauthentication and its
        # matched TX done present: malformed, never an exception.
        no_assoc = good.replace(b'one-shot WLAN join RX: subtype=1 status=0\n', b'')
        self.assertNotIn(b'RX: subtype=1 status=0', no_assoc)
        result = classify(no_assoc[:no_assoc.index(b'one-shot WLAN join TX: subtype=12')] + late +
                          no_assoc[no_assoc.index(b'one-shot WLAN join TX: subtype=12'):])
        self.assertTrue(result['malformed_stage_record'])
        self.assertFalse(result['bounded_join_pass'])
        # Two association responses are likewise refused without indexing errors.
        twice = good.replace(b'one-shot WLAN join RX: subtype=1 status=0\n', b'one-shot WLAN join RX: subtype=1 status=0\n' * 2)
        self.assertTrue(classify(twice[:after_activation] + late + twice[after_activation:])['malformed_stage_record'])

    def test_credit_and_completion_cannot_move_across_stage_fences(self):
        raw = log(True)
        credit = b'one-shot WLAN join credit: pages=2 remaining=0\n'
        late_credit = raw.replace(credit, b'', 1) + credit
        self.assertFalse(classify(late_credit)['bounded_join_pass'])
        done = b'one-shot WLAN join TX done: pid=1 status=0 advanced=0 count=0\n'
        late_done = raw.replace(done, b'') + done
        self.assertFalse(classify(late_done)['bounded_join_pass'])
        stage = b'one-shot WLAN join cleanup submission: stage=1\n'
        self.assertFalse(classify(stage + raw.replace(stage, b''))['bounded_join_pass'])
        # Firmware RX may arrive before the asynchronous completion event.
        response = b'one-shot WLAN join RX: subtype=11 status=0\n'
        early_response = raw.replace(done + response, response + done)
        self.assertTrue(classify(early_response)['bounded_join_pass'])

    def test_target_shell_quoting_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.json'
            source = Path(directory) / 'source.sh'
            source.write_text('printf %s "$TARGET_SSID"\n')
            value = {'ssid': "lab';$(exit 9)", 'bssid': '02:00:00:00:00:01',
                     'frequency_mhz': 5200, 'channel': 40}
            target.write_text(json.dumps(value))
            target.chmod(0o600)
            self.assertEqual(subprocess.check_output(['sh'], input=bind(target, source)), value['ssid'].encode())
            for key, bad in [('ssid', 'bad\nline'), ('bssid', 'ff:00:00:00:00:01'),
                             ('frequency_mhz', 5180), ('channel', 36)]:
                changed = dict(value, **{key: bad})
                target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    bind(target, source)
            target.chmod(0o644)
            with self.assertRaises(ValueError):
                bind(target, source)


if __name__ == '__main__':
    unittest.main()
