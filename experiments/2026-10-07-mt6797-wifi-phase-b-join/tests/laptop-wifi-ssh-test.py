#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The laptop's two-lifetime Wi-Fi SSH check: the bounded USB probe (boot, fault, open window, fresh listener, admissible address), the attributable Wi-Fi exchange against the device's own cycle marker, the fail-closed guarded USB ack, first-fault/closed stop, no address in the receipt."""
import os
import pathlib
import re
import runpy
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
MOD = runpy.run_path(str(HERE / 'laptop-wifi-ssh.py'), run_name='x')
BOOT = '0123abcd-0123-0123-0123-0123456789ab'
OTHER = 'ffffffff-0123-0123-0123-0123456789ab'
KEYS = pathlib.Path('/private/a53-auth')
ADDR = '192.168.4.20'


class Result:
    def __init__(self, rc, out=b''):
        self.returncode, self.stdout = rc, out


class Clock:
    def __init__(self):
        self.t = 100.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


def cycle_of(arg, infix):
    return int(re.search(r'/c(\d+)/' + infix, arg).group(1))


class Device:
    """A minimal model: per cycle, a sequence of probe states; the (boot, cycle) the device
    serves over Wi-Fi with its listener pid/address; and whether the guarded ack write
    succeeds. The probe emits the hardened grammar (BOOT, DMESG, FATAL, TERM, the ready block,
    LIVE)."""
    def __init__(self, states, serve=None, serve_id=None, ack_rc=0):
        self.states = states
        self.serve = serve or {}             # {cycle: (boot, cycle_marker)}
        self.serve_id = serve_id or {}       # {cycle: (sshd_pid, address)}
        self.ack_rc = ack_rc
        self.acks = []

    def probe_out(self, cycle):
        queue = self.states.get(cycle, [])
        st = queue.pop(0) if len(queue) > 1 else (queue[0] if queue else {})
        boot = st.get('boot', BOOT)
        body = 'BOOT=%s\n' % boot
        if st.get('dmesg', 'ok') == 'ok':
            body += 'FATAL=%s\nTERM=%s\nDMESG=ok\n' % (st.get('fatal', 0), st.get('term', 0))
        else:
            body += 'FATAL=0\nTERM=0\nDMESG=fail\n'
        body += 'READY_BEGIN\n'
        if st.get('ready', False):
            body += 'boot=%s\ncycle=%d\nsshd_pid=1234\naddress=%s\n' % (st.get('ready_boot', BOOT), cycle, st.get('addr', ADDR))
        body += 'READY_END\n'
        live = '1' if (st.get('ready', False) and st.get('live', True)) else '0'
        body += 'LIVE=%s\n' % live
        return Result(0, body.encode())

    def exchange_out(self, cycle):
        boot, marker = self.serve.get(cycle, (BOOT, cycle))
        pid, addr = self.serve_id.get(cycle, ('1234', ADDR))
        return Result(0, ('%s\n%s\nboot=%s\ncycle=%d\nsshd_pid=%s\naddress=%s\n'
                          % (boot, MOD['MARKER'], boot, marker, pid, addr)).encode())

    def runner(self):
        def run(cmd, **kw):
            arg = cmd[-1]
            if 'host-ack' in arg:
                c = cycle_of(arg, 'host-ack')
                if self.ack_rc == 0:
                    self.acks.append(c)
                return Result(self.ack_rc)
            if 'printf BOOT=' in arg:
                return self.probe_out(cycle_of(arg, 'ready'))
            if MOD['MARKER'] in arg:
                return self.exchange_out(cycle_of(arg, 'ready'))
            raise AssertionError('unexpected command: ' + arg)
        return run


MARKER = MOD['MARKER']
READY = {'ready': True}





class WifiSsh(unittest.TestCase):
    def test_cycle_probe_exchange_and_guarded_ack(self):
        clock = Clock()
        dev = Device({1: [{}, {}, READY]})  # ready after two polls
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ready_seen'] and receipt['ssh_attempted'])
        self.assertTrue(receipt['boot_match'] and receipt['ack_written'] and not receipt['closed'])
        self.assertEqual(receipt['ready_wait_s'], 0.4)  # two short 0.2 s polls
        self.assertEqual(dev.acks, [1])
        self.assertNotIn(ADDR, ' '.join('%s=%s' % kv for kv in receipt.items()))  # no address in the receipt
        # The probe, the Wi-Fi command and the ack are well-formed with the baseline options.
        base, target = MOD['base_command'](KEYS)
        wifi = MOD['wifi_command'](KEYS, ADDR, 1)
        self.assertEqual(wifi[:len(base)], base)
        self.assertIn('HostKeyAlias=' + target.split('@')[1], wifi)
        self.assertIn(MOD['MARKER'], wifi[-1])
        self.assertIn('/c1/ready', wifi[-1])
        self.assertIn('host_ack boot=' + BOOT + ' cycle=1 ssh_exit=0', MOD['ack_argument'](BOOT, 1))
        self.assertIn('[ ! -e', MOD['ack_argument'](BOOT, 1))  # refuses an existing leaf

    def test_fault_closes_the_cycle_and_stops_without_exchange_or_ack(self):
        clock = Clock()
        dev = Device({1: [{'fatal': 1}]})
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['closed'] and not receipt['ssh_attempted'] and not receipt['ack_written'])
        self.assertIn('fault', receipt['reason'])
        self.assertEqual(dev.acks, [])

    def test_reached_terminal_closes_the_window(self):
        clock = Clock()
        dev = Device({1: [{'term': 1}]})  # this cycle's stage-3 already reached
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['closed'] and not receipt['ssh_attempted'])
        self.assertIn('window has closed', receipt['reason'])

    def test_wifi_marker_mismatch_is_not_a_match_and_writes_no_ack(self):
        clock = Clock()
        dev = Device({1: [READY]}, serve={1: (BOOT, 2)})  # device serves cycle=2 marker
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ssh_attempted'] and not receipt['boot_match'] and not receipt['ack_written'])
        self.assertEqual(dev.acks, [])
        dev = Device({1: [READY]}, serve={1: (OTHER, 1)})  # device serves a foreign boot
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['boot_match'] or receipt['ack_written'])

    def test_ack_refused_by_the_guard_fails_the_cycle(self):
        clock = Clock()
        dev = Device({1: [READY]}, ack_rc=12)  # device guard: stage-3 terminal reached between
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['boot_match'] and not receipt['ack_written'])
        self.assertIn('refused by the device guard', receipt['reason'])

    def test_two_cycles_both_acknowledged(self):
        clock = Clock()
        dev = Device({1: [READY], 2: [READY]})
        out = MOD['run'](KEYS, BOOT, 2, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(out['all_pass'])
        self.assertEqual([r['cycle'] for r in out['cycles']], [1, 2])
        self.assertEqual(dev.acks, [1, 2])

    def test_first_failed_cycle_stops_the_run(self):
        clock = Clock()
        dev = Device({1: [{'fatal': 1}], 2: [READY]})
        out = MOD['run'](KEYS, BOOT, 2, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(out['all_pass'])
        self.assertEqual(len(out['cycles']), 1)
        self.assertTrue(out['cycles'][0]['closed'])
        self.assertEqual(dev.acks, [])

    def test_boot_mismatch_is_a_stop_condition(self):
        clock = Clock()
        dev = Device({1: [{'boot': OTHER}]})
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['closed'] and not receipt['ssh_attempted'])
        self.assertIn('live boot differs', receipt['reason'])

    def test_unreliable_dmesg_snapshot_never_proceeds_to_an_exchange(self):
        clock = Clock()
        dev = Device({1: [{'dmesg': 'fail', 'ready': True}]}, )
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 10, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['ready_seen'] or receipt['ssh_attempted'] or receipt['closed'])
        self.assertEqual(dev.acks, [])

    def test_dead_listener_is_not_ready(self):
        clock = Clock()
        dev = Device({1: [{'ready': True, 'live': False}]})
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 10, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['ready_seen'] or receipt['ssh_attempted'])
        self.assertEqual(dev.acks, [])

    def test_served_identity_must_match_the_usb_ready_block(self):
        clock = Clock()
        # The Wi-Fi-served listener pid differs from the USB probe's ready block.
        dev = Device({1: [READY]}, serve_id={1: ('9999', ADDR)})
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertTrue(receipt['ssh_attempted'] and not receipt['boot_match'] and not receipt['ack_written'])
        self.assertEqual(dev.acks, [])
        # A different served address also fails the binding.
        dev = Device({1: [READY]}, serve_id={1: ('1234', '10.0.0.9')})
        receipt = MOD['run_cycle'](KEYS, BOOT, 1, 60, runner=dev.runner(), monotonic=clock.monotonic, sleep=clock.sleep)
        self.assertFalse(receipt['boot_match'] or receipt['ack_written'])

    def test_ack_argument_is_symlink_safe_and_noclobber(self):
        arg = MOD['ack_argument'](BOOT, 1)
        self.assertIn('[ ! -e', arg)
        self.assertIn('[ ! -L', arg)   # a dangling symlink must not redirect the write
        self.assertIn('set -C', arg)   # noclobber
        self.assertIn('|| exit 14', arg)  # a failed dmesg snapshot fails closed
        self.assertIn('host_ack boot=' + BOOT + ' cycle=1 ssh_exit=0', arg)

    def test_admissibility(self):
        usb = MOD['base_command'](KEYS)[1].split('@')[1]
        self.assertTrue(MOD['admissible'](ADDR, 'root@' + usb) and MOD['admissible']('10.0.0.5', 'root@' + usb))
        for bad in (usb, '127.0.0.1', '224.0.0.1', '0.0.0.0', '255.255.255.255', 'x'):
            self.assertFalse(MOD['admissible'](bad, 'root@' + usb))

    def test_main_refuses_without_keys_and_the_device_script_writes_the_ready_block(self):
        with tempfile.TemporaryDirectory() as directory:
            keys = pathlib.Path(directory) / 'keys'
            keys.mkdir()
            result = subprocess.run([str(HERE / 'laptop-wifi-ssh.py'), str(keys), BOOT, '--poll-seconds', '10'],
                                    capture_output=True, text=True, env=dict(os.environ), timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertIn('lacks admin or known_hosts', result.stderr)
            script = (HERE / 'join-twice.sh').read_text()
            self.assertIn('/tmp/mt6797-wifi-phase-b-1/c', script)
            self.assertIn('> "$cd/ready"', script, 'the device writes the per-cycle ready block the helper reads')
            self.assertIn('cycle=%s', script)


if __name__ == '__main__':
    unittest.main()
