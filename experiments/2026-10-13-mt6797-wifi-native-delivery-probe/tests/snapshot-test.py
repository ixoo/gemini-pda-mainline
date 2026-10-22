#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual set-policy and safety wiring checks, without device access."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
a = p.parse_args()
d = a.source / 'drivers/net/wireless/mediatek/mt6797'
with tempfile.TemporaryDirectory(prefix='snapshot-policy-') as tmp:
    output = Path(tmp) / 'test'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(d),
                    str(Path(__file__).with_name('snapshot-sets-test.c')),
                    '-o', str(output)], check=True)
    subprocess.run([str(output)], check=True)
core = (d / 'snapshot.c').read_text()
mac = (d / 'mac.c').read_text()
assert 'static bool snapshot_enable;' in mac
assert 'module_param(snapshot_enable, bool, 0444)' in mac
assert 'if (!enabled || IS_ERR_OR_NULL(parent) || !ops' in core
assert 'MT6797_SNAPSHOT_OPS(mt6797_snapshot_data_ops, mt6797_snapshot_read, NULL)' in core
assert 'capable(CAP_SYS_RAWIO)' in core
assert 'kfree_sensitive' in core
reader = core.split('static ssize_t mt6797_snapshot_read(', 1)[1].split('#define MT6797_SNAPSHOT_OPS', 1)[0]
assert 'ops->step' not in reader and 'wait_for_completion_interruptible_timeout' in reader
assert 'r->deadline - now' in reader and 'if (!size)' in reader
tick = core.split('int mt6797_snapshot_tick(', 1)[1].split('void mt6797_snapshot_fail(', 1)[0]
assert tick.index('mutex_unlock(&s->lock);\n\t/* Never hold') < tick.index('ops->step(')
assert 'if (!r->terminal)' in tick
assert 'gate = gate' in core and 's->poisoned = false' not in core
assert 'f->result = s->last;' in core and 'kref_get(&f->result->ref)' in core
shutdown = mac.split('static void mt6797_mac_snapshot_shutdown(', 1)[1].split('#endif', 1)[0]
assert shutdown.index('mt6797_snapshot_disable(') < shutdown.index('mac->join_running = false') < shutdown.index('cancel_delayed_work_sync(')
work = mac.split('static void mt6797_mac_join_work(', 1)[1].split('static ', 1)[0]
assert work.index('for (n = 0; n < 8; n++)') < work.index('mt6797_snapshot_tick(mac->snapshot)')
assert 'snapshot_delay = mt6797_snapshot_active' in work
assert 'mt6797_hif_' not in core
print('actual set-policy and safety wiring checks=pass; device_action=none')
