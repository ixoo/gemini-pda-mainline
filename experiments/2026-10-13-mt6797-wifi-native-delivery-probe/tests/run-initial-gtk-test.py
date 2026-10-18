#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Actual GTK checker/callbacks plus frozen PTK/pthread fixtures; host only."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('parent', type=Path, help='C10 plus independent 0203')
p.add_argument('child', type=Path, help='initial-GTK source')
p.add_argument('--gtk3', action='store_true', help='also validate the admitted capacity/handoff overlays')
p.add_argument('--timeout-observer', action='store_true', help='also validate the refused-timeout observer')
p.add_argument('--beacon-observer', action='store_true', help='also validate owned-beacon recency')
p.add_argument('--timeout-handler', action='store_true', help='validate the conditional owned timeout handler')
p.add_argument('--pm-connected', action='store_true', help='validate owned PM indication before keys')
p.add_argument('--connection-monitor', action='store_true', help='also validate standard loss reporting')
a = p.parse_args()
a.pm_connected = a.pm_connected or a.connection_monitor
a.timeout_handler = a.timeout_handler or a.pm_connected
a.beacon_observer = a.beacon_observer or a.timeout_handler
a.timeout_observer = a.timeout_observer or a.beacon_observer
a.gtk3 = a.gtk3 or a.timeout_observer
fixtures = Path(__file__).resolve().parent
# Pin the frozen fixtures whose narrow substitutions are used below.
for name, digest in {
    'ccmp-rx-test.c': '8a34df09b1d89644952de95e363fadec170f569fd5b39f75239d8a87606ba96b',
    'native-rx-test.c': '9b3e1e355425cc69fdcd6f6e78058225876253967bb632b1441a22c976cbbae6',
    'ccmp-monitor-state-test.c': 'b9f907551aaf4f6ffdfcc2f8919ab37e7404106330869b3914715a422b177ce4',
    'run-native-beacon-test.py': '078b69b048c55e6a1808d03f7bdc9285db8a985016d22b7bac49a56e9fab663d',
}.items():
    assert hashlib.sha256((fixtures / name).read_bytes()).hexdigest() == digest, name
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = a.parent.resolve() / rel, a.child.resolve() / rel
assert hashlib.sha256((child / 'ccmp-rx.h').read_bytes()).hexdigest() == \
    '35b581f1cd3abdda66e8b392b39bd538875975e2254e80488dc1cc8dbbec85a0'
assert hashlib.sha256((child / 'ccmp-gtk-rx.h').read_bytes()).hexdigest() == \
    '44deda239a5c824469b69489e21fec84ef0af8a26ee7b13f95b1f764ab437bb1'
assert {x.name for x in child.iterdir()} == {x.name for x in parent.iterdir()} | {'ccmp-gtk-rx.h'}
for x in parent.iterdir():
    if x.is_file() and x.name not in (({'mac.c', 'Kconfig', 'native-diag.h'} if a.gtk3 else {'mac.c', 'Kconfig'}) |
                                        ({'hif.c', 'hif.h', 'join-commands.h', 'join-command-submit.h'} if a.pm_connected else set())):
        assert x.read_bytes() == (child / x.name).read_bytes(), x.name
# Reversing exactly the selected archive must recover every parent file.
archive = fixtures.parents[2] / 'patches/proposals/0204-wifi-mt6797-gate-one-separately-seeded-initial-GTK.patch'
parity_mac = None
observer_parent_mac = None
beacon_parent_mac = None
handler_parent_mac = None
monitor_parent_mac = None
with tempfile.TemporaryDirectory(prefix='gtk-reverse-') as directory:
    import shutil
    recovered = Path(directory)
    shutil.copytree(child, recovered / rel)
    if a.connection_monitor:
        patch = fixtures.parents[2] / 'patches/proposals/0212-wifi-mt6797-own-connection-monitoring-in-PM-required-experiment.patch'
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True, timeout=10)
        monitor_parent_mac = (recovered / rel / 'mac.c').read_text()
    if a.pm_connected:
        patch = fixtures.parents[2] / 'patches/proposals/0211-wifi-mt6797-indicate-PM-connection-from-owned-beacon-before-keys.patch'
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True, timeout=10)
    if a.timeout_handler:
        patch = fixtures.parents[2] / 'patches/proposals/0210-wifi-mt6797-condition-owned-BSS-timeout-on-fresh-beacons.patch'
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True, timeout=10)
        handler_parent_mac = (recovered / rel / 'mac.c').read_text()
    if a.beacon_observer:
        patch = fixtures.parents[2] / 'patches/proposals/0209-wifi-mt6797-retain-owned-beacon-recency-at-refused-timeout.patch'
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True, timeout=10)
        beacon_parent_mac = (recovered / rel / 'mac.c').read_text()
    if a.timeout_observer:
        patch = fixtures.parents[2] / 'patches/proposals/0208-wifi-mt6797-observe-refused-BSS-timeout-and-checked-RX-age.patch'
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=recovered, check=True, timeout=10)
        observer_parent_mac = (recovered / rel / 'mac.c').read_text()
    if a.gtk3:
        for name in ['0207-wifi-mt6797-report-checked-key-classes-and-GTK-ARP-handoff.patch',
                     '0206-wifi-mt6797-bound-low-traffic-CCMP-observation-capacity.patch']:
            overlay = fixtures.parents[2] / 'patches/proposals' / name
            subprocess.run(['git', 'apply', '--reverse', str(overlay)], cwd=recovered,
                           check=True, timeout=10)
    subprocess.run(['git', 'apply', '--reverse', str(archive)], cwd=recovered,
                   check=True, timeout=10)
    files = {x.relative_to(recovered) for x in recovered.rglob('*') if x.is_file()}
    assert files == {rel / x.name for x in parent.iterdir() if x.is_file()}
    for x in parent.iterdir():
        if x.is_file():
            assert x.read_bytes() == (recovered / rel / x.name).read_bytes(), x.name
    if a.gtk3:
        capacity = fixtures.parents[2] / 'patches/proposals/0206-wifi-mt6797-bound-low-traffic-CCMP-observation-capacity.patch'
        subprocess.run(['git', 'apply', str(capacity)], cwd=recovered, check=True, timeout=10)
        parity_mac = (recovered / rel / 'mac.c').read_text()
        assert (recovered / rel / 'native-diag.h').read_bytes() == (child / 'native-diag.h').read_bytes()

old, new = parity_mac or (parent / 'mac.c').read_text(), (child / 'mac.c').read_text()


def function(text, name):
    match = re.search(r'\b' + re.escape(name) + r'\([^;]*?\)\n\{', text)
    assert match, name
    start = match.start()
    return text[start:text.index('\n}\n', start) + 2]


def matching_endif(text, start):
    depth = 0
    for match in re.finditer(r'(?m)^#(if[^\n]*|endif[^\n]*)$', text[start:]):
        if match[1].startswith('if'):
            depth += 1
        elif depth:
            depth -= 1
        else:
            return start + match.start() - 1
    raise AssertionError('missing outer endif')


extractors = (fixtures / 'run-native-beacon-test.py').read_text().replace(
    'text.index("\\n#endif", native_start)', 'matching_endif(text, native_start)').replace(
    'text.index("\\n#endif", account_start)', 'matching_endif(text, account_start)')
tree = ast.parse(extractors)
ns = {'matching_endif': matching_endif}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)],
                        type_ignores=[]), 'existing-native-extractors', 'exec'), ns)

with tempfile.TemporaryDirectory(prefix='initial-gtk-') as directory:
    tmp = Path(directory)
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if sys.platform.startswith('linux'):
        flags += ['-fno-pie', '-no-pie']
    baseline = (fixtures / 'ccmp-rx-test.c').read_text().replace(
        '"../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"',
        '"' + str(fixtures.parents[1] / '2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c') + '"')
    (tmp / 'ptk-baseline.inc').write_text(baseline.replace('int main(void)', 'int ptk_baseline_tests(void)'))
    binary = tmp / 'checker'
    subprocess.run([*flags, '-I', str(tmp), '-I', str(child), str(fixtures / 'ccmp-gtk-rx-test.c'),
                    '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)

    start = new.index('struct mt6797_mac {'); end = new.index('\n};', start) + 3
    names = [
        ('void', 'mt6797_ccmp_observe_terminal'),
        ('void', 'mt6797_ccmp_withdraw'), ('bool', 'mt6797_ccmp_rx_ready'),
        ('void', 'mt6797_ccmp_withheld_arp'), ('void', 'mt6797_ccmp_receive'),
        ('void', 'mt6797_mac_sta_set_decap_offload'), ('int', 'mt6797_ccmp_queue_rx'),
        ('void', 'mt6797_native_diag_rx_report'), ('int', 'mt6797_mac_join_fail_stop'),
        ('int', 'mt6797_ccmp_disable_key'), ('int', 'mt6797_mac_set_key'),
        ('int', 'mt6797_mac_sta_state'), ('int', 'mt6797_native_diag_pre_read'),
        ('void', 'mt6797_native_diag_ordinary_record'), ('void', 'mt6797_mac_tx'),
        ('void', 'mt6797_native_diag_step'), ('bool', 'mt6797_native_diag_tx_fenced')]
    if a.timeout_observer:
        names.append(('bool', 'mt6797_ccmp_timeout_continue') if a.timeout_handler else
                     ('void', 'mt6797_ccmp_timeout_observe'))
        if a.timeout_handler:
            names.append(('int', 'mt6797_mac_join_control_event'))
        assert function(handler_parent_mac or new, 'mt6797_mac_join_control_event') == function(
            observer_parent_mac, 'mt6797_mac_join_control_event'), 'control admission changed'
    if a.beacon_observer:
        assert function(handler_parent_mac or new, 'mt6797_mac_join_work') == function(
            beacon_parent_mac, 'mt6797_mac_join_work'), 'beacon dispatch/ownership changed'
    if a.pm_connected:
        names += [('void', 'mt6797_ccmp_pm_beacon'), ('int', 'mt6797_ccmp_pm_indicate'),
                  ('int', 'mt6797_mac_join_associate'), ('int', 'mt6797_mac_join_cleanup_step')]
    if a.connection_monitor:
        names.append(('void', 'mt6797_ccmp_connection_lost'))
        assert function(new, 'mt6797_mac_tx') == function(monitor_parent_mac, 'mt6797_mac_tx'), 'new TX class'
        assert new.count('ieee80211_hw_set(hw, CONNECTION_MONITOR)') == 1
    obs_start = new.index('struct mt6797_ccmp_observation {')
    obs_end = new.index('\n};', obs_start) + 3
    handler_definitions = ''
    if a.timeout_handler:
        for macro in ['MT6797_JOIN_DATA_BUDGET_MS', 'MT6797_JOIN_GRANT_TAIL_MS',
                      'MT6797_JOIN_TEARDOWN_MARGIN_MS']:
            found = re.findall(r'^#define ' + macro + r' [^\n]+$', new, re.M)
            assert len(found) == 1
            handler_definitions += found[0] + '\n'
    (tmp / 'actual-ccmp-monitor.inc').write_text(handler_definitions + new[obs_start:obs_end] + '\n' + new[start:end] + '\n' + '\n'.join(
        '#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wunused-parameter"\n' +
        'static ' + result + ' ' + function(new, name) + '\n#pragma GCC diagnostic pop'
        for result, name in names))
    event = new.index('\tif (mt6797_join_event(mac->join_packet, bytes, 0x24, 8))')
    end = new.index('\n\tif (mt6797_join_event(mac->join_packet, bytes, 0x11', event)
    (tmp / 'actual-key-event.inc').write_text('static int owned_key_event(struct mt6797_mac *mac, size_t bytes) {\n' +
        new[event:end].rsplit('\n#endif', 1)[0] + '\nreturn -EINVAL; }\n')
    (tmp / 'parent-monitor-step.inc').write_text('static void ' +
        function(old, 'mt6797_native_diag_step').replace('mt6797_native_diag_step(', 'parent_monitor_step(', 1) + '\n')
    dispatch = ns['hooks'](new).replace('static void ' + function(new, 'mt6797_native_diag_rx_report') + '\n', '')
    (tmp / 'actual-dispatch.inc').write_text(dispatch)
    (tmp / 'helper-fixture.inc').write_text(baseline.replace('int main(void)', 'int offline_helper_tests(void)'))
    native = (fixtures / 'native-rx-test.c').read_text().replace('int main(void)', 'int native_layout_tests(void)')
    (tmp / 'native-fixture.inc').write_text('#define own native_own\n#define ap native_ap\n' + native + '\n#undef own\n#undef ap\n')
    callbacks = (fixtures / 'ccmp-monitor-state-test.c').read_text()
    callbacks = callbacks.replace('#include "ccmp-rx.h"', '#include "ccmp-rx.h"\n#include "ccmp-gtk-rx.h"\n#include "normal_command.h"')
    callbacks = callbacks.replace('static void mutex_init(struct mutex *m)',
                                'static struct mutex *seed_receive, *seed_mac;\nstatic void mutex_init(struct mutex *m)')
    callbacks = callbacks.replace('memset(s, 0, sizeof(*s)); s->ccmp.pn[5] = 5;',
        'if (!(k->flags & IEEE80211_KEY_FLAG_PAIRWISE)) {\n'
        ' assert(pthread_mutex_trylock(&seed_receive->lock) == EBUSY);\n'
        ' assert(!pthread_mutex_trylock(&seed_mac->lock)); assert(!pthread_mutex_unlock(&seed_mac->lock)); }\n'
        ' memset(s, 0, sizeof(*s)); s->ccmp.pn[5] = (k->flags & IEEE80211_KEY_FLAG_PAIRWISE) ? 5 : 50;')
    callbacks = callbacks.replace('mutex_init(&m->mutex); mutex_init(&m->ccmp_receive_mutex);',
        'mutex_init(&m->mutex); mutex_init(&m->ccmp_receive_mutex); seed_mac = &m->mutex; seed_receive = &m->ccmp_receive_mutex;')
    callbacks = callbacks.replace('static int submit_error, wait_mode;',
        'static int submit_error, wait_mode, credit_error; static bool withdraw_on_credit, expire_on_credit;')
    callbacks = callbacks.replace('static void ieee80211_get_key_rx_seq(',
        'static bool withdraw_at_gtk_seed; static void gtk_seed_withdraw(void);\nstatic void ieee80211_get_key_rx_seq(')
    callbacks = callbacks.replace('if (!(k->flags & IEEE80211_KEY_FLAG_PAIRWISE)) {\n',
        'if (!(k->flags & IEEE80211_KEY_FLAG_PAIRWISE)) {\n')
    callbacks = callbacks.replace('memset(s, 0, sizeof(*s)); s->ccmp.pn[5] = (k->flags',
        'gtk_seed_withdraw(); memset(s, 0, sizeof(*s)); s->ccmp.pn[5] = (k->flags')
    callbacks = callbacks.replace('static struct mt6797_mac *current;',
        'static struct mt6797_mac *current;\n'
        'static void gtk_seed_withdraw(void) { if (withdraw_at_gtk_seed) { '
        'mutex_lock(&current->mutex); mt6797_ccmp_withdraw(current); mutex_unlock(&current->mutex); } }')
    callbacks = callbacks.replace('m->join_credit_pending = false; m->join_page_debt = 0; return 0;',
        'if (credit_error) { return credit_error; }\n'
        ' if (withdraw_on_credit) { mt6797_ccmp_withdraw(m); }\n'
        ' if (expire_on_credit) { now += 10000 * NSEC_PER_MSEC; }\n'
        ' m->join_credit_pending = false; m->join_page_debt = 0; return 0;')
    callbacks = callbacks.replace('seed_calls = key_submits = 0; submit_error = 0;',
        'seed_calls = key_submits = 0; submit_error = credit_error = 0; withdraw_at_gtk_seed = withdraw_on_credit = expire_on_credit = false;')
    callbacks = callbacks.replace('static int mt6797_hif_native_monitor(void *,',
        'static int mt6797_hif_diag_mask(void *, unsigned int, bool, u64);\nstatic int mt6797_hif_native_monitor(void *,')
    callbacks = callbacks.replace('m->join_deadline = now + 20000 * NSEC_PER_MSEC;',
                                  'm->join_deadline = now + 125000 * NSEC_PER_MSEC;')
    callbacks = callbacks.replace('m->join_data_deadline = now + 15000 * NSEC_PER_MSEC;',
                                  'm->join_data_deadline = now + 120000 * NSEC_PER_MSEC;')
    callbacks = callbacks.replace('now + 10000 * NSEC_PER_MSEC', 'now + 60000 * NSEC_PER_MSEC')
    callbacks = callbacks.replace('now += 10000 * NSEC_PER_MSEC', 'now += 60000 * NSEC_PER_MSEC')
    callbacks = callbacks.replace('m.ccmp_rx.pn[5] == 6 && seed_calls == 1', 'm.ccmp_rx.pn[5] == 6 && seed_calls == 2')
    # Preserve the errno assertion on both Linux and macOS (EPROTO differs).
    callbacks = callbacks.replace('assert(strstr(last_log, "removal_command_credit=0 status=-71"));',
        'char expected_error[64]; snprintf(expected_error, sizeof(expected_error), '
        '"removal_command_credit=0 status=%d ", -EPROTO); assert(strstr(last_log, expected_error));')
    if a.gtk3:
        callbacks = callbacks.replace('#define ETH_ALEN 6', '#define ETH_ALEN 6\n#define ETH_HLEN 14\n#define ETH_P_ARP 0x0806\n'
            'static bool is_multicast_ether_addr(const unsigned char *p) { return p[0] & 1; }\n'
            'static unsigned short get_unaligned_be16(const unsigned char *p) { return (unsigned short)p[0] << 8 | p[1]; }')
        callbacks = callbacks.replace('m.ccmp_queued = 63', 'm.ccmp_queued = 1023').replace('m.ccmp_queued = 64', 'm.ccmp_queued = 1024')
        callbacks = callbacks.replace('m.native_diag_total = 512;', 'm.native_diag_total = 4096;')
        callbacks = callbacks.replace('m.native_diag_total = 511;', 'm.native_diag_total = 4095;').replace('m.native_diag_total == 512', 'm.native_diag_total == 4096')
        callbacks = callbacks.replace('m.native_diag_bytes = MT6797_NATIVE_DIAG_BYTES_MAX -', 'm.native_diag_bytes = MT6797_CCMP_DIAG_BYTES_MAX -')
        callbacks = callbacks.replace('arm/63->64', 'arm/1023->1024')
    if a.timeout_handler:
        callbacks = callbacks.replace('#define NSEC_PER_MSEC 1000000ULL',
            '#define NSEC_PER_MSEC 1000000ULL\n#define NSEC_PER_USEC 1000ULL')
        stub = ('struct mt6797_hif;\n#define min(a, b) ((a) < (b) ? (a) : (b))\n'
                'static unsigned int handler_reads;\n'
                'static int mt6797_hif_read32(struct mt6797_hif *h, unsigned int reg, u64 deadline, u32 *v)\n'
                '{ (void)h; (void)reg; (void)deadline; (void)v; handler_reads++; return -EIO; }\n'
                'static bool skb_queue_empty(const struct sk_buff_head *q) { return !q->head; }\n')
        callbacks = callbacks.replace('#include \"actual-ccmp-monitor.inc\"', stub + '#include \"actual-ccmp-monitor.inc\"')
    if a.pm_connected:
        callbacks = callbacks.replace("#define MT6797_JOIN_BMC_WLAN_INDEX 2\n", "")
        callbacks = callbacks.replace('#include \"ccmp-gtk-rx.h\"', '#include \"ccmp-gtk-rx.h\"\n#include \"join-commands.h\"')
        callbacks = callbacks.replace('#include \"actual-ccmp-monitor.inc\"',
            (fixtures / 'pm-callback-prototypes.inc').read_text() + '\n#include \"actual-ccmp-monitor.inc\"')
        if a.connection_monitor:
            callbacks = callbacks.replace('#include \"actual-ccmp-monitor.inc\"',
                'static void mt6797_ccmp_connection_lost(struct mt6797_mac *, const char *);\n#include \"actual-ccmp-monitor.inc\"')
        stub = 'static int ' + function(callbacks, 'mt6797_mac_join_associate') + '\n'
        assert callbacks.count(stub) == 1
        callbacks = callbacks.replace(stub, '')
        callbacks = callbacks.replace('seed_calls = key_submits = 0;',
            'm->ccmp_pm_connected = true; pm_reset_world(); seed_calls = key_submits = 0;')
        callbacks = callbacks.replace('static int mt6797_mac_join_wait_credit(struct mt6797_mac *m)\n{',
            'static int mt6797_mac_join_wait_credit(struct mt6797_mac *m)\n{\n int rc; if (pm_credit_hook(m, &rc)) return rc;')
        callbacks = callbacks.replace('assert(add && deadline > now);',
            'assert(deadline > now); if (!add) return pm_remove_key(pairwise);')
        anchor = 'assert(!pthread_mutex_trylock(&m->mutex.lock));\n'
        assert callbacks.count(anchor) == 1
        callbacks = callbacks.replace(anchor, anchor +
            ' if (pm_wait_hook(m, c, ticks)) { assert(!pthread_mutex_unlock(&m->mutex.lock)); return c->done; }\n')
    callbacks = callbacks.replace('int main(void)', 'int existing_callbacks(void)')
    callbacks = callbacks.replace('GTK-withhold', 'initial-key ownership').replace('actual monitor engine:', 'actual mask engine (control-call stub):')
    extra = (fixtures / 'initial-gtk-callbacks.inc').read_text()
    if a.gtk3:
        extra = extra.replace('m.ccmp_queued = 64;', 'm.ccmp_queued = 1024;')
        extra = extra.replace('gtk_callback_tests();', 'gtk_callback_tests();\n gtk3_observer_budget_tests();')
        extra = (fixtures / 'gtk3-observer-budget.inc').read_text() + '\n' + extra
    if a.timeout_observer:
        extra = (fixtures / 'timeout-observer.inc').read_text() + '\n' + extra
        extra = extra.replace('gtk_callback_tests();', 'gtk_callback_tests();\n timeout_observer_tests();')
    if a.beacon_observer:
        extra = (fixtures / 'beacon-observer.inc').read_text() + '\n' + extra
        extra = extra.replace('timeout_observer_tests();', 'timeout_observer_tests();\n beacon_observer_tests();')
    if a.timeout_handler:
        extra = extra.replace('mt6797_ccmp_timeout_observe', 'mt6797_ccmp_timeout_continue')
        extra = (fixtures / 'timeout-handler.inc').read_text() + '\n' + extra
        extra = extra.replace('beacon_observer_tests();', 'beacon_observer_tests();\n timeout_handler_tests();')
    if a.pm_connected:
        extra = (fixtures / 'pm-callbacks.inc').read_text() + '\n' + extra
        extra = extra.replace('timeout_handler_tests();', 'timeout_handler_tests();\n pm_callback_tests();')
    if a.connection_monitor:
        callbacks = '#define FIXTURE_CONNECTION_MONITOR 1\n' + callbacks
    (tmp / 'callbacks.c').write_text(callbacks + '\n' + extra)
    binary = tmp / 'callbacks'
    subprocess.run([*flags, '-pthread', '-DCONFIG_MT6797_CCMP_MASK_CONTROL',
        '-DCONFIG_MT6797_CCMP_60S_WINDOW', '-DCONFIG_MT6797_CCMP_INITIAL_GTK',
        '-I', str(tmp), '-I', str(child), str(tmp / 'callbacks.c'), '-o', str(binary)], check=True, timeout=30)
    subprocess.run([str(binary)], check=True, timeout=30)

    for options in [[], ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DCONFIG_MT6797_CCMP_STABLE_EPOCH',
                       '-DCONFIG_MT6797_CCMP_MASK_CONTROL', '-DCONFIG_MT6797_CCMP_60S_WINDOW']]:
        tokens = []
        for label, source in [('parent', old), ('off', new)]:
            path = tmp / (label + '.c'); path.write_text(re.sub(r'^#include[^\n]*\n', '', source, flags=re.M))
            tokens.append(subprocess.run(['cc', '-E', '-P', '-DIS_ENABLED(x)=1', *options, str(path)],
                         capture_output=True, check=True).stdout)
        assert tokens[0] == tokens[1], 'option-off full MAC changed'
print('PASS actual checker/callbacks, original pthread withdrawal, option-off MAC parity; no firmware/key retirement proof')
