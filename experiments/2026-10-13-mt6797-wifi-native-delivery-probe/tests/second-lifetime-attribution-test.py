#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline counterexamples against actual source; never enables protected reuse.

A passing diagnostic reproduces the missing attribution contract. It is NOT a
passing second-lifetime admission test or proof that stale firmware traffic
actually survives teardown. Inputs are a reviewed MAC tree and unchanged RX
headers; no kernel build, firmware command or device access occurs.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('mac_tree', type=Path)
p.add_argument('header_tree', type=Path)
a = p.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
mac = (a.mac_tree / rel / 'mac.c').read_text()
headers = (a.header_tree / rel).resolve()
fixtures = Path(__file__).resolve().parent
# Extract the complete production key-event branch, including its real decoder,
# state changes and completion publication. Only kernel environment is stubbed.
start = mac.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x24, 8)) {')
end = mac.index('\n#endif\n\tif (mt6797_join_event(mac->join_packet, bytes, 0x11, 4))', start)
branch = mac[start:end]
assert branch.count('complete_all(&mac->ccmp_key_done);') == 1
assert 'mac->join_key_done = true;' in branch
assert 'mac->join_key_done_second = true;' in branch
for gate in ('mac->join_key_group_submitted', 'mac->join_key_pairwise_submitted',
             'mac->join_cleanup_stage', 'mac->join_cleanup_done'):
    assert gate in branch
prefix = r'''
#include <errno.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "join-events.h"
typedef unsigned char u8;
#define CONFIG_MT6797_CCMP_STABLE_EPOCH 1
#define dev_info(device, ...) ((void)printf(__VA_ARGS__))
static bool ccmp_stable_epoch = true;
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a,b,6); }
static bool is_broadcast_ether_addr(const u8 *a) {
 static const u8 b[6] = {255,255,255,255,255,255}; return !memcmp(a,b,6);
}
static void complete_all(unsigned int *done) { ++*done; }
struct mt6797_mac {
 u8 join_packet[16], join_ap[6];
 bool join_sta_active, join_bss_configured, join_deauth_done;
 bool join_cleanup_done, join_key_pairwise_submitted, join_key_group_submitted;
 bool join_key_done, join_key_done_second;
 unsigned int join_cleanup_stage, join_key_pairwise, ccmp_key_done;
 void *join_internal, *join_inflight;
};
static int key_event(struct mt6797_mac *mac, size_t bytes) {
'''
key_test = prefix + branch + r'''
 return -ENOENT;
}
int main(void) {
 struct mt6797_mac m = { .join_sta_active=true, .join_bss_configured=true };
 const u8 peer[6] = {2,0,0,0,0,2};
 u8 saved[16];
 m.join_packet[0]=16; m.join_packet[3]=0xe0; m.join_packet[4]=0x24;
 memcpy(m.join_ap,peer,6); memcpy(m.join_packet+10,peer,6);
 memcpy(saved,m.join_packet,sizeof(saved));
 /* Before new install: old event is refused, no completion publication. */
 assert(key_event(&m,16)==-EPROTO && m.ccmp_key_done==0);
 /* Counterfactual re-arm only: exactly the same old bytes during new install
  * satisfy the production predicate and publish the pairwise completion. */
 m.join_key_pairwise_submitted=true;
 assert(key_event(&m,16)==0 && m.join_key_done && m.ccmp_key_done==1);
 /* After that install, during group install: same old bytes count again. */
 m.join_key_group_submitted=true;
 assert(key_event(&m,16)==0 && m.join_key_done_second && m.ccmp_key_done==1);
 assert(!memcmp(saved,m.join_packet,sizeof(saved)));
 assert(key_event(&m,16)==-EPROTO && m.ccmp_key_done==1);
 puts("COUNTEREXAMPLE: byte-identical old key event publishes new-install completion if reuse is enabled without an attributable barrier");
 /* Actual TX decoder can reject a fresh distinct PID; reusing a wire PID
  * cannot be repaired by a host-only generation absent from the packet. */
 {
  u8 tx[24]={24,0,0,0xe0,0x0f}; struct mt6797_join_tx_result out;
  tx[8]=127; tx[12]=1;
  assert(mt6797_join_tx_done(tx,24,127,1,&out));
  assert(!mt6797_join_tx_done(tx,24,126,1,&out));
  assert(mt6797_join_tx_done(tx,24,127,1,&out));
 }
 puts("TX attribution: distinct wire PID rejects old completion; same PID is indistinguishable");
 return 0;
}
'''
# Reuse the maintained real PTK/GTK frame builders and boundary tests.
baseline = (fixtures / 'ccmp-rx-test.c').read_text().replace(
    '"../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"',
    '"' + str(fixtures.parents[1] / '2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c') + '"')
gtk = (fixtures / 'ccmp-gtk-rx-test.c').read_text().replace('int main(void)', 'int gtk_baseline_tests(void)')
rx_test = gtk + r'''
int main(void) {
 unsigned char old[256]; struct mt6797_ccmp_rx out;
 struct mt6797_ccmp_rx_context first=context(), next=context();
 size_t n=frame(old,9,false,100);
 assert(ptk_baseline_tests()==0);
 assert(gtk_baseline_tests()==0);
 assert(mt6797_ccmp_rx_check(old,n,&first,&out));
 /* Resetting only a host context makes the same old descriptor admissible. */
 assert(mt6797_ccmp_rx_check(old,n,&next,&out));
 assert(!mt6797_ccmp_rx_check(old,n,&next,&out));
 n=frame(old,9,false,99);
 assert(!mt6797_ccmp_rx_check(old,n,&next,&out));
 /* Carrying the old floor also fails: new-key PN 1 is refused. */
 n=frame(old,9,false,1);
 assert(!mt6797_ccmp_rx_check(old,n,&first,&out));
 for (unsigned int key=0; key<4; key++) {
  first=group_context(key); next=group_context(key);
  n=group_frame(old,9,false,100,key,true);
  assert(mt6797_ccmp_gtk_rx_check(old,n,&first,&out));
  assert(mt6797_ccmp_gtk_rx_check(old,n,&next,&out));
  assert(!mt6797_ccmp_gtk_rx_check(old,n,&next,&out));
  next=group_context((key+1)%4);
  assert(!mt6797_ccmp_gtk_rx_check(old,n,&next,&out));
 }
 puts("COUNTEREXAMPLE: fresh PTK/GTK host floor accepts old descriptor without a producer-retirement boundary; equal/lower PN and mixed key index still refused");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='second-lifetime-attribution-') as d:
    tmp = Path(d)
    (tmp / 'ptk-baseline.inc').write_text(baseline.replace('int main(void)', 'int ptk_baseline_tests(void)'))
    for name, code in (('key', key_test), ('rx', rx_test)):
        source, binary = tmp / (name+'.c'), tmp / name
        source.write_text(code)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(tmp), '-I', str(headers), str(source), '-o', str(binary)],
                       check=True, timeout=30)
        subprocess.run([str(binary)], check=True, timeout=30)
print('mac_sha256='+hashlib.sha256(mac.encode()).hexdigest())
for name in ('join-events.h', 'ccmp-rx.h', 'ccmp-gtk-rx.h'):
    print(name+'_sha256='+hashlib.sha256((headers/name).read_bytes()).hexdigest())
print('offline_admission=REFUSED; no protected reuse, kernel build or device test admitted')
