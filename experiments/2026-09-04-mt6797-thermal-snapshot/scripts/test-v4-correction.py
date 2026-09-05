#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise extracted production V4 decoder/converter and rejecting mutants."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('edit', HERE / 'correct-v4-conversion.py')
edit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edit)

PREAMBLE = r'''
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
typedef int32_t s32;
typedef uint32_t u32;
typedef int64_t s64;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) 4095U
#define THERMAL_TEMP_INVALID INT_MIN
@ENUM@
@MAP@
struct config { int num_sensors; const int *vts_index; };
struct mtk_thermal {
    int adc_ge, adc_oe, degc_cali, o_slope, o_slope_sign;
    int vts[MAX_NUM_VTS]; const struct config *conf;
};
@FUNCTIONS@
/* Independently expressed reference contract; index expectation is explicit. */
static int reference(struct mtk_thermal *m, int sensor, int raw)
{
    int ix = sensor == 4 ? 5 : sensor;
    int64_t oe=m->adc_oe-512;
    int64_t gain=10000+((int64_t)(m->adc_ge-512)*10000)/4096;
    int64_t room=(((m->vts[ix]+3350-oe)*10000/4096)*10000)/gain;
    int64_t sample=(((((int64_t)raw-oe)*10000)>>12)*10000)/gain;
    int64_t delta=(sample-room)*15/18;
    return (int)((m->degc_cali*5-delta*1000/(1663+(m->o_slope_sign?-1:1)*m->o_slope*10))*100);
}
static void words(u32 *b, int ge, int oe, int degree, int slope, int sign, int id, int en, const int *v)
{
    b[0]=((u32)ge<<22)|((u32)oe<<12)|((u32)id<<9)|v[2];
    b[1]=((u32)slope<<26)|((u32)v[0]<<17)|((u32)v[1]<<8)|((u32)sign<<7)|((u32)degree<<1)|en;
    b[2]=((u32)v[3]<<23)|((u32)v[4]<<14);
}
#define REQUIRE(c) do { if (!(c)) { fprintf(stderr,"refusal_line=%d\n",__LINE__); return 1; } } while (0)
int main(void)
{
    const struct config conf={5,mt6797_vts_index};
    struct mtk_thermal m={.conf=&conf};
    int coefficients[]={0,97,260,484,401};
    u32 b[3]; unsigned long conversions=0, masks=0, decodes=0;
    for (int id=0;id<2;id++) for(int sign=0;sign<2;sign++) {
        words(b,512,512,40,63,sign,id,1,coefficients);
        REQUIRE(!mtk_thermal_extract_efuse_v4(&m,b)); decodes++;
        REQUIRE(m.adc_ge==512 && m.adc_oe==512 && m.degc_cali==40);
        REQUIRE(m.o_slope==(id?63:0) && m.o_slope_sign==sign);
        REQUIRE(m.vts[0]==0 && m.vts[1]==97 && m.vts[2]==260 && m.vts[3]==484 && m.vts[5]==401);
        m.vts[4]=123; /* Unused VTS5 must never supply ABB. */
        REQUIRE(raw_to_mcelsius_v4(&m,-1,3000)==INT_MIN);
        REQUIRE(raw_to_mcelsius_v4(&m,5,3000)==INT_MIN);
        for (int sensor=0;sensor<5;sensor++) for(int raw=1;raw<4096;raw++)
            REQUIRE(raw_to_mcelsius_v4(&m,sensor,raw)==reference(&m,sensor,raw));
    }
    /* Reject decoder boundary mutations before trusting its output. */
    const int bad[][3]={{264,512,40},{759,512,40},{512,264,40},{512,759,40},{512,512,0}};
    for (unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++) {
        words(b,bad[i][0],bad[i][1],bad[i][2],0,0,1,1,coefficients);
        REQUIRE(mtk_thermal_extract_efuse_v4(&m,b)==-EINVAL);decodes++;
    }
    words(b,512,512,40,0,0,1,0,coefficients);
    REQUIRE(mtk_thermal_extract_efuse_v4(&m,b)==-EINVAL);decodes++;
    for(int sensor=0;sensor<5;sensor++) {
        int keep=coefficients[sensor];coefficients[sensor]=485;
        words(b,512,512,40,0,0,1,1,coefficients);
        REQUIRE(mtk_thermal_extract_efuse_v4(&m,b)==-EINVAL);decodes++;
        coefficients[sensor]=keep;
    }
    const int limits[]={265,512,758}, degrees[]={1,40,63}, slopes[]={0,31,63};
    for(int g=0;g<3;g++) for(int o=0;o<3;o++) for(int d=0;d<3;d++)
    for(int s=0;s<3;s++) for(int sign=0;sign<2;sign++) {
        words(b,limits[g],limits[o],degrees[d],slopes[s],sign,1,1,coefficients);
        REQUIRE(!mtk_thermal_extract_efuse_v4(&m,b));decodes++;
        m.vts[4]=123;
        for(int sensor=0;sensor<5;sensor++) {
            int previous=INT_MAX;
            REQUIRE(raw_to_mcelsius_v4(&m,sensor,0)==INT_MIN);
            REQUIRE(raw_to_mcelsius_v4(&m,sensor,4096)==INT_MIN);
            for(int raw=1;raw<4096;raw++) {
                int actual=raw_to_mcelsius_v4(&m,sensor,raw);
                REQUIRE(actual==reference(&m,sensor,raw));
                REQUIRE(actual<=previous && actual%100==0);previous=actual;
                REQUIRE(raw_to_mcelsius_v4(&m,sensor,raw|0x1000)==actual);
                REQUIRE(raw_to_mcelsius_v4(&m,sensor,raw|INT_MIN)==actual);
                conversions++;masks+=2;
            }
        }
    }
    printf("decode_cases=%lu\nconversion_grid_cases=%lu\nupper_mask_cases=%lu\ndistinct_sensor_ID_cases=81900\n",decodes,conversions,masks);
    return 0;
}
'''


def translation(source):
    a=source.index('enum {\n\tVTS1,'); b=source.index('\n};',a)+3
    enum=source[a:b]
    a=source.index('static const int mt6797_vts_index['); b=source.index('\n};',a)+3
    mapping=source[a:b].replace('MT6797_NUM_SENSORS','5')
    funcs='\n'.join(edit.function(source,n) for n in ('raw_to_mcelsius_v4','mtk_thermal_extract_efuse_v4'))
    return PREAMBLE.replace('@ENUM@',enum).replace('@MAP@',mapping).replace('@FUNCTIONS@',funcs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    if args.source.is_symlink(): raise ValueError('symlinked source')
    original=args.source.read_text(); corrected=edit.corrected(original)
    # The sole changed span is V4 conversion. Decoder, bank layout and other SoCs stay byte-identical.
    old=edit.function(original,'raw_to_mcelsius_v4'); new=edit.function(corrected,'raw_to_mcelsius_v4')
    if corrected.replace(new,old)!=original: raise ValueError('edit escaped conversion')
    try: edit.corrected(original+'\n')
    except ValueError: pass
    else: raise ValueError('unrecognized source accepted')
    mutations={
        'offset': ('s64 offset = mt->adc_oe - 512;', 's64 offset = mt->adc_oe;'),
        'sensor-index': ('mt->vts[vts_index]', 'mt->vts[sensno]'),
        'zero-code': ('if (!(raw & GENMASK(11, 0)))', 'if (raw == 0)'),
        'sensor-bound': ('sensno >= mt->conf->num_sensors', 'sensno > mt->conf->num_sensors'),
        'calibration-enable': ('if (!(buf[1] & BIT(0)))', 'if (0)'),
        'GE-bound': ('mt->adc_ge < 265', 'mt->adc_ge < 264'),
        'OE-bound': ('mt->adc_oe > 758', 'mt->adc_oe > 759'),
        'ID-slope': ('if (!((buf[0] >> 9) & 0x1))', 'if (0)'),
        'VTS-bound': ('> 484)', '> 485)'),
        'VTS4-field': ('(buf[2] >> 23) & 0x1ff', '(buf[2] >> 14) & 0x1ff'),
    }
    with tempfile.TemporaryDirectory(prefix='gemini-v4-correction-',dir='/tmp') as tmp:
        root=Path(tmp)
        for label,source in [('corrected',corrected)]+[(label,corrected.replace(a,b)) for label,(a,b) in mutations.items()]:
            if label!='corrected' and source==corrected: raise ValueError('mutation did not apply: '+label)
            c=root/'test.c'; exe=root/'test';c.write_text(translation(source))
            subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-fsanitize=undefined,bounds',
                            '-fno-sanitize-recover=all',str(c),'-o',str(exe)],check=True,capture_output=True)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            if label=='corrected':
                if result.returncode: raise ValueError(result.stderr)
                print(result.stdout,end='')
            elif not result.returncode: raise ValueError('mutation survived: '+label)
        print('mutations_rejected='+str(len(mutations)))
    print('corrected_source_sha256='+hashlib.sha256(corrected.encode()).hexdigest())
    print('source_boundary=conversion-only\nsource_identity_refusal=pass\ntemporary_harness_removed=yes\ndevice_access=none\nkernel_build=none')


if __name__=='__main__': main()
