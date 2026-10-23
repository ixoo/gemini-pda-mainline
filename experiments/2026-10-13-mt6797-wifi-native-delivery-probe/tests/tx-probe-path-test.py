#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""One-pass actual-source probe-path feasibility test; fake host I/O only."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('mac_tree', type=Path)
p.add_argument('header_tree', type=Path)
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
s = (a.mac_tree / rel / 'mac.c').read_text()
headers = (a.header_tree / rel).resolve()

def function(name):
    start = s.index(name)
    brace = s.index('\n{', start) + 1
    depth = 0
    for i in range(brace, len(s)):
        depth += (s[i] == '{') - (s[i] == '}')
        if not depth:
            return s[start:i+1]
    raise AssertionError('source function incomplete')

pid_start = s.index('struct mt6797_join_pid_pool {')
pid_struct = s[pid_start:s.index('\n};', pid_start)+3]
assign = function('static int mt6797_ccmp_assign_pid(')
take = function('static inline unsigned char mt6797_join_pid_take(')
# The existing native submission/completion path has one internal owner,
# reserved for deauthentication. Do not rename these predicates in a fixture.
assert 'mt6797_ccmp_assign_pid(mac, skb == mac->join_internal)' in s
assert 'mt6797_hif_send_management(mac->hif, skb->data, skb->len,' in s
assert 'if (completed_internal) {\n\t\t\t\t\tmac->join_deauth_done = ack;' in s
assert 'mt6797_mac_deauth_delivery(mac, "completion", true,' in s
code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "join-tx.h"
#define MT6797_JOIN_PID_LAST 126U
#define MT6797_JOIN_PID_RESERVED 127U
#define dev_info(device, ...) ((void)printf(__VA_ARGS__))
static bool ccmp_stable_epoch = true;
'''+pid_struct+take+r'''
struct mt6797_mac {
 int first_error;
 bool closing, join_retired, join_credit_pending, ccmp_reserved_pid_used;
 bool join_data_ended;
 unsigned int join_page_debt, join_data_page_debt, join_next_pid, join_pid;
 struct mt6797_join_pid_pool ccmp_pid_pool;
};
'''+assign+r'''
int main(void) {
 unsigned char frame[26]={0}, output[MT6797_JOIN_TX_DESC_BYTES], saved[sizeof(output)];
 unsigned int pages=0;
 struct mt6797_mac m={0};
 /* Existing unprotected native deauthentication shape is supported. */
 frame[0]=0xc0;
 assert(mt6797_join_tx_descriptor(frame,26,1,127,500,3,output,&pages));
 /* Payload-free protected ToDS QoS-null: 24-byte MAC + 2-byte QoS header.
  * The actual management encoder refuses it without touching output. */
 frame[0]=0xc8;frame[1]=0x41;
 memset(output,0xa5,sizeof(output));memcpy(saved,output,sizeof(saved));
 assert(!mt6797_join_tx_descriptor(frame,26,1,127,500,3,output,&pages));
 assert(!memcmp(output,saved,sizeof(saved)));
 /* Simply marking the probe internal consumes the only reserved owner.
  * Data and a subsequent internal deauthentication are then both refused. */
 assert(mt6797_ccmp_assign_pid(&m,true)==0 && m.join_pid==127);
 assert(mt6797_ccmp_assign_pid(&m,false)==-EOWNERDEAD);
 assert(mt6797_ccmp_assign_pid(&m,true)==-EOWNERDEAD);
 puts("actual probe path: protected native QoS-null encoder REFUSED; internal probe exhausts reserved owner and blocks data/deauth");
 puts("pass_timebox=STOP; required new native protected TX shape and distinct internal ownership exceed existing-path scope");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='tx-probe-path-') as d:
    source, binary = Path(d)/'test.c', Path(d)/'test'
    source.write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-I',str(headers),str(source),'-o',str(binary)],
                   check=True,timeout=30)
    subprocess.run([str(binary)],check=True,timeout=30)
print('completion wiring: all existing internal completions remain deauthentication evidence; no probe owner exists')
