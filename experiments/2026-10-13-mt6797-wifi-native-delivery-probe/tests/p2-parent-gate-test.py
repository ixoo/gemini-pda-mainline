#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Additional P2 remote-owner gate cannot bypass inherited local custody."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='p2-owner-gate-') as d:
    root=Path(d).resolve();private=root/'private';runtime=root/'runtime';keys=root/'keys'
    (private/'artifacts/credentials').mkdir(parents=True);runtime.mkdir();keys.mkdir()
    script=root/'join.sh';script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX='+b'0'*64+
        b'\nTARGET_SSID_HEX=66697874757265\n'+(HERE/'join-ccmp-p2.sh').read_bytes());script.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private),GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(script),GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    binding=load('p2_owner_binding',HERE/'passive-host-ccmp-p2.py')
    host=load('p2_owner_generic_host',HERE/'passive-host-ccmp.py')
    host.PH.HELPER.join_and_record=lambda active:None
    binding.bind_ccmp_p2(host)
    helper=host.PH.HELPER
    assert (helper.poll,helper.join_timeout,helper.grace)==(710,770,5)
    receipt=helper.receipt_path;receipt.parent.mkdir(parents=True)
    helper.record.update(started=True,safe=True,group_quiescent=True)
    class Collector:
        def __init__(self):self.writes=[]
        def write_new(self,path,data):self.writes.append((path,data))
    for payload,allowed in [(None,False),({},False),({'p2_remote_stream_quiescence':{'quiesced':False}},False),
                            ({'p2_remote_stream_quiescence':{'quiesced':True}},True)]:
        if receipt.exists():receipt.unlink()
        if payload is not None:receipt.write_text(json.dumps(payload))
        collector=Collector()
        try:helper.join_and_record({'collector':collector})
        except RuntimeError as e:
            assert not allowed and 'refusing export, seal and recovery' in str(e)
        else:assert allowed
        assert len(collector.writes)==1
        assert collector.writes[0][0]==receipt.parent/'p2-remote-stream-quiescence.json'
    helper.record['safe']=False
    helper.join_and_record({'collector':Collector()})
    assert helper.record['safe'] is False  # old parent gate must still refuse
    assert host.NativeWifiHelper.join_and_record is host.PH.WifiHelper.join_and_record
print('P2 parent gate: missing/unknown remote work refuses seal/recovery; original local custody and bounds preserved PASS')
