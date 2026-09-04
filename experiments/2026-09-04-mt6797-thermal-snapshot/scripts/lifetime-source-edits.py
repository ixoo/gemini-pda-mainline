#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Drain V4 thermal readers before transaction close, including probe failure."""
from pathlib import Path
import hashlib
import sys

p = Path(sys.argv[1]) / 'drivers/thermal/mediatek/auxadc_thermal.c'
s = p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest() == 'c51a7a23b8e32f1e93304f9fd30d1d21fa212ca04162fbca6f68fc93e1e12d4b'


def replace(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)


replace('\tbool is_v4;\n\tbool traced;', '\tbool is_v4;\n\tbool readers_group = false;\n\tbool traced;')
replace('''\tif (traced) {
\t\tret = mt6797_thermal_probe_trace(
\t\t\tGEMINI_MT6797_THERMAL_ZONE_REGISTER,''', '''\t/* Drain all public readers before closing the V4 transaction. */
\tif (is_v4) {
\t\tif (!devres_open_group(&pdev->dev, mt, GFP_KERNEL)) {
\t\t\tret = -ENOMEM;
\t\t\tgoto fail_zone;
\t\t}
\t\treaders_group = true;
\t}

\tif (traced) {
\t\tret = mt6797_thermal_probe_trace(
\t\t\tGEMINI_MT6797_THERMAL_ZONE_REGISTER,''')
replace('''\t\tif (ret) {
\t\t\tmtk_thermal_transaction_close(mt, ops, &mt->transaction);
\t\t\treturn ret;
\t\t}
\t}

#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)''', '''\t\tif (ret)
\t\t\tgoto fail_zone;
\t}

#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)''')
replace('''#endif
\treturn 0;

fail_zone:''', '''#endif
\tif (readers_group)
\t\tdevres_close_group(&pdev->dev, mt);
\treturn 0;

fail_zone:''')
replace('''fail_zone:
\tif (traced)''', '''fail_zone:
\tif (readers_group)
\t\tdevres_release_group(&pdev->dev, mt);
\tif (traced)''')
replace('''\tif (mt && mt->conf->version == MTK_THERMAL_V4)
\t\tmtk_thermal_transaction_close(mt, &mt6797_thermal_transaction_ops,
\t\t\t\t\t      &mt->transaction);''', '''\tif (mt && mt->conf->version == MTK_THERMAL_V4) {
\t\t/* Removal waits for active sysfs callbacks before clock shutdown. */
\t\tdevres_release_group(&pdev->dev, mt);
\t\tmtk_thermal_transaction_close(mt, &mt6797_thermal_transaction_ops,
\t\t\t\t\t      &mt->transaction);
\t}''')
p.write_text(s)
