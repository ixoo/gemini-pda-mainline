# SPDX-License-Identifier: MIT
"""Strict V4 deployment receipt with observed block identities."""
import re

GUARD_SHA256 = "0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf"

def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def receipt(raw, candidate):
    d={}
    for line in raw.splitlines():
        key,sep,value=line.partition('=')
        require(sep and key not in d,'receipt duplicate or malformed field')
        d[key]=value
    fixed={'experiment':'2026-09-04-mt6797-thermal-snapshot','target_logical_name':'boot2',
           'boot2_device_guard':'passed','boot2_device_guard_sha256':GUARD_SHA256,'fresh_predecessor_backup':'no','candidate_sha256':candidate,
           'readback_sha256':candidate,'temporary_readback_removed':'yes',
           'shutdown':'requested-after-evidence-flush','post_shutdown_reachability':'unreachable',
           'reboot':'no','next_action':'owner-physically-selects-boot2'}
    require(d.keys()==fixed.keys() | {'result','target','root','target_major_minor','root_major_minor','predecessor_sha256','boot_id','power','poweroff_ssh_rc'},'receipt inventory')
    require(all(d[k]==v for k,v in fixed.items()),'receipt invariant')
    require(d['result'] in ('write-synced-flushed-full-readback-verified','skipped-already-matching'),'receipt write result')
    require(re.fullmatch(r'/dev/mmcblk0p[0-9]+',d['target']) and d['target']!=d['root'],'receipt inactive target')
    require(re.fullmatch(r'/dev/[A-Za-z0-9][A-Za-z0-9_.-]*',d['root']), 'receipt canonical root')
    for key in ('root_major_minor', 'target_major_minor'):
        require(re.fullmatch(r'[1-9][0-9]{0,3}:(?:0|[1-9][0-9]{0,6})', d[key]), 'receipt device number')
        major, minor = map(int, d[key].split(':'))
        require(major <= 4095 and minor <= 1048575, 'receipt device range')
    require(d['root_major_minor'] != d['target_major_minor'], 'receipt mounted target')
    require(re.fullmatch(r'[0-9a-f]{64}',d['predecessor_sha256']),'receipt predecessor')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',d['boot_id']),'receipt boot')
    require(d['poweroff_ssh_rc'] in ('0','255'),'receipt shutdown status')
    power=d['power'].split('|')
    require(len(power)==4 and power[0]=='1' and power[2]=='Good' and power[1].isdigit() and power[3].isdigit(),'receipt power')
    capacity,external=int(power[1]),int(power[3])
    require(0<=capacity<=100 and (capacity>=80 or (capacity>=40 and external>=1)),'receipt stable power')
    if d['result']=='skipped-already-matching': require(d['predecessor_sha256']==candidate,'receipt skip identity')
    return d['boot_id']
