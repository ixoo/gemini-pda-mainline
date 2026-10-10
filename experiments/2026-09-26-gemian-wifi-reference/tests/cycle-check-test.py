#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixture for cycle-check.py: private file validation, SSID escaping, link and service matching, correlation, seal."""
import io
import os
import pathlib
import runpy
import stat
import tempfile
import unittest
import unittest.mock

MOD = runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/cycle-check.py'), run_name='x')
REAL_LSTAT = os.lstat
TARGET = {'ssid': 'Net Work', 'bssid': '02:11:22:33:44:55', 'frequency_mhz': 5200, 'channel': 40}


def link(bssid='02:11:22:33:44:55', ssid='Net Work', freq=5200):
    return ('Connected to %s (on wlan0)\n\tSSID: %s\n\tfreq: %d\n\tRX: 1 bytes (1 packets)\n'
            '\tTX: 1 bytes (1 packets)\n\tsignal: -50 dBm\n\ttx bitrate: 6.0 MBit/s\n\n\tbss flags:\tshort-slot-time\n'
            '\tdtim period:\t1\n\tbeacon int:\t100\n' % (bssid, ssid, freq))


class PrivateFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'ap-target.json')
        with open(self.path, 'w') as handle:
            handle.write('{"ssid": "Net Work", "bssid": "02:11:22:33:44:55", "frequency_mhz": 5200, "channel": 40}\n')
        os.chmod(self.path, 0o600)

    def tearDown(self):
        self.tmp.cleanup()

    def fake_root(self, path):
        real = REAL_LSTAT(path)

        class St:
            st_mode, st_uid, st_gid, st_nlink, st_size = real.st_mode, 0, 0, real.st_nlink, real.st_size
        return St()

    def test_valid_file_loads_with_root_ownership(self):
        with unittest.mock.patch.object(os, 'lstat', self.fake_root):
            self.assertEqual(MOD['load_target'](self.path), TARGET)

    def test_non_root_owner_refused(self):
        if os.getuid() == 0:
            self.skipTest('running as root')
        with self.assertRaises(ValueError) as err:
            MOD['load_target'](self.path)
        self.assertIn('owned', str(err.exception))

    def test_mode_symlink_links_and_schema_refused(self):
        with unittest.mock.patch.object(os, 'lstat', self.fake_root):
            os.chmod(self.path, 0o644)
            with self.assertRaises(ValueError) as err:
                MOD['load_target'](self.path)
            self.assertIn('0600', str(err.exception))
            os.chmod(self.path, 0o600)
            with open(self.path, 'w') as handle:
                handle.write('{"ssid": "x", "bssid": "02:11:22:33:44:55", "frequency_mhz": 5200, "channel": 40, "psk": "no"}\n')
            with self.assertRaises(ValueError) as err:
                MOD['load_target'](self.path)
            self.assertIn('schema', str(err.exception))
            self.assertNotIn('psk', str(err.exception).replace('schema', ''))
            with open(self.path, 'w') as handle:
                handle.write('{"ssid": "x", "bssid": "0211.2233.4455", "frequency_mhz": 5200, "channel": 40}\n')
            with self.assertRaises(ValueError):
                MOD['load_target'](self.path)
            with open(self.path, 'w') as handle:
                handle.write('{"ssid": "x", "bssid": "02:11:22:33:44:55", "frequency_mhz": "5200", "channel": 40}\n')
            with self.assertRaises(ValueError):
                MOD['load_target'](self.path)
        link_path = os.path.join(self.tmp.name, 'link.json')
        os.symlink(self.path, link_path)
        with self.assertRaises(ValueError) as err:
            MOD['private_file'](link_path)
        self.assertIn('regular', str(err.exception))
        hard = os.path.join(self.tmp.name, 'hard.json')
        os.link(self.path, hard)
        with unittest.mock.patch.object(os, 'lstat', self.fake_root):
            with self.assertRaises(ValueError) as err:
                MOD['private_file'](self.path)
            self.assertIn('link', str(err.exception))

    def test_approved_service_shape(self):
        approved = os.path.join(self.tmp.name, 'approved-service')
        for text, ok in (('wifi_0211223344aa_4e657420576f726b_managed_psk\n', True), ('wifi_x\n', False),
                         ('wifi_0211223344aa_4e65_managed_psk\nwifi_0211223344aa_4e66_managed_psk\n', False),
                         ('ethernet_0211223344aa_cable\n', False)):
            with open(approved, 'w') as handle:
                handle.write(text)
            os.chmod(approved, 0o600)
            with unittest.mock.patch.object(os, 'lstat', self.fake_root):
                if ok:
                    self.assertEqual(MOD['load_approved'](approved), text.strip())
                else:
                    with self.assertRaises(ValueError):
                        MOD['load_approved'](approved)


class LinkMatchTest(unittest.TestCase):
    def test_exact_match_and_iw49_escaping(self):
        self.assertTrue(MOD['link_matches'](link(), TARGET))
        # iw 4.9 util.c print_ssid_escaped: interior spaces as spaces; leading and trailing spaces,
        # the backslash, tabs and non-ASCII bytes as \\xNN
        self.assertEqual(MOD['iw_escape']('Net Work'), 'Net Work')
        self.assertEqual(MOD['iw_escape'](' lead'), '\\x20lead')
        self.assertEqual(MOD['iw_escape']('trail '), 'trail\\x20')
        self.assertEqual(MOD['iw_escape'](' '), '\\x20')
        self.assertEqual(MOD['iw_escape']('a\\b'), 'a\\x5cb')
        self.assertEqual(MOD['iw_escape']('a,b\tc é'), 'a,b\\x09c \\xc3\\xa9')
        odd = dict(TARGET, ssid=' a,b\tc\\d é ')
        self.assertTrue(MOD['link_matches'](link(ssid='\\x20a,b\\x09c\\x5cd \\xc3\\xa9\\x20'), odd))
        self.assertFalse(MOD['link_matches'](link(ssid=' a,b\tc\\d é '), odd))

    def test_mismatches(self):
        self.assertFalse(MOD['link_matches'](link(bssid='02:11:22:33:44:56'), TARGET))
        self.assertFalse(MOD['link_matches'](link(ssid='Net Works'), TARGET))
        self.assertFalse(MOD['link_matches'](link(ssid='Net Work '), TARGET))
        self.assertFalse(MOD['link_matches'](link(freq=2437), TARGET))
        self.assertFalse(MOD['link_matches']('Not connected.\n', TARGET))
        self.assertFalse(MOD['link_matches']('', TARGET))
        self.assertFalse(MOD['link_matches'](link().replace('\tSSID', 'SSID'), TARGET))


class KmsgTest(unittest.TestCase):
    def lines(self, items, start=200):
        return ['7,%d,%d,-;%s\n' % (start + i, 1000 + i, m) for i, m in enumerate(items)]

    def test_positive_control_correlates_seq_after_arm(self):
        good = self.lines(['gwref10 arm: deadline_s=240 caps=1/1/1/1/1/1',
                           'gwref10 cmd: n=1 cid=0x81 seq=42 set=0 len=16 bss=0 type=1',
                           'gwref10 event: n=2 eid=0x02 seq=42 len=20 hif=24'])
        self.assertTrue(MOD['positive_control'](good, 200))
        stale = self.lines(['gwref10 cmd: n=1 cid=0x81 seq=42 set=0 len=16 bss=0 type=1',
                            'gwref10 arm: deadline_s=240 caps=1/1/1/1/1/1',
                            'gwref10 event: n=2 eid=0x02 seq=42 len=20 hif=24'])
        self.assertFalse(MOD['positive_control'](stale, 201))
        wrong = self.lines(['gwref10 arm: deadline_s=240 caps=1/1/1/1/1/1',
                            'gwref10 cmd: n=1 cid=0x81 seq=42 set=0 len=16 bss=0 type=1',
                            'gwref10 event: n=2 eid=0x02 seq=43 len=20 hif=24'])
        self.assertFalse(MOD['positive_control'](wrong, 200))
        other = self.lines(['gwref10 arm: deadline_s=240 caps=1/1/1/1/1/1',
                            'gwref10 cmd: n=1 cid=0x82 seq=42 set=0 len=16 bss=0 type=1',
                            'gwref10 event: n=2 eid=0x02 seq=42 len=20 hif=24'])
        self.assertFalse(MOD['positive_control'](other, 200))

    def test_seal_check(self):
        arm = 'gwref10 arm: deadline_s=240 caps=512/1024/1024/2048/1024/256'
        cmd = 'gwref10 cmd: n=1 cid=0x81 seq=42 set=0 len=16 bss=0 type=1'
        sealed = 'gwref10 seal: reason=explicit records=1 truncated=0 cmd=1/0/0 event=0/0/0 credit=0/0/0 rxd=0/3/0 txd=0/0/0 state=0/0/0'
        ok, summary = MOD['seal_check'](self.lines([arm, cmd, sealed]))
        self.assertTrue(ok, summary)
        self.assertEqual((summary['records'], summary['suppressed'], summary['truncated'], summary['complete']), (1, 3, 0, 0))
        self.assertEqual(summary['stream_intact'], 1)
        empty = 'gwref10 seal: reason=explicit records=0 truncated=0 cmd=0/0/0 event=0/0/0 credit=0/0/0 rxd=0/0/0 txd=0/0/0 state=0/0/0'
        ok, summary = MOD['seal_check'](self.lines([arm, empty]))
        self.assertTrue(ok and summary['complete'] == 1)
        ok, summary = MOD['seal_check'](self.lines([arm]))
        self.assertFalse(ok)
        self.assertEqual(summary['seal_reason'], 'missing')
        ok, summary = MOD['seal_check'](self.lines([arm, empty, empty]))
        self.assertFalse(ok)
        self.assertEqual(summary['seal_lines'], 2)
        ok, summary = MOD['seal_check'](self.lines([empty, arm]))        # seal before arm
        self.assertFalse(ok)
        self.assertEqual(summary['arm_before_seal'], 0)
        ok, summary = MOD['seal_check'](self.lines([arm, empty, 'gwref10 cmd: n=9 cid=0x81 seq=1 set=0 len=16 bss=0 type=1']))
        self.assertFalse(ok)
        self.assertEqual(summary['records_after_seal'], 1)
        ok, summary = MOD['seal_check'](self.lines([arm, 'gwref10 seal: reason=explicit records=1 truncated=0 cmd=1/0/0']))  # malformed
        self.assertFalse(ok)
        self.assertEqual(summary['stream_intact'], 0)
        wrong_count = 'gwref10 seal: reason=explicit records=2 truncated=0 cmd=2/0/0 event=0/0/0 credit=0/0/0 rxd=0/0/0 txd=0/0/0 state=0/0/0'
        self.assertFalse(MOD['seal_check'](self.lines([arm, cmd, wrong_count]))[0])
        gap = self.lines([arm, cmd, sealed])
        gap[2] = gap[2].replace(',202,', ',205,')                          # a dropped kmsg line
        self.assertFalse(MOD['seal_check'](gap)[0])
        early = self.lines([arm, cmd, sealed])
        early[2] = early[2][:30]                                           # logger stopped mid-line
        self.assertFalse(MOD['seal_check'](early)[0])

    def test_kmsg_stream_bound_and_signal(self):
        import subprocess, tempfile, time
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'src'); out = os.path.join(tmp, 'out')
            with open(src, 'w') as f:
                f.write('x' * 100)
            rc = subprocess.run(['python3', str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/cycle-check.py'),
                                 'kmsg-stream', src, out, '40'], stdout=subprocess.PIPE, timeout=20)
            self.assertEqual(rc.returncode, 3)
            self.assertEqual(rc.stdout.decode().strip(), 'bytes=40 capped=1 drops=0 failure=none stopped_by=bound')
            self.assertEqual(os.path.getsize(out), 40)
            proc = subprocess.Popen(['python3', str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/cycle-check.py'),
                                     'kmsg-stream', src, out, '1000'], stdout=subprocess.PIPE)
            time.sleep(0.3)
            with open(src, 'a') as f:
                f.write('y' * 10)
            time.sleep(0.3)
            proc.send_signal(15)
            stdout, _ = proc.communicate(timeout=20)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(stdout.decode().strip(), 'bytes=110 capped=0 drops=0 failure=none stopped_by=signal')
            # an idle source (no data ever) stops promptly on SIGTERM with a report, no kill needed
            idle = os.path.join(tmp, 'idle'); open(idle, 'w').close()
            proc = subprocess.Popen(['python3', str(pathlib.Path(__file__).resolve().parent.parent / 'lifecycle/cycle-check.py'),
                                     'kmsg-stream', idle, out, '1000'], stdout=subprocess.PIPE)
            time.sleep(0.3)
            started = time.monotonic()
            proc.send_signal(15)
            stdout, _ = proc.communicate(timeout=5)
            self.assertLess(time.monotonic() - started, 1.0)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(stdout.decode().strip(), 'bytes=0 capped=0 drops=0 failure=none stopped_by=signal')


class CliTest(unittest.TestCase):
    def test_errors_carry_no_identifiers(self):
        with unittest.mock.patch.object(MOD['sys'], 'stdin', io.StringIO('wifi_0211223344aa_4e65_managed_psk')):
            with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as out:
                rc = MOD['main'](['cycle-check', 'service-match'])
        self.assertEqual(rc, 2)
        self.assertIn('check_error=1', out.getvalue())
        self.assertNotIn('4e65', out.getvalue())


if __name__ == '__main__':
    unittest.main()
