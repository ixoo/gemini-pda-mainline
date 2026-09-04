#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run actual interface, owner and scan bodies with pthread/IO/sysfs adapters."""
import argparse
import hashlib
from pathlib import Path
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
    return body if body.startswith('static') else 'static int\n' + body


names = ['mtk_thermal_temp_is_valid', 'mtk_thermal_bank_temperature_capture',
         'mtk_read_temp_scan', 'mtk_read_temp', 'mt6797_observer_time_ns',
         'mt6797_observer_scan']
actual = '\n'.join(function(name) for name in names)
actual += '''
static const struct mt6797_thermal_observer_ops mt6797_observer_ops = {
    .time_ns = mt6797_observer_time_ns, .scan = mt6797_observer_scan,
};
'''
actual += function('mt6797_temperature_snapshot_show') + '\n'
actual += function('mt6797_temperature_snapshot_status_show')
for name in ['mt6797_temperature_snapshot', 'mt6797_temperature_snapshot_status']:
    assert f'DEVICE_ATTR_ADMIN_RO({name});' in text
fixture = Path(__file__).resolve().parent.parent / 'source/observer-interface-fixture.c'
program = fixture.read_text().replace('/* ACTUAL_FUNCTIONS */', actual)
managed = Path('/workspace/gemini-pda/thermal-observer-work')
managed.mkdir(exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
with tempfile.TemporaryDirectory(prefix='interface-oracle.', dir=managed) as work:
    root = Path(work)
    (root / 'linux').mkdir()
    shims = {
        'errno.h': '#include <asm-generic/errno.h>\n',
        'limits.h': '#include <limits.h>\n',
        'types.h': '#include <stdbool.h>\ntypedef unsigned int u32;\ntypedef unsigned long long u64;\n',
        'mutex.h': '''#include <pthread.h>
#include <assert.h>
struct mutex { pthread_mutex_t native; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->native, NULL)); }
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->native)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->native)); }
''',
    }
    for name, value in shims.items():
        (root / 'linux' / name).write_text(value)
    headers = {}
    for name in ['mt6797_thermal_observer.h', 'mt6797_thermal_snapshot.h']:
        headers[name] = (source / 'drivers/thermal/mediatek' / name).read_text()
        (root / name).write_text(headers[name])
    command = ['cc', '-std=gnu11', '-pthread', '-Wall', '-Wextra', '-Werror',
               '-Wno-unused-parameter', '-I', str(root), str(root / 'fixture.c'),
               '-o', str(root / 'fixture')]
    (root / 'fixture.c').write_text(program)
    subprocess.run(command, check=True)
    subprocess.run([str(root / 'fixture')], check=True, timeout=15)
    mutations = {
        'negative-show-error': (program.replace('/* Return a record even on failure:',
                                               'if (ret) return ret;\n\t/* Return a record even on failure:'), False),
        'status-spends-budget': (program.replace('attempts = mt->observer.budget.attempts;',
                                                 'attempts = ++mt->observer.budget.attempts;'), False),
        'four-attempt-budget': (program, True),
    }
    for name, (mutant, change_header) in mutations.items():
        if change_header:
            original = headers['mt6797_thermal_snapshot.h']
            assert '#define MT6797_THERMAL_SNAPSHOT_ATTEMPTS 3U' in original
            (root / 'mt6797_thermal_snapshot.h').write_text(original.replace(
                '#define MT6797_THERMAL_SNAPSHOT_ATTEMPTS 3U',
                '#define MT6797_THERMAL_SNAPSHOT_ATTEMPTS 4U'))
        else:
            assert mutant != program, name
        (root / 'fixture.c').write_text(mutant)
        subprocess.run(command, check=True)
        result = subprocess.run([str(root / 'fixture')], capture_output=True, timeout=15)
        assert result.returncode != 0, name
    print('interface_mutations_rejected=3')
print('driver_sha256=' + hashlib.sha256(text.encode()).hexdigest())
