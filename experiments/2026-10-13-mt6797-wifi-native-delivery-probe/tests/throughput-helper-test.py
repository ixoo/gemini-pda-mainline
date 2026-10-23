#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real local sockets, cancellation, CPU arithmetic and generated shell; no device."""
from pathlib import Path
import runpy
import resource
import socket
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
T=runpy.run_path(str(HERE.parent/'throughput-helper.py'))
R=runpy.run_path(str(HERE.parent/'throughput-run.py'))


class MeasurementTests(unittest.TestCase):
    def test_receive_counts_actual_known_bytes(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',False,duration=0.2,maximum=4096)
        with socket.create_connection(endpoint.socket.getsockname()) as peer:
            peer.sendall(bytes(4096));peer.shutdown(socket.SHUT_WR)
        endpoint.thread.join(1);endpoint.close()
        self.assertEqual(endpoint.result['bytes'],4096)
        self.assertEqual(endpoint.result['errors'],0)
        self.assertTrue(endpoint.result['owner_quiescent'])
        self.assertGreater(endpoint.result['Mbit_s'],0)

    def test_send_counts_actual_known_bytes(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',True,duration=0.2,maximum=4096)
        raw=b''
        with socket.create_connection(endpoint.socket.getsockname()) as peer:
            while data:=peer.recv(1024):raw+=data
        endpoint.thread.join(1);endpoint.close()
        self.assertEqual(raw,bytes(4096))
        self.assertEqual(endpoint.result['bytes'],4096)
        self.assertTrue(endpoint.result['known_size_complete'])

    def test_cancel_before_accept_is_quiescent(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',False,duration=0.2)
        endpoint.close()
        self.assertTrue(endpoint.result['owner_quiescent'])
        self.assertFalse(endpoint.result['completed'])

    def test_unknown_peer_refuses_without_another_accept(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'192.0.2.1',False,duration=0.2)
        with socket.create_connection(endpoint.socket.getsockname()):pass
        endpoint.thread.join(1);endpoint.close()
        self.assertEqual(endpoint.result['errors'],1)
        self.assertEqual(endpoint.result['bytes'],0)

    def test_cpu_delta_excludes_guest_double_count(self):
        raw=b'TP1_TX_CPU_BEFORE cpu 1000 0 200 8000 100 0 0 0 1000 0\r\nTP1_TX_CPU_AFTER cpu 1100 0 300 8800 120 0 0 0 1100 0\r\n'
        value=T['cpu_result'](raw,'TX')
        self.assertTrue(value['valid'])
        self.assertEqual(value['total_ticks'],1020)
        self.assertEqual(value['idle_ticks'],800)
        self.assertAlmostEqual(value['idle_percent'],100*800/1020)
        self.assertFalse(T['cpu_result'](b'', 'RX')['valid'])

    def test_generated_shell_and_finite_protocol(self):
        script=T['remote_script']('00000000-0000-4000-8000-000000000001','192.0.2.1')
        self.assertEqual(script.count('$BB timeout 1'),2)
        self.assertIn('bs=65536 count=16',script)
        self.assertEqual(T['validate_idle_safety'](script)['maximum_transfer_silence_seconds'],1)
        self.assertIn('5000000000',script)  # late-start refusal preserved
        self.assertEqual(script.count('TP1_%s_CPU_BEFORE'),1)
        self.assertNotIn('iperf',script)
        self.assertLess(len(script.encode())+1000,4096)
        subprocess.run(['/bin/sh','-n'],input=script.encode(),check=True)
        subprocess.run(['shellcheck','--shell=sh','-'],input=script.encode(),check=True)

    def test_silent_command_exceeding_idle_policy_is_refused(self):
        script=T['remote_script']('00000000-0000-4000-8000-000000000001','192.0.2.1')
        with self.assertRaises(ValueError):
            T['validate_idle_safety'](script.replace('$BB timeout 1','$BB timeout 31'))
        with self.assertRaises(ValueError):
            T['validate_idle_safety'](script.replace('TP2_PROGRESS','QUIET'))

    def test_five_chunks_use_separate_connections(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',False,duration=0.2,maximum=4096,chunks=5)
        address=endpoint.socket.getsockname()
        for _ in range(5):
            with socket.create_connection(address) as peer:
                peer.sendall(bytes(4096));peer.shutdown(socket.SHUT_WR)
        endpoint.thread.join(1);endpoint.close()
        self.assertEqual(endpoint.result['bytes'],5*4096)
        self.assertEqual(len(endpoint.result['chunks']),5)
        self.assertTrue(endpoint.result['completed'])

    def test_empty_chunk_stops_before_another_accept(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',False,duration=0.2,maximum=4096,chunks=5)
        with socket.create_connection(endpoint.socket.getsockname()) as peer:
            peer.shutdown(socket.SHUT_WR)
        endpoint.thread.join(1);endpoint.close()
        self.assertEqual(endpoint.result['errors'],1)
        self.assertEqual(len(endpoint.result['chunks']),1)
        self.assertFalse(endpoint.result['completed'])

    def test_rx_counter_streams_above_inherited_file_limit(self):
        script=T['remote_script']('00000000-0000-4000-8000-000000000001','192.0.2.1')
        counter=next(line.strip() for line in script.splitlines() if 'n=$(set -o pipefail;' in line)
        # Exercise the actual generated counter; substitute only the network
        # producer with a known 1 MiB zero stream. Keep the inherited 128 KiB
        # regular-file limit. No device, limit extension or payload file.
        producer='$BB timeout 1 $BB nc 192.0.2.1 48002'
        self.assertEqual(counter.count(producer),1)
        counter=counter.replace(producer,'$BB dd if=/dev/zero bs=65536 count=16 2>/dev/null')
        def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(131072,131072))
        result=subprocess.run(['/bin/bash','-c','BB=command; rc=0; '+counter+'; printf "%s %s\\n" "$n" "$rc"'],capture_output=True,check=True,preexec_fn=limit)
        self.assertEqual(result.stdout.strip(),b'1048576 0')
        self.assertNotIn('/tmp/tp2-rx',script)
        self.assertFalse(T['validate_receive_safety'](script)['regular_payload_file'])
        with self.assertRaises(ValueError):
            T['validate_receive_safety'](script.replace('| $BB wc -c','> /tmp/oversize-rx'),regular_file_limit=T['MAX_BYTES']-1)

    def test_duration_ends_before_a_large_byte_cap(self):
        endpoint=T['Endpoint']('127.0.0.1',0,'127.0.0.1',True,duration=0.03,maximum=1<<40)
        count=0
        with socket.create_connection(endpoint.socket.getsockname()) as peer:
            while data:=peer.recv(65536):count+=len(data)
        endpoint.thread.join(1);endpoint.close()
        self.assertGreater(count,0)
        self.assertEqual(endpoint.result['chunks'][0]['ended_by'],'duration')
        self.assertGreaterEqual(endpoint.result['chunks'][0]['elapsed_ns'],30_000_000)
        self.assertLess(endpoint.result['chunks'][0]['elapsed_ns'],500_000_000)

    def test_device_chunk_counts_and_duplicate_refusal(self):
        raw=(b'TP2_PROGRESS direction=RX chunk=1 phase=start ns=1000000000\r\n'
             b'TP2_PROGRESS direction=RX chunk=1 phase=end rc=143 bytes=65536 ns=2000000000\r\n')
        row=T['device_chunks'](raw,'RX')[1]
        self.assertEqual(row['device_received_bytes'],65536)
        self.assertEqual(row['device_elapsed_ns'],1_000_000_000)
        self.assertAlmostEqual(row['device_Mbit_s'],0.524288)
        self.assertEqual(T['device_chunks'](raw+raw,'RX'),{})

    def test_controller_claim_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'claim.json'
            R['write_new'](path,{'one_attempt':True})
            with self.assertRaises(FileExistsError):R['write_new'](path,{})
            self.assertEqual(path.stat().st_mode&0o777,0o600)


if __name__=='__main__':unittest.main()
