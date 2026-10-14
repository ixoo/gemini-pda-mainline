#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile actual pinned dispatch/prepare fragments, synthetic RX only; no device."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent', type=Path)
parser.add_argument('child', type=Path)
args = parser.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = args.parent / rel, args.child / rel
old, new = (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()
assert hashlib.sha256((parent / 'mac.c').read_bytes()).hexdigest() == \
    'a140b36a170a8608f48ca1dbb014b98181e337a2df58c768c37239b5f3ada746'
begin = old.index('\t\t\tif (ccmp_stable_epoch)\n\t\t\t\tcontinue;')
end = old.index('\n#endif', begin)
replacement_begin = new.index('\t\t\tif (ccmp_stable_epoch) {', new.index('translated/plain withheld'))
replacement_end = new.index('\n#endif', replacement_begin)
label = '#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH\nmanagement_frame:\n#endif\n'
assert new.replace(new[replacement_begin:replacement_end], old[begin:end]).replace(label, '') == old
for path in parent.iterdir():
    if path.is_file() and path.name != 'mac.c':
        assert (child / path.name).read_bytes() == path.read_bytes(), path.name
assert {p.name for p in parent.iterdir() if p.is_file()} == \
    {p.name for p in child.iterdir() if p.is_file()}


def function(text, name):
    start = text.index('static void ' + name + '(')
    pos = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[pos] == '{') - (text[pos] == '}')
        pos += 1
    return text[start:pos]


def dispatch(text, gate_start):
    gate_end = text.index('\n#endif', gate_start)
    decode = text.index('\t\t\tif (!mt6797_join_rx_frame(')
    delivery_end = text.index('\n\t\t}\n', decode)
    return '''static int dispatch(struct mt6797_mac *mac, size_t bytes) {
        struct { size_t logical_bytes; } rx = { bytes };
        struct mt6797_join_rx_frame frame;
        const unsigned char *body;
        struct sk_buff *skb;
        struct sk_buff_head received = {0};
        int ret = 0;
        for (int tick = 0; tick < 1; tick++) {
    ''' + text[gate_start:gate_end] + '\n' + text[decode:delivery_end] + '''
        }
    failed: free(received.skb); return ret;
    }
    '''


fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include "join-rx.h"
#define CONFIG_MT6797_CCMP_STABLE_EPOCH 1
#define CONFIG_MT6797_STATION_JOIN 1
#define IS_ENABLED(x) (x)
#define BIT(x) (1U << (x))
#define NSEC_PER_MSEC 1000000ULL
#define IEEE80211_STYPE_AUTH 0xb0
#define IEEE80211_STYPE_ASSOC_REQ 0
#define IEEE80211_STYPE_DEAUTH 0xc0
#define IEEE80211_STYPE_DISASSOC 0xa0
#define NL80211_BAND_5GHZ 1
#define min(a,b) ((a)<(b)?(a):(b))
#define mutex_lock(p) ((void)(p))
#define mutex_unlock(p) ((void)(p))
#define spin_lock_irqsave(p,f) ((void)(p), (f)=0)
#define spin_unlock_irqrestore(p,f) ((void)(p), (void)(f))
#define wiphy_dev(p) (p)
#define dev_info(...) ((void)0)
struct ieee80211_rx_status { int band, freq, signal; };
struct sk_buff { unsigned char data[2304]; struct ieee80211_rx_status status; };
struct sk_buff_head { int lock; struct sk_buff *skb; };
struct ieee80211_vif { int valid_links; };
struct ieee80211_prep_tx_info { unsigned int subtype; int link_id; };
struct wiphy { unsigned char perm_addr[6]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct mt6797_mac {
    struct ieee80211_hw *hw; struct ieee80211_vif *vif;
    struct sk_buff_head join_queue;
    int mutex, first_error;
    bool join_cleanup_requested, join_cleanup_done, join_data_phase, join_data_ended;
    bool join_peer_ready, join_running, join_retired, closing;
    bool join_channel_valid, join_bss_valid, join_channel_granted;
    bool join_authenticated, join_auth_received, join_assoc_received, join_auth_ok;
    bool join_open, join_short_preamble;
    uint64_t join_deadline, join_grant_deadline;
    unsigned int join_seen, join_tx_allowed, join_rx_allowed, join_submitted;
    unsigned int join_assoc_status, join_aid;
    unsigned char join_ap[6], join_packet[128];
};
static bool ccmp_stable_epoch;
static int delivered;
static uint64_t ktime_get_ns(void) { return 1000000000ULL; }
static void mt6797_mac_join_end_data(struct mt6797_mac *m, const char *s) { (void)m; (void)s; }
static void mt6797_mac_join_refused_frame(struct mt6797_mac *m, size_t n) { (void)m; (void)n; }
static unsigned int get_unaligned_le16(const unsigned char *p) { return mt6797_join_le16(p); }
static struct sk_buff *dev_alloc_skb(size_t n) { assert(n <= 2304); return calloc(1, sizeof(struct sk_buff)); }
static void skb_put_data(struct sk_buff *s, const void *p, size_t n) { memcpy(s->data, p, n); }
#define IEEE80211_SKB_RXCB(s) (&(s)->status)
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *s) { assert(!q->skb); q->skb=s; delivered++; }
'''
checks = r'''
static void packet(struct mt6797_mac *m, int subtype) {
    unsigned char *p = m->join_packet, *f = p+40;
    memset(p, 0, 128);
    p[0] = subtype == 10 || subtype == 12 ? 66 : 70;
    p[2]=1; p[3]=0xe8; p[5]=40; p[6]=24; p[25]=100;
    f[0]=subtype<<4;
    memcpy(f+4, m->hw->wiphy->perm_addr, 6);
    memcpy(f+10, m->join_ap, 6); memcpy(f+16, m->join_ap, 6);
    if (subtype==11) f[26]=2;
    if (subtype==1) { f[28]=1; f[29]=0xc0; }
}
int main(void) {
    struct wiphy w = { .perm_addr={2,1,2,3,4,5} };
    struct ieee80211_vif v = {0};
    struct ieee80211_hw h = { .wiphy=&w };
    struct mt6797_mac m = { .hw=&h, .vif=&v, .join_peer_ready=true,
        .join_running=true, .join_channel_valid=true, .join_bss_valid=true,
        .join_channel_granted=true, .join_deadline=10000000000ULL,
        .join_grant_deadline=10000000000ULL, .join_ap={2,6,7,8,9,10} };
    struct ieee80211_prep_tx_info info = { .subtype=IEEE80211_STYPE_AUTH };
    h.priv=&m;
    mt6797_mac_mgd_prepare_tx(&h, &v, &info);
    assert(m.join_open && !m.first_error && (m.join_rx_allowed & BIT(11)));
    m.join_seen=BIT(11); m.join_submitted=BIT(11);
    ccmp_stable_epoch=true; packet(&m,11);
    assert(dispatch(&m,70)==0);
    assert(m.join_auth_received==FIXED && delivered==FIXED);
    /* No retry/gate relaxation: even child refuses a repeated AUTH. */
    mt6797_mac_mgd_prepare_tx(&h, &v, &info);
    assert(m.first_error==-EOPNOTSUPP && m.closing && !m.join_open);
    m.first_error=0; m.closing=false;
    if (FIXED) {
        assert(m.join_auth_ok);
        m.join_authenticated=true; /* successful sta_state transition premise */
        info.subtype=IEEE80211_STYPE_ASSOC_REQ;
        mt6797_mac_mgd_prepare_tx(&h,&v,&info);
        assert(m.join_open && !m.first_error && (m.join_rx_allowed & BIT(1)));
        m.join_submitted |= BIT(0); packet(&m,1);
        assert(dispatch(&m,70)==0 && m.join_assoc_received && delivered==2);
    }
    /* Old mode still takes its original strict management path. */
    ccmp_stable_epoch=false; m.join_auth_received=false;
    m.join_rx_allowed=BIT(11); packet(&m,11); delivered=0;
    assert(dispatch(&m,70)==0 && m.join_auth_received && delivered==1);
    /* CCMP mode still drops all non-management/invalid shapes, no legacy RX. */
    ccmp_stable_epoch=true; m.join_auth_received=false; delivered=0;
    for (int mutation=0; mutation<10; mutation++) {
        packet(&m,11);
        switch(mutation) {
        case 0: m.join_packet[44]^=1; break; /* RA */
        case 1: m.join_packet[50]^=1; break; /* TA */
        case 2: m.join_packet[56]^=1; break; /* BSSID */
        case 3: m.join_packet[41]|=0x40; break; /* protected */
        case 4: m.join_packet[40]=0x08; break; /* ordinary data */
        case 5: m.join_packet[66]=1; break; /* auth transaction */
        case 6: m.join_packet[5]=36; break; /* channel */
        case 7: m.join_packet[10]=2; break; /* status */
        case 8: m.join_packet[0]=69; break; /* length */
        case 9: m.join_packet[62]=1; break; /* fragment */
        }
        assert(dispatch(&m,70)==0 && !m.join_auth_received && !delivered);
    }
    if (FIXED) {
        m.join_auth_received=false; m.join_rx_allowed=BIT(11);
        packet(&m,11); m.join_packet[68]=1;
        assert(dispatch(&m,70)==0 && m.join_auth_received && !m.join_auth_ok);
        assert(dispatch(&m,70)==-EPROTO); /* duplicate response still refuses */
        packet(&m,1); m.join_packet[0]=71;
        m.join_rx_allowed=BIT(1); delivered=0;
        assert(dispatch(&m,71)==0 && !delivered); /* truncated IE */
        m.join_rx_allowed=BIT(10)|BIT(12);
        for(int subtype=10; subtype<=12; subtype+=2) {
            packet(&m,subtype);
            delivered=0;
            assert(dispatch(&m,66)==0 && delivered==1);
        }
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='ccmp-management-', dir='/tmp/opencode') as directory:
    temporary = Path(directory)
    for name, text, start, fixed in (('parent', old, begin, 0),
                                    ('child', new, replacement_begin, 1)):
        source = temporary / (name + '.c')
        source.write_text(fixture + function(text, 'mt6797_mac_mgd_prepare_tx') +
                          '\n' + dispatch(text, start) + checks)
        binary = temporary / name
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-fno-pie', '-no-pie', '-DFIXED=' + str(fixed),
                        '-I', str(child), str(source), '-o', str(binary)],
                       check=True, timeout=30)
        subprocess.run([str(binary)], check=True, timeout=30)
        print(name + ': actual dispatch/prepare PASS (synthetic, ASan/UBSan)')
print('Exact MAC-only reversal PASS; parser, callbacks, radio/crypto/budgets unchanged')
