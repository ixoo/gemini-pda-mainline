#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Compile actual reporting helpers and verify their production wiring; no kernel build."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('kernel_tree', type=Path)
a = p.parse_args()
s = (a.kernel_tree / 'drivers/net/wireless/mediatek/mt6797/mac.c').read_text()
start = s.index('static const char * __maybe_unused\nmt6797_mac_deauth_verdict(')
end = s.index('\n#ifdef CONFIG_MT6797_CCMP_TX_PID_REUSE', start)
helpers = s[start:end]
assert s.count('slots=retired deauth=%u delivery=%s') == 2
assert s.count('mt6797_mac_deauth_verdict(mac));') == 2
assert 'mac->join_deauth_timed_out = true;\n\tmt6797_mac_deauth_delivery(mac, "timeout"' in s
for name in ('join_deauth_status_valid', 'join_deauth_status_late', 'join_deauth_timed_out'):
    assert f'mac->{name} = false;' in s
assert 'mac->join_deauth_status = result.status;' in s
assert s.count('mac->join_deauth_status = result.status;') == 3
assert re.search(r'late-unclassified".*?return false;', s, re.S)
assert 'ack = result.status == 0;' in s
assert 'mac->join_deauth_done = ack;' in s
c = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#define __maybe_unused __attribute__((unused))
struct mt6797_mac {
 bool join_deauth_status_valid, join_deauth_status_late, join_deauth_timed_out;
 unsigned char join_deauth_status, join_lifetimes;
};
static char line[512];
static void pr_info(const char *format, ...) __attribute__((format(printf, 1, 2)));
static void pr_info(const char *format, ...) {
 va_list args; va_start(args, format); vsnprintf(line, sizeof(line), format, args); va_end(args);
}
'''+helpers+r'''
int main(void) {
 struct mt6797_mac m = { .join_lifetimes = 1 }, before;
 assert(!strcmp(mt6797_mac_deauth_verdict(&m), "unclassified"));
 m.join_deauth_timed_out = true;
 assert(!strcmp(mt6797_mac_deauth_verdict(&m), "missing"));
 for (unsigned int status = 0; status < 256; status++) {
  for (unsigned int late = 0; late < 2; late++) {
   m.join_deauth_status_valid = true;
   m.join_deauth_status = status;
   m.join_deauth_status_late = late;
   before = m;
   assert(!strcmp(mt6797_mac_deauth_verdict(&m), status == 0 ? "transmitted" :
                  status == 5 ? "flushed" : "unclassified"));
   mt6797_mac_deauth_delivery(&m, late ? "late" : "completion", true, status, late);
   assert(!memcmp(&m, &before, sizeof(m)));
   assert(strstr(line, status == 0 ? "transmitted=1 flushed=0" :
                 status == 5 ? "transmitted=0 flushed=1" : "unclassified=1"));
   mt6797_mac_deauth_delivery(&m, "cleanup", true, status, late);
   assert(!memcmp(&m, &before, sizeof(m)));
  }
 }
 puts("actual delivery helpers: D2 normal/EMI1 late status0, GTK5-8 status5, timeout, unknown and all statuses PASS");
}
'''
with tempfile.TemporaryDirectory(prefix='deauth-delivery-') as d:
    source, binary = Path(d) / 'test.c', Path(d) / 'test'
    source.write_text(c)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                    '-fsanitize=address,undefined', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    # Option-off shape: both reporting functions may have no caller.
    source.write_text(c[:c.index('int main(void)')] + 'int main(void) { return 0; }\n')
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wformat=2',
                    str(source), '-o', str(binary)], check=True)
print('actual source wiring: stage3, normal/late/unknown/timeout, rearm and unchanged ACK predicate PASS')
