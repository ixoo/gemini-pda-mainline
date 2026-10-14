#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual7.1.3 cipher predicate plus actual parent/fixed registration blocks."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

parent, child, upstream = (Path(p) for p in sys.argv[1:4])
rel = 'drivers/net/wireless/mediatek/mt6797/mac.c'
old, new = (parent / rel).read_text(), (child / rel).read_text()
expected = old.replace('static bool ccmp_stable_epoch;\n',
    'static bool ccmp_stable_epoch;\nstatic const u32 mt6797_ccmp_ciphers[] = { WLAN_CIPHER_SUITE_CCMP };\n')
expected = expected.replace('\t\tieee80211_hw_set(hw, SUPPORTS_RX_DECAP_OFFLOAD);',
    '\t\thw->wiphy->cipher_suites = mt6797_ccmp_ciphers;\n'
    '\t\thw->wiphy->n_cipher_suites = ARRAY_SIZE(mt6797_ccmp_ciphers);\n'
    '\t\tieee80211_hw_set(hw, SUPPORTS_RX_DECAP_OFFLOAD);')
assert new == expected, 'only the cipher admission fix is permitted'
core = (upstream / 'net/mac80211/main.c').read_text()
start = core.index('static int ieee80211_init_cipher_suites(')
end = core.index('\n}\n', start) + 3
predicate = core[start:end]
assert 'SW_CRYPTO_CONTROL) &&\n\t\t    !local->hw.wiphy->cipher_suites' in predicate
array = re.search(r'static const u32 mt6797_ccmp_ciphers\[\] = .*?;', new)[0]
def block(text):
    start = text.index('\tif (ccmp_stable_epoch) {', text.index('int mt6797_mac_register('))
    return text[start:text.index('\n\t}', start) + 3]
code = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
typedef uint32_t u32;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
enum { SW_CRYPTO_CONTROL=1, MFP_CAPABLE=2, SUPPORTS_RX_DECAP_OFFLOAD=4 };
enum { WLAN_CIPHER_SUITE_WEP40=0x000fac01, WLAN_CIPHER_SUITE_TKIP=0x000fac02,
 WLAN_CIPHER_SUITE_CCMP=0x000fac04, WLAN_CIPHER_SUITE_WEP104=0x000fac05,
 WLAN_CIPHER_SUITE_AES_CMAC=0x000fac06, WLAN_CIPHER_SUITE_GCMP=0x000fac08,
 WLAN_CIPHER_SUITE_GCMP_256=0x000fac09, WLAN_CIPHER_SUITE_CCMP_256=0x000fac0a,
 WLAN_CIPHER_SUITE_BIP_GMAC_128=0x000fac0b, WLAN_CIPHER_SUITE_BIP_GMAC_256=0x000fac0c,
 WLAN_CIPHER_SUITE_BIP_CMAC_256=0x000fac0d };
struct wiphy { const u32 *cipher_suites; unsigned int n_cipher_suites; struct {void *parent;} dev; };
struct ieee80211_hw { unsigned int flags; struct wiphy *wiphy; };
struct ieee80211_local { struct ieee80211_hw hw; };
static bool fips_enabled, ccmp_stable_epoch;
static unsigned int warnings;
#define ieee80211_hw_check(hw, flag) ((hw)->flags & (flag))
#define ieee80211_hw_set(hw, flag) ((hw)->flags |= (flag))
#define WARN_ON(test) ((test) ? (++warnings, 1) : 0)
#define dev_err(dev, ...) ((void)(dev))
'''
code += array + '\n' + predicate + '\n'
code += 'static void parent_register(struct ieee80211_hw *hw) {\n' + block(old) + '\n}\n'
code += 'static void fixed_register(struct ieee80211_hw *hw) {\n' + block(new) + '\n}\n'
code += r'''
int main(void) {
 struct wiphy old={0}, fixed={0}, native={0};
 struct ieee80211_local a={.hw={.wiphy=&old}}, b={.hw={.wiphy=&fixed}}, c={.hw={.wiphy=&native}};
 ccmp_stable_epoch=true; parent_register(&a.hw);
 assert(ieee80211_init_cipher_suites(&a)==-EINVAL && warnings==1 && !old.cipher_suites);
 fixed_register(&b.hw);
 assert(b.hw.flags==a.hw.flags && fixed.n_cipher_suites==1 && fixed.cipher_suites[0]==WLAN_CIPHER_SUITE_CCMP);
 assert(!ieee80211_init_cipher_suites(&b) && warnings==1 && fixed.n_cipher_suites==1);
 ccmp_stable_epoch=false; fixed_register(&c.hw);
 assert(!c.hw.flags && !native.cipher_suites);
 assert(!ieee80211_init_cipher_suites(&c) && native.n_cipher_suites>1);
 fips_enabled=true;
 assert(ieee80211_init_cipher_suites(&b)==-EINVAL && warnings==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='ccmp-cipher-admission-', dir='/tmp/opencode') as tmp:
    p = Path(tmp); (p / 'test.c').write_text(code)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-fno-pie', '-no-pie', str(p / 'test.c'), '-o', str(p / 'test')], check=True, timeout=30)
    subprocess.run([str(p / 'test')], check=True, timeout=10)
print('cipher admission: PASS actual upstream predicate reproduces -EINVAL; fixed CCMP-only list, unchanged flags/native and FIPS refusal (host-only)')
