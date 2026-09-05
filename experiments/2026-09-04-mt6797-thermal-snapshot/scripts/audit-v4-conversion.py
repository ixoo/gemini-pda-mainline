#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile only the exact pure conversion in a temporary host harness."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

SOURCE_SHA = 'e2ce72fa105be597a5c7a3cea37499512093c86ba4cc4ac85b92c10b0254c481'

HARNESS = r'''
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
typedef int32_t s32;
typedef int64_t s64;
#define GENMASK(h,l) 4095U
#define THERMAL_TEMP_INVALID INT_MIN
struct mtk_thermal { int adc_ge, adc_oe, degc_cali, o_slope, o_slope_sign; int vts[6]; };
@FUNCTION@
@NORMALIZED@
/* Independent arithmetic expression of the pinned reference contract.
 * Synthetic encoded offset is normalized; room numerator is positive.
 * All integer division truncates toward zero. No reference code is copied. */
static int reference(struct mtk_thermal *m, int sensor, int raw)
{
    int64_t offset = m->adc_oe - 512;
    int64_t gain = 10000 + ((int64_t)(m->adc_ge - 512) * 10000) / 4096;
    int64_t room = (((m->vts[sensor] + 3350 - offset) * 10000 / 4096) * 10000) / gain;
    int64_t sample = (((((int64_t)raw - offset) * 10000) >> 12) * 10000) / gain;
    int64_t change = (sample - room) * 15 / 18;
    int64_t denominator = 1663 + (m->o_slope_sign ? -1 : 1) * m->o_slope * 10;
    return (int)((m->degc_cali * 5 - change * 1000 / denominator) * 100);
}
int main(void)
{
    const int gain[] = {265,512,758}, offset[] = {265,512,758};
    const int vts[] = {0,260,484}, degree[] = {1,40,63}, slope[] = {0,31,63};
    unsigned long cases=0, different=0, accepted_different=0, bounded_different=0, mask_cases=0;
    int maximum=0, accepted_maximum=0, minimum=INT_MAX, highest=INT_MIN, witness=0;
    for (unsigned g=0; g<3; g++) for (unsigned o=0; o<3; o++)
    for (unsigned v=0; v<3; v++) for (unsigned d=0; d<3; d++)
    for (unsigned s=0; s<3; s++) for (int sign=0; sign<2; sign++) {
        struct mtk_thermal m = {gain[g],offset[o],degree[d],slope[s],sign,{0}};
        for (int i=0;i<6;i++) m.vts[i]=vts[v];
        int previous=INT_MAX;
        if (raw_to_mcelsius_v4(&m,0,0)!=INT_MIN || raw_to_mcelsius_v4(&m,0,4096)!=INT_MIN) return 1;
        for (int raw=1;raw<=4095;raw++) {
            int actual=raw_to_mcelsius_v4(&m,0,raw), expected=reference(&m,0,raw);
            if (normalized(&m,0,raw)!=expected) return 4;
            if (actual>previous || actual%100) return 2;
            previous=actual;
            if (actual<minimum) minimum=actual;
            if (actual>highest) highest=actual;
            int delta=abs(actual-expected);
            if (delta) different++;
            if (delta>maximum) maximum=delta;
            if (actual>=-20000 && actual<=150000 && expected>=-20000 && expected<=150000) {
                if (delta) accepted_different++;
                if (delta>accepted_maximum) accepted_maximum=delta;
                if (delta && actual>=0 && actual<=58500 && expected>=0 && expected<=58500) bounded_different++;
                if (delta && !witness && actual>=0 && actual<=58500 && expected>=0 && expected<=58500) {
                    printf("synthetic_witness=ge:%d,oe:%d,vts:%d,deg:%d,slope:%d,sign:%d,raw:%d,actual:%d,reference:%d\n",
                           m.adc_ge,m.adc_oe,m.vts[0],m.degc_cali,m.o_slope,sign,raw,actual,expected);
                    witness=1;
                }
            }
            if (raw_to_mcelsius_v4(&m,0,raw|0x1000)!=actual ||
                raw_to_mcelsius_v4(&m,0,raw|INT_MIN)!=actual) return 3;
            mask_cases+=2; cases++;
        }
    }
    printf("synthetic_cases=%lu\nreference_differences=%lu\nmaximum_difference_mC=%d\naccepted_range_differences=%lu\naccepted_range_maximum_difference_mC=%d\noutput_min_mC=%d\noutput_max_mC=%d\nupper_mask_cases=%lu\nmonotonicity=pass\nquantization=pass\n",cases,different,maximum,accepted_different,accepted_maximum,minimum,highest,mask_cases);
    printf("bounded_range_differences=%lu\nnormalized_reference_equivalence=pass\n", bounded_different);
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    if args.source.is_symlink() or hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('production source identity mismatch')
    source = raw.decode()
    start = source.index('static int raw_to_mcelsius_v4(')
    end = source.index('\n}', start) + 2
    function = source[start:end]
    # Scoped context installs cleanup immediately; no source-tree copy or device IO.
    with tempfile.TemporaryDirectory(prefix='gemini-v4-audit-', dir='/tmp') as name:
        root = Path(name)
        c = root / 'audit.c'
        normalized = function.replace('raw_to_mcelsius_v4', 'normalized').replace('mt->adc_oe', '(mt->adc_oe - 512)')
        c.write_text(HARNESS.replace('@FUNCTION@', function).replace('@NORMALIZED@', normalized))
        exe = root / 'audit'
        subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(c), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print('production_source_sha256=' + SOURCE_SHA)
    print('kernel_build=none\ndevice_access=none\nprivate_calibration_used=no\ntemporary_harness_removed=yes')


if __name__ == '__main__':
    main()
