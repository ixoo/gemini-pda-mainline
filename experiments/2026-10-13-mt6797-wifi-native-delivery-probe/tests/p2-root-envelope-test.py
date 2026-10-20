#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the composed image's actual two-member delta and exact logger package."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

REPO=Path(__file__).resolve().parents[3]
old,new,logger=[Path(v).resolve(strict=True) for v in sys.argv[1:]]
sha=lambda data:hashlib.sha256(data).hexdigest()
for root in [old,new]:
    receipt=json.loads((root/'candidate.json').read_text())
    assert {p.name for p in root.iterdir()}==set(receipt['files'])|{'candidate.json'}
    for name,identity in receipt['files'].items():
        assert (root/name).is_file() and not (root/name).is_symlink()
        assert len((root/name).read_bytes())==identity['bytes']
        assert sha((root/name).read_bytes())==identity['sha256']
for name in ['Image.gz','kernel.config','board.dtb']:
    assert (old/name).read_bytes()==(new/name).read_bytes()
parse=runpy.run_path(str(REPO/'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
a,b=[parse((root/'initramfs.img').read_bytes()) for root in [old,new]]
assert len(a)==len(b)==64 and a.keys()==b.keys()
assert {name for name in a if a[name]!=b[name]}=={'bin/usb-auth','bin/kmsg-capture'}
assert a['bin/usb-auth'].data.count(b'-M 360')==1
assert b['bin/usb-auth'].data==a['bin/usb-auth'].data.replace(b'-M 360',b'-M 900')
assert b['bin/usb-auth'].data.count(b'-I 60')==1
assert b['bin/kmsg-capture'].data==(logger/'kmsg-capture').read_bytes()
for name in ['bin/usb-auth','bin/kmsg-capture']:
    assert a[name].mode==b[name].mode and a[name].uid==b[name].uid and a[name].gid==b[name].gid
receipt=json.loads((new/'candidate.json').read_text())
assert receipt['logger_deadline_ms']==900000 and receipt['logger_byte_limit']==2097152
assert receipt['host_control_pm_window_ms']==[604000,608000]
assert receipt['host_stream_tick_count']==602 and receipt['host_stream_tick_interval_ns']==1000000000
assert receipt['host_stream_required_ms']==600000 and receipt['host_stream_scheduled_ms']==601000
assert receipt['periodic_ping_offsets_s']==list(range(10,591,10))
assert all(sha(b[name].data)==digest for name,digest in receipt['live_root_sha256'].items())
assert sha((logger/'SHA256SUMS').read_bytes())==receipt['logger_package_manifest_sha256']
print('Actual P2 container: unchanged kernel/config/DT, exact two-member RAM delta and bounded host/logger contract PASS')
