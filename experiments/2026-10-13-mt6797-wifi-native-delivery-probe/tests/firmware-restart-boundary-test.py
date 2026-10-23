#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline actual-source restart refusal audit; no firmware, kernel or device I/O."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('base_tree', type=Path)
p.add_argument('mac_tree', type=Path)
p.add_argument('sealed_kmsg', type=Path)
a = p.parse_args()
raw = a.sealed_kmsg.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '006210923ecddecc6c9f652e00b23f4c910e3d828c4d3b2cc69787e66c7c41e4'
records = {int(m[1]): (int(m[2]), m[3]) for line in raw.splitlines()
           if (m := re.match(rb'^\d+,(\d+),(\d+),[^;]*;(.*)', line))}
assert len(records) == 4966
for label, credit, event, expected in (('pairwise', 2031, 2035, 5059), ('group', 2042, 2043, 1079)):
    t, msg = records[credit]
    end, done = records[event]
    assert msg.endswith(b'one-shot WLAN join credit: pages=1 remaining=0')
    assert b'one-shot WLAN join key done:' in done
    assert ('after='+label).encode() in done
    assert end - t == expected > 0
    print(f'{label}: released-page record {credit} precedes key event {event} by {expected} us')
rel = Path('drivers/net/wireless/mediatek/mt6797')
hif = (a.base_tree / rel / 'hif.c').read_text()
consys = (a.base_tree / 'drivers/soc/mediatek/mt6797-consys.c').read_text()
mac = (a.mac_tree / rel / 'mac.c').read_text()

def function(source, signature):
    start = source.index(signature)
    brace = source.index('\n{', start) + 1
    depth = 0
    # Selected functions have balanced comments/strings; no brace occurs in
    # their strings. Verify exact trailing newline rather than parsing C anew.
    for n in range(brace, len(source)):
        depth += (source[n] == '{') - (source[n] == '}')
        if depth == 0:
            assert source[n:n+2] == '}\n'
            return source[start:n+2]
    raise AssertionError('unterminated source function')

fail = function(hif, 'static int mt6797_hif_fail(')
start = function(hif, 'int mt6797_hif_start_submit(')
mac_start = function(mac, 'static int mt6797_mac_start(')
trigger = function(consys, 'static ssize_t firmware_start_after_wmt_store(')
guard_start = trigger.index('\tif (owner != &mt6797_consys')
guard_end = trigger.index('\n\tret = mtk_pm_domain_confirmed_off', guard_start)
guard = trigger[guard_start:guard_end]
provider_start = consys.index('\tif (mt6797_consys.bound) {')
provider_end = consys.index('\n\tret = mt6797_consys_resolve', provider_start)
provider_guard = consys[provider_start:provider_end]
assert '.suppress_bind_attrs = true' in consys
assert 'builtin_platform_driver(mt6797_consys_driver)' in consys
registration = consys[consys.index('static struct platform_driver mt6797_consys_driver'): ]
assert '.remove' not in registration
assert 'owner->deferred_start_attempted' in guard
worker = function(consys, 'static void mt6797_consys_probe_firmware_start(')
stop_tail = worker[worker.index('\nstopped:'):]
assert stop_tail.count(';') == 2  # one semicolon in log string, one statement
assert 'state retained' in stop_tail
assert not re.search(r'\b(?:reset_control_assert|mt6797_hif_free|mt6797_mac_unregister)\s*\(', stop_tail)
code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
typedef uint8_t u8;
typedef uint64_t u64;
#define IS_ENABLED(x) 1
#define MT6797_HIF_WRITE 1
#define MT6797_NORMAL_COLD 0
struct mt6797_hif_pio_result { int unused; };
struct mt6797_hif { int mutex, io, first_error; void *transaction;
 struct { int phase; } normal;
 bool start_attempted; u64 start_deadline_ns; u8 scratch[2560]; };
static unsigned int sends;
static bool mutex_trylock(int *m) { (void)m; return true; }
static void mutex_lock(int *m) { (void)m; }
static void mutex_unlock(int *m) { (void)m; }
static int mt6797_hif_enter(struct mt6797_hif *h, u64 n) { (void)n; return h->first_error; }
static int mt6797_hif_guard(struct mt6797_hif *h) { return h->first_error; }
static void mt6797_init_abort(void *t) { (void)t; }
static void mt6797_normal_abort(void *t) { (void)t; }
static int mt6797_start_begin(void *t, const u8 *p, size_t n, unsigned int s) { (void)t;(void)p;(void)n;(void)s;return 0; }
static int mt6797_start_submitted(void *t, int e) { (void)t;return e; }
static int mt6797_hif_pio_transfer(int *io, int port, int dir, u8 *p, size_t n, size_t cap, struct mt6797_hif_pio_result *r) {
 (void)io;(void)port;(void)dir;(void)p;(void)n;(void)cap;(void)r; sends++;return 0;
}
struct mt6797_mac { int mutex, first_error; bool scan_ready, configured, closing, join_closed, started; };
struct ieee80211_hw { void *priv; };
struct owner { bool bound, deferred_start_armed, wmt_init_complete, deferred_start_attempted; };
static struct owner mt6797_consys;
static int trigger_guard(struct owner *owner) {
 int ret;
'''+guard+r'''
 return 0;
out: return ret;
}
'''+fail+start+mac_start+r'''
int main(void) {
 u8 command[16]={0}; struct mt6797_hif h={0};
 struct mt6797_mac m={.scan_ready=true,.configured=true};
 struct ieee80211_hw hw={.priv=&m};
 assert(reprobe_guard()==0);
 mt6797_consys=(struct owner){.bound=true,.deferred_start_armed=true,.wmt_init_complete=true};
 assert(reprobe_guard()==-EBUSY);
 assert(trigger_guard(&mt6797_consys)==0);
 mt6797_consys.deferred_start_attempted=true;
 assert(trigger_guard(&mt6797_consys)==-ENODEV);
 assert(mt6797_hif_start_submit(&h,command,16,3,100)==0 && sends==1);
 assert(mt6797_hif_start_submit(&h,command,16,3,100)==-EIO && sends==1);
 assert(h.first_error==-EIO);
 /* A successful mac80211 start is only host admission. It did not repeat
  * HIF START, capability, board record or regulatory initialization. */
 assert(mt6797_mac_start(&hw)==0 && sends==1);
 {
  bool all_required_start_steps_repeated = sends==2;
  assert(!all_required_start_steps_repeated); /* offline restart REFUSED */
 }
 m.join_closed=true;
 assert(mt6797_mac_start(&hw)==-EOPNOTSUPP && sends==1);
 puts("actual source: provider re-probe refuses retained bound owner; deferred second trigger refuses; HIF duplicate START refuses/poisons with no send; host-only start cannot certify restart PASS");
 return 0;
}
'''
provider_helper = 'static int reprobe_guard(void) {\n int ret=0;\n' + provider_guard + '\nout_unlock: return ret;\n}\n'
code = code.replace('static int trigger_guard(', provider_helper + 'static int trigger_guard(')
with tempfile.TemporaryDirectory(prefix='firmware-restart-refusal-') as d:
    source, binary = Path(d)/'test.c', Path(d)/'test'
    source.write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                    str(source),'-o',str(binary)],check=True,timeout=30)
    subprocess.run([str(binary)],check=True,timeout=30)
print('provider_reprobe=REFUSED; no removal/reset lifecycle; no available firmware restart boundary')
