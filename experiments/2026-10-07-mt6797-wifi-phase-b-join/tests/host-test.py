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
                      'key done: second after=group bss=0 peer=1', 'key credit returned: group']
        lines += ['TX: subtype=12 pid=' + ('5' if keys else '3') + ' pages=1', 'credit: pages=1 remaining=0',
                  'TX done: pid=' + ('5' if keys else '3') + ' status=0 advanced=0 count=0']
        if keys:
            lines += ['key removal: pairwise submitted sequence=12', 'credit: pages=1 remaining=0',
                      'key removal: group submitted sequence=13', 'credit: pages=1 remaining=0']
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
        swapped = raw.replace(b'one-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join TX done: pid=5 status=0 advanced=0 count=0\n',
                              b'one-shot WLAN join TX done: pid=5 status=0 advanced=0 count=0\none-shot WLAN join credit: pages=1 remaining=0\n')
        self.assertNotEqual(swapped, raw)
        self.assertTrue(classify(swapped)['driver_handshake_path_pass'])
        # Missing all removals, or only the group removal missing: not healthy; a partial
        # handshake (pairwise only) with its exact removal is healthy but not a pass.
        no_removals = raw.replace(b'one-shot WLAN join key removal: pairwise submitted sequence=12\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key removal: group submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        self.assertFalse(classify(no_removals)['bounded_join_pass'])
        no_group_removal = raw.replace(b'one-shot WLAN join key removal: group submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        self.assertFalse(classify(no_group_removal)['bounded_join_pass'])
        partial = raw.replace(b'one-shot WLAN join key command: group submitted sequence=11\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key done: second after=group bss=0 peer=1\none-shot WLAN join key credit returned: group\n', b'').replace(
            b'one-shot WLAN join key removal: group submitted sequence=13\none-shot WLAN join credit: pages=1 remaining=0\n', b'')
        partial_result = classify(partial)
        self.assertTrue(partial_result['bounded_join_pass'])
        self.assertFalse(partial_result['handshake_keys_submitted'] or partial_result['driver_handshake_path_pass'])
        # Page arithmetic and sequence ownership: wrong EAPOL page count, duplicate or
        # out-of-order key sequences are malformed.
        self.assertTrue(classify(raw.replace(b'eapol sent: pid=3 pages=2 bytes=135', b'eapol sent: pid=3 pages=1 bytes=135'))['malformed_stage_record'] or
                        not classify(raw.replace(b'eapol sent: pid=3 pages=2 bytes=135', b'eapol sent: pid=3 pages=1 bytes=135'))['bounded_join_pass'])
        self.assertTrue(classify(raw.replace(b'key command: group submitted sequence=11', b'key command: group submitted sequence=10'))['malformed_stage_record'])
        self.assertTrue(classify(raw.replace(b'key removal: group submitted sequence=13', b'key removal: group submitted sequence=9'))['malformed_stage_record'])
        # Group before pairwise, a missing credit, a third security frame, a removal of a
        # key never submitted, or a removal before the deauthentication: not healthy.
        bad = [raw.replace(b'key command: pairwise submitted sequence=10', b'key command: group submitted sequence=10', 1),
               raw.replace(b'one-shot WLAN join key credit returned: group\n', b''),
               raw.replace(b'eapol sent: pid=4 pages=2 bytes=113', b'eapol sent: pid=4 pages=2 bytes=113\none-shot WLAN join eapol sent: pid=6 pages=2 bytes=113'),
               raw.replace(b'one-shot WLAN join key command: group submitted sequence=11\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join key done: second after=group bss=0 peer=1\none-shot WLAN join key credit returned: group\n', b''),
               raw.replace(b'one-shot WLAN join key removal: pairwise submitted sequence=12\none-shot WLAN join credit: pages=1 remaining=0\n', b'').replace(
                   b'one-shot WLAN join TX: subtype=12 pid=5 pages=1\n', b'one-shot WLAN join key removal: pairwise submitted sequence=12\none-shot WLAN join credit: pages=1 remaining=0\none-shot WLAN join TX: subtype=12 pid=5 pages=1\n')]
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
        # The second-window record is reported and optional: absent still passes; twice,
        # before the group command, before the first record, or a first record after the
        # group command fails the key lifetime. Nothing names it the group key's completion.
        full = classify(good)
        self.assertTrue(full['firmware_key_done_second_window'] and full['key_done_records'] == ['first', 'second'])
        no_group = good.replace(group, b'')
        self.assertTrue(classify(no_group)['driver_handshake_path_pass'])
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
