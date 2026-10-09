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


def log(accepted):
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
                  'activation: sequence=9 state=3',
                  'TX: subtype=12 pid=3 pages=1', 'credit: pages=1 remaining=0',
                  'TX done: pid=3 status=0 advanced=0 count=0']
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
        late0 = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=1 vector=1 bss=0\n'
        self.assertEqual(classify(good[:activation] + early + good[activation:])['eapol_observations'][0]['bss'], 15)
        self.assertTrue(classify(good[:after_activation] + late15 + good[after_activation:])['malformed_stage_record'])
        self.assertFalse(classify(good[:after_activation] + late0 + good[after_activation:])['malformed_stage_record'])
        for bad in (b'bss=1', b'bss=16', b'bss=3c'):
            self.assertTrue(classify(good[:activation] + early.replace(b'bss=15', bad) + good[activation:])['malformed_stage_record'], bad)

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

    def test_eapol_observations_are_bounded_to_the_driver_window(self):
        good = log(True)
        activation = good.index(b'one-shot WLAN join activation:')
        after_activation = good.index(b'\n', activation) + 1
        assoc_rx = good.index(b'one-shot WLAN join RX: subtype=1 status=0')
        deauth_tx = good.index(b'one-shot WLAN join TX: subtype=12')
        after_deauth_tx = good.index(b'\n', deauth_tx) + 1
        deauth_done = good.index(b'TX done: pid=3')
        after_deauth_done = good.index(b'\n', deauth_done) + 1
        late = b'one-shot WLAN join eapol observed: translated=1 frame=131 activated=1 vector=1 bss=0\n'
        early = b'one-shot WLAN join eapol observed: translated=0 frame=131 activated=0 vector=0 bss=15\n'
        # After activation, and even between the deauthentication submission and its
        # matched TX done: valid; metadata is retained; the verdict is unchanged.
        result = classify(good[:after_activation] + late + good[after_activation:])
        self.assertFalse(result['malformed_stage_record'])
        self.assertEqual(result['eapol_shape_observations'], 1)
        self.assertEqual(result['eapol_observations'], [{'translated': 1, 'frame': 131, 'activated': 1, 'vector': 1, 'bss': 0}])
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
        for bad in (b'translated=0 frame=130 activated=1 vector=1 bss=0', b'translated=0 frame=2085 activated=1 vector=1 bss=0',
                    b'translated=1 frame=98 activated=1 vector=1 bss=0', b'translated=1 frame=2053 activated=1 vector=1 bss=0',
                    b'translated=1 frame=0 activated=1 vector=1 bss=0', b'translated=2 frame=131 activated=1 vector=1 bss=0'):
            self.assertTrue(classify(good[:after_activation] + b'one-shot WLAN join eapol observed: ' + bad + b'\n' + good[after_activation:])['malformed_stage_record'], bad)
        for ok in (b'translated=0 frame=131 activated=1 vector=1 bss=0', b'translated=0 frame=2084 activated=1 vector=1 bss=0',
                   b'translated=1 frame=99 activated=1 vector=1 bss=0', b'translated=1 frame=2052 activated=1 vector=1 bss=0'):
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
