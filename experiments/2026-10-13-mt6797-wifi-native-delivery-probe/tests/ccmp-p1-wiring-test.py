#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL P1 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-p1').replace('CCMP2', 'P1').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-p1').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-p1h').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '71c581f0e4478e71009f2ff3d09b78be6951124a6d6c8ca09bd92cd2e78262ba').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    '7bc347261ba8246dd1a4a53fa0270ab4705e91f73f9bdb850fdc06f29937fa2f')
fixture = fixture.replace('laptop-wifi-ssh-ccmp.py', 'laptop-wifi-ssh-connected.py')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
fixture = fixture.replace(
    "    assert standalone.ROOT == runtime",
    "    assert standalone.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-connected.py'\n    assert standalone.ROOT == runtime").replace(
    "    ph = host.PH",
    "    assert host.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-connected.py'\n    ph = host.PH")
fixture = fixture.replace('join-ccmp.sh', 'join-ccmp-p1.sh')

# Exercise the actual bound helper instance and then its real child CLI; this
# closes the parent-only coverage gap that burned I50's SSH observation.
fixture = fixture.replace('import tempfile', 'import tempfile\nfrom unittest.mock import patch\nimport contextlib, io')
start = "    session = load('laptop-session-ccmp-p1.py')"
replacement = """    calls = []
    def fake_spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return __import__('types').SimpleNamespace(pid=34567)
    with patch('subprocess.Popen',fake_spawn):
        session = load('laptop-session-ccmp-p1.py')"""
assert fixture.count(start)==1
fixture = fixture.replace(start,replacement)
start = """    calls = []
    def fake_spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return __import__('types').SimpleNamespace(pid=34567)
    helper = host.NativeWifiHelper(keys, os.environ['GEMINI_WIFI_SSH_BOOT'],
                                   ph.WIFI_SSH_RECEIPT, cycles=1, spawn=fake_spawn)"""
replacement = """    helper = ph.HELPER
    captured=dict(zip(helper.spawn.__code__.co_freevars,[c.cell_contents for c in helper.spawn.__closure__]))
    assert captured['original_spawn'] is fake_spawn
    assert helper.poll==210 and helper.join_timeout==270 and helper.grace==5"""
assert fixture.count(start)==1
fixture = fixture.replace(start,replacement)
anchor = "    assert kwargs['start_new_session'] is True and helper.pgid == 12345"
# This inherited fixture uses calls[0], not the standalone S1 spelling.
anchor = "    assert calls[0][1]['start_new_session'] and helper.pgid == 34567"
extra = """
    argv=calls[0][0]
    assert argv[argv.index('--poll-seconds')+1]=='210'
    (keys/'admin').write_text('fixture');(keys/'known_hosts').write_text('fixture')
    child=load('laptop-wifi-ssh-connected.py')
    received=[]
    def no_transport(*args):
        received.append(args)
        return {'boot_id':os.environ['GEMINI_WIFI_SSH_BOOT'],'cycles_expected':1,'cycles':[],'all_pass':False}
    with patch.object(child,'run',no_transport),patch.object(sys,'argv',argv[1:]), \\
         patch.object(sys,'platform','darwin'),contextlib.redirect_stdout(io.StringIO()):
        assert child.main()==1
    assert received[0][0]==expected_root/'ssh-client-observation'
    assert received[0][-2:]==(1,210)
    assert json.loads(ph.WIFI_SSH_RECEIPT.read_text())['all_pass'] is False
"""
assert fixture.count(anchor)==1
fixture=fixture.replace(anchor,anchor+extra)
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
