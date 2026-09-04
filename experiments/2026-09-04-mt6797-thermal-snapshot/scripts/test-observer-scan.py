#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute actual scan function bodies with injected IO, on Buildbox only.

This is a userspace C oracle, not a kernel build or a hardware timing test.
The input must be the validated prepared tree containing the observer patch.
"""
from pathlib import Path
import argparse
import hashlib
import re
import resource
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
assert str(source) == '/workspace/gemini-pda/src/linux-7.1.3-series-source'
text = (source / 'drivers/thermal/mediatek/auxadc_thermal.c').read_text()


def function(name):
    start = text.index(name + '(')
    start = text.rfind('\n', 0, start) + 1
    end = text.index('\n}', start) + 2
    body = text[start:end]
    if not body.startswith('static'):
        body = 'static int\n' + body
    return body


validity = function('mtk_thermal_temp_is_valid')
assert 'temp >= MT8173_TEMP_MIN' in validity and 'temp <= MT8173_TEMP_MAX' in validity
limits = []
for name in ('MT8173_TEMP_MIN', 'MT8173_TEMP_MAX'):
    match = re.search(r'^#define\s+' + name + r'\s+([^\n]+)', text, re.M)
    assert match, name
    limits.append('#define ' + name + ' ' + match[1])
bank = function('mtk_thermal_bank_temperature_capture')
scan = function('mtk_read_temp_scan')
poll = function('mtk_read_temp')
assert bank.count('readl(') == 1
assert bank.count('mt->raw_to_mcelsius(') == 1
assert scan.count('mtk_thermal_get_bank(') == 1
assert scan.count('mtk_thermal_put_bank(') == 1
assert 'temperature, NULL)' in poll
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <limits.h>
#include "mt6797_thermal_snapshot.h"
#define THERMAL_TEMP_INVALID (-274000)
#define max(a, b) ({ __typeof__(a) va = (a); __typeof__(b) vb = (b); va > vb ? va : vb; })
struct mtk_thermal;
struct bank_data { int num_sensors; int sensors[2]; };
struct mtk_thermal_data { int num_banks; struct bank_data bank_data[6]; int msr[2]; };
struct mtk_thermal_bank { struct mtk_thermal *mt; int id; };
struct mtk_thermal {
    const struct mtk_thermal_data *conf;
    void *thermal_base;
    struct mtk_thermal_bank banks[6];
    int (*raw_to_mcelsius)(struct mtk_thermal *, int, int32_t);
};
struct thermal_zone_device { struct mtk_thermal *mt; };
static struct mtk_thermal *thermal_zone_device_priv(struct thermal_zone_device *tz) { return tz->mt; }
static int temperatures[7], reads, conversions, bank_gets, bank_puts, selected, held;
static const int expected_banks[] = {0, 1, 2, 2, 3, 4, 5};
static const int expected_sensors[] = {0, 3, 1, 2, 1, 1, 1};
static unsigned char registers[8];
static uint32_t readl(void *address) {
    assert(held && reads < 7 && selected == expected_banks[reads]);
    assert(address == registers + ((reads == 3) ? 4 : 0));
    return reads++;
}
static int convert(struct mtk_thermal *mt, int sensor, int32_t raw) {
    (void)mt;
    assert(held && raw == conversions && sensor == expected_sensors[conversions]);
    return temperatures[conversions++];
}
static bool mtk_thermal_temp_is_valid(int t) { return t >= -20000 && t <= 150000; }
static void mtk_thermal_get_bank(struct mtk_thermal_bank *bank) {
    assert(!held && bank->id == bank_gets);
    selected = bank->id; held = 1; bank_gets++;
}
static void mtk_thermal_put_bank(struct mtk_thermal_bank *bank) {
    assert(held && bank->id == bank_puts);
    held = 0; bank_puts++;
}
static void reset_counts(void) { reads = conversions = bank_gets = bank_puts = held = 0; }
static void check_counts(void) { assert(reads == 7 && conversions == 7 && bank_gets == 6 && bank_puts == 6 && !held); }
'''
main = r'''
int main(void) {
    const struct mtk_thermal_data conf = {
        .num_banks = 6,
        .bank_data = {{1,{0,0}}, {1,{3,0}}, {2,{1,2}}, {1,{1,0}}, {1,{1,0}}, {1,{1,0}}},
        .msr = {0,4},
    };
    struct mtk_thermal mt = {.conf=&conf, .thermal_base=registers, .raw_to_mcelsius=convert};
    struct thermal_zone_device tz = {.mt=&mt};
    int mask, slot, normal, observed, expected;
    for (slot = 0; slot < 6; slot++) {
        mt.banks[slot].mt = &mt;
        mt.banks[slot].id = slot;
    }
    for (mask = 0; mask < 128; mask++) {
        struct mt6797_thermal_snapshot_budget budget = {};
        struct mt6797_thermal_snapshot snapshot = {};
        expected = THERMAL_TEMP_INVALID;
        for (slot = 0; slot < 7; slot++) {
            temperatures[slot] = (mask & (1 << slot)) ? 35000 + slot * 100 : 150001;
            if (temperatures[slot] <= 150000 && temperatures[slot] > expected)
                expected = temperatures[slot];
        }
        reset_counts();
        assert(mtk_read_temp(&tz, &normal) == 0);
        check_counts();
        assert(normal == expected && budget.attempts == 0);
        assert(mt6797_thermal_snapshot_begin(&budget, &snapshot, 1) == 0);
        reset_counts();
        assert(mtk_read_temp_scan(&mt, &observed, &snapshot) == 0);
        check_counts();
        assert(normal == observed && snapshot.count == 7 && snapshot.valid_mask == (unsigned)mask);
        for (slot = 0; slot < 7; slot++)
            assert(snapshot.samples[slot].temperature == temperatures[slot]);
        int ret = mt6797_thermal_snapshot_finish(&snapshot, 2, observed);
        assert((ret == 0) == (mask == 127));
        assert(!snapshot.active && snapshot.complete == (mask == 127));
    }
    puts("validity_patterns=128 scans=256 reads_per_scan=7 bank_lock_pairs_per_scan=6 return_equivalence=pass");
    return 0;
}
'''
preamble = preamble.replace(
    'static bool mtk_thermal_temp_is_valid(int t) { return t >= -20000 && t <= 150000; }',
    '\n'.join(limits) + '\n' + validity)

# Temporary files remain below a managed Buildbox work root and are always removed.
managed = Path('/workspace/gemini-pda/thermal-observer-work')
managed.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='scan-oracle.', dir=managed) as work:
    root = Path(work)
    (root / 'linux').mkdir()
    for name, content in {
        'errno.h': '#include <asm-generic/errno.h>\n',
        'limits.h': '#include <limits.h>\n',
        'types.h': '#include <stdint.h>\n#include <stdbool.h>\ntypedef uint32_t u32;\ntypedef uint64_t u64;\n',
    }.items():
        (root / 'linux' / name).write_text(content)
    (root / 'mt6797_thermal_snapshot.h').write_bytes(
        (source / 'drivers/thermal/mediatek/mt6797_thermal_snapshot.h').read_bytes())
    (root / 'oracle.c').write_text(preamble + '\n' + bank + '\n' + scan + '\n' + poll + '\n' + main)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I', str(root),
                    str(root / 'oracle.c'), '-o', str(root / 'oracle')], check=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    subprocess.run([str(root / 'oracle')], check=True)
    positive = (root / 'oracle.c').read_text()
    mutations = {
        'extra-read': ('raw = readl(', 'raw = readl(mt->thermal_base + conf->msr[i]); raw = readl('),
        'missing-capture': ('if (snapshot)', 'if (0 && snapshot)'),
        'invalid-return': ('temp = THERMAL_TEMP_INVALID;', 'temp = 0;'),
        'missing-unlock': ('mtk_thermal_put_bank(bank);', '(void)bank;'),
    }
    for name, (old, new) in mutations.items():
        assert positive.count(old) == 1, name
        (root / 'oracle.c').write_text(positive.replace(old, new))
        # Missing-unlock intentionally leaves an unused stub; ignore that only.
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-I', str(root),
                        str(root / 'oracle.c'), '-o', str(root / 'oracle')], check=True)
        result = subprocess.run([str(root / 'oracle')], capture_output=True)
        assert result.returncode != 0, name
    print('scan_mutations_rejected=4')
print('driver_sha256=' + hashlib.sha256(text.encode()).hexdigest())
