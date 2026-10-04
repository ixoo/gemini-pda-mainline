#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate the diagnostic patch on Buildbox from exact prepared Gemian files."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REVISION = '59e00a9144d782e148332009a835b99c43382467'
ROOT = Path('/workspace/gemini-pda')
SOURCE = ROOT / 'gemian-source/gemian-baseline' / REVISION
PARENTS = {
    'drivers/misc/mediatek/power/mt6797/bq25890.c':
        '01f79a7dba68dd916e7fbc1bd20be448d10ff6706521112a7904cdb86900add6',
    'drivers/i2c/busses/i2c-mtk.c':
        '7624af7e123ab907ee6e649e09b6d3e2a1c06c34e91755145faf4065ce3fa3d8',
    'drivers/i2c/busses/i2c-mtk.h':
        'dfd2ba8e415789f2213319f26c74855a3989141fc057742cc4ba192577e379b1',
}


def run(args, **kwargs):
    env = dict(os.environ, GIT_AUTHOR_DATE='2000-01-01T00:00:00+00:00',
               GIT_COMMITTER_DATE='2000-01-01T00:00:00+00:00')
    return subprocess.check_output(args, text=True, env=env, **kwargs).strip()


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def transform(files):
    driver, controller, header = PARENTS
    s = files[driver]
    s = replace(s, '#include <linux/i2c.h>',
                '#include <linux/i2c.h>\n#include <linux/gemini-reg06-observer.h>')
    marker = 'unsigned int bq25890_read_byte(unsigned char cmd, unsigned char *returnData)'
    branch = s.index('#else', s.index('#ifdef CONFIG_MTK_I2C_EXTENSION'))
    start = s.index(marker, branch)
    end = s.index('unsigned int bq25890_write_byte', start)
    body = s[start:end]
    body = replace(body, marker,
                   'static unsigned int bq25890_read_byte_observed(unsigned char cmd,\n'
                   '\t\tunsigned char *returnData, bool eligible)')
    body = replace(body, '\tint ret, retries = 1;',
                   '\tint ret, retries = 1;\n\tbool observe;')
    body = replace(body, '\tmutex_lock(&bq25890_i2c_access);',
                   '\tmutex_lock(&bq25890_i2c_access);\n'
                   '\tobserve = eligible && cmd == 6 && reg06_observer &&\n'
                   '\t\treg06_state == 1;\n'
                   '\tif (observe) {\n'
                   '\t\treg06_state = 2;\n'
                   '\t\tmemset(&reg06_record, 0, sizeof(reg06_record));\n\t}')
    body = replace(body, '\t\tret = i2c_transfer(new_client->adapter, msgs, xfers);',
                   '\t\tif (observe)\n'
                   '\t\t\tret = gemini_reg06_transfer(new_client->adapter, msgs,\n'
                   '\t\t\t\t\t\t    &reg06_record);\n'
                   '\t\telse\n'
                   '\t\t\tret = i2c_transfer(new_client->adapter, msgs, xfers);')
    body = replace(body, '\tmutex_unlock(&bq25890_i2c_access);',
                   '\tif (observe) {\n'
                   '\t\treg06_record.result = ret;\n'
                   '\t\tif (gemini_reg06_valid(&reg06_record))\n'
                   '\t\t\treg06_record.value = *returnData;\n'
                   '\t\treg06_state = 3;\n\t}\n'
                   '\tmutex_unlock(&bq25890_i2c_access);')
    body += ('unsigned int bq25890_read_byte(unsigned char cmd, unsigned char *data)\n'
             '{\n\treturn bq25890_read_byte_observed(cmd, data, false);\n}\n\n')
    snippet = (HERE / 'driver.inc').read_text()
    s = s[:start] + snippet + '\n' + body + s[end:]
    s = replace(s, '\tmutex_lock(&bq25890_access_mutex);\n'
                '\tret = bq25890_read_byte(RegNum, &bq25890_reg);',
                '\tmutex_lock(&bq25890_access_mutex);\n'
                '\tret = bq25890_read_byte_observed(RegNum, &bq25890_reg,\n'
                '\t\t\tRegNum == 6 && MASK == 0x3f && SHIFT == 2);')
    s = replace(s, '\tret_device_file = device_create_file(&(dev->dev), &dev_attr_bq25890_access);',
                '\tret_device_file = device_create_file(&(dev->dev), &dev_attr_bq25890_access);\n'
                '\tif (reg06_observer &&\n'
                '\t    device_create_file(&dev->dev, &dev_attr_reg06_observe))\n'
                '\t\tdev_warn(&dev->dev, "REG06 observer unavailable\\n");')
    files[driver] = s
    s = files[header]
    s = replace(s, 'struct mt_i2c {', '#include <linux/gemini-reg06-observer.h>\n\nstruct mt_i2c {')
    s = replace(s, '\tstruct mt_i2c_ext ext_data;',
                '\tstruct gemini_reg06_record *reg06_pending;\n'
                '\tstruct gemini_reg06_record *reg06_active;\n'
                '\tstruct i2c_msg *reg06_request;\n\tstruct mt_i2c_ext ext_data;')
    files[header] = s
    s = files[controller]
    s = replace(s, '\tif (i2c->ext_data.isEnable && i2c->ext_data.timing)\n'
                '\t\tspeed_hz = i2c->ext_data.timing;\n'
                '\telse\n\t\tspeed_hz = i2c->speed_hz;\n#if',
                '\tif (i2c->reg06_active) {\n'
                '\t\ti2c->reg06_active->transfers++;\n'
                '\t\ti2c->reg06_active->fifo_path = !isDMA;\n'
                '\t\ti2c->reg06_active->wrrd = i2c->op == I2C_MASTER_WRRD;\n\t}\n'
                '\tif (i2c->ext_data.isEnable && i2c->ext_data.timing)\n'
                '\t\tspeed_hz = i2c->ext_data.timing;\n'
                '\telse\n\t\tspeed_hz = i2c->speed_hz;\n#if')
    s = replace(s, '\ttmo = wait_event_timeout(i2c->wait, i2c->trans_stop, tmo);',
                '\ttmo = wait_event_timeout(i2c->wait, i2c->trans_stop, tmo);\n'
                '\tif (i2c->reg06_active)\n'
                '\t\ti2c->reg06_active->irq = i2c->irq_stat;')
    s = replace(s, '\t\tdata_size = (i2c_readw(i2c, OFFSET_FIFO_STAT) >> 4) & 0x000F;',
                '\t\tdata_size = (i2c_readw(i2c, OFFSET_FIFO_STAT) >> 4) & 0x000F;\n'
                '\t\tif (i2c->reg06_active) {\n'
                '\t\t\ti2c->reg06_active->fifo_seen = true;\n'
                '\t\t\ti2c->reg06_active->fifo_count = data_size;\n\t\t}')
    start = s.index('static int mt_i2c_transfer(struct i2c_adapter *adap')
    end = s.index('static void mt_i2c_parse_extension', start)
    body = s[start:end]
    body = replace(body, '\tmutex_lock(&i2c->i2c_mutex);',
                   '\tmutex_lock(&i2c->i2c_mutex);\n'
                   '\tif (i2c->reg06_pending && i2c->reg06_request == msgs) {\n'
                   '\t\ti2c->reg06_pending->master_calls++;\n'
                   '\t\tif (i2c->id == 0 && !i2c->appm && !i2c->gpupm &&\n'
                   '\t\t    !i2c->have_pmic && !i2c->have_dcm &&\n'
                   '\t\t    !i2c->use_push_pull && !i2c->buffermode &&\n'
                   '\t\t    !i2c->is_hw_trig && !i2c->ext_data.isEnable &&\n'
                   '\t\t    i2c->speed_hz == 400000 && i2c->clk_src_div == 10 &&\n'
                   '\t\t    adap->timeout == 2 * HZ && adap->retries == 1 &&\n'
                   '\t\t    i2c->dev_comp && i2c->dev_comp->dma_support == 1) {\n'
                   '\t\t\ti2c->reg06_active = i2c->reg06_pending;\n'
                   '\t\t\ti2c->reg06_active->controller_ok = true;\n'
                   '\t\t}\n\t}')
    body = replace(body, '\tmutex_unlock(&i2c->i2c_mutex);',
                   '\ti2c->reg06_active = NULL;\n'
                   '\tmutex_unlock(&i2c->i2c_mutex);')
    s = s[:start] + body + s[end:]
    start = s.index('static int mt_i2c_probe(')
    s = s[:start] + (HERE / 'controller.inc').read_text() + '\n' + s[start:]
    files[controller] = s
    files['include/linux/gemini-reg06-observer.h'] = (HERE / 'gemini-reg06-observer.h').read_text()
    return files


def main():
    assert platform.system() == 'Linux'
    assert run(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD']) == REVISION
    assert not run(['git', '-C', str(SOURCE), 'status', '--porcelain'])
    assert shutil.disk_usage(ROOT).free > 1024 ** 3
    files = {}
    for name, expected in PARENTS.items():
        raw = (SOURCE / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, name
        files[name] = raw.decode()
    parent = ROOT / 'gemian-artifacts/reg06-patch-review'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prepare-', dir=parent) as tmp:
        work = Path(tmp)
        run(['git', 'init', '-q', str(work)])
        def write(items):
            for name, text in items.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
        write(files)
        identity = ['-c', 'user.name=Gemini diagnostic experiment',
                    '-c', 'user.email=diagnostic@example.invalid',
                    '-c', 'commit.gpgsign=false']
        run(['git', '-C', str(work), 'add', '.'])
        run(['git', '-C', str(work)] + identity + ['commit', '-q', '-m', 'Pinned parent files'])
        write(transform(dict(files)))
        run(['git', '-C', str(work), 'diff', '--check'])
        run(['git', '-C', str(work), 'add', '.'])
        run(['git', '-C', str(work)] + identity + ['commit', '-q', '-m',
            'diagnostic: observe one existing Gemian REG06 read', '-m',
            'Default-off internal experiment; synthetic non-certifying author. '
            'No added charger transaction or changed policy/transfer result.'])
        patch = subprocess.check_output(['git', '-C', str(work), 'format-patch', '-1', '--stdout'])
        sha = hashlib.sha256(patch).hexdigest()
        target = parent / (sha + '.patch')
        target.write_bytes(patch)
        print(json.dumps({'patch': str(target), 'sha256': sha,
                          'source_revision': REVISION, 'parents': PARENTS}))


if __name__ == '__main__':
    main()
