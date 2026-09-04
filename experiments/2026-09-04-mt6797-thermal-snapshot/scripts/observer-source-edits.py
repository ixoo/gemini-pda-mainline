#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exact-anchor integration; never run against the managed source tree."""
from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1])
source = Path(__file__).resolve().parent.parent / 'source'
p = root / 'drivers/thermal/mediatek/auxadc_thermal.c'
s = original = p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest() == '143e0458d5dd4489a8843a250ee58ebf2bda4581e48e029a35efad6ffce575cd'
replacements = []


def replace(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
    replacements.append((old, new))


replace('#include "auxadc_thermal_internal.h"', '#include <linux/ktime.h>\n\n#include "mt6797_thermal_observer.h"\n#include "auxadc_thermal_internal.h"')
replace('\t/* Calibration values */', '''#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)
\tstruct mt6797_thermal_observer observer;
#endif
\t/* Calibration values */''')
replace('mtk_thermal_bank_temperature - get the temperature of a bank\n * @bank:\tThe bank', 'mtk_thermal_bank_temperature_capture - get the temperature of a bank\n * @bank:\tThe bank\n * @snapshot:\tOptional collector for the existing converted samples')
replace('static int mtk_thermal_bank_temperature(struct mtk_thermal_bank *bank)', '''static int
mtk_thermal_bank_temperature_capture(struct mtk_thermal_bank *bank,
\t\t\t\t     struct mt6797_thermal_snapshot *snapshot)''')
replace('\t\t\tmt, conf->bank_data[bank->id].sensors[i], raw);', '''\t\t\tmt, conf->bank_data[bank->id].sensors[i], raw);

\t\tif (snapshot)
\t\t\tmt6797_thermal_snapshot_append(snapshot, bank->id,
\t\t\t\tconf->bank_data[bank->id].sensors[i], temp,
\t\t\t\tmtk_thermal_temp_is_valid(temp));''')
replace('static void mt6797_eem_unpack_anchors', '''static int mtk_thermal_bank_temperature(struct mtk_thermal_bank *bank)
{
\treturn mtk_thermal_bank_temperature_capture(bank, NULL);
}

static void mt6797_eem_unpack_anchors''')
replace('''static int mtk_read_temp(struct thermal_zone_device *tz, int *temperature)
{
\tstruct mtk_thermal *mt = thermal_zone_device_priv(tz);''', '''static int mtk_read_temp_scan(struct mtk_thermal *mt, int *temperature,
\t\t\t      struct mt6797_thermal_snapshot *snapshot)
{''')
replace('tempmax = max(tempmax, mtk_thermal_bank_temperature(bank));', 'tempmax = max(tempmax,\n\t\t\t      mtk_thermal_bank_temperature_capture(bank, snapshot));')
replace('static const struct thermal_zone_device_ops mtk_thermal_ops', '''static int mtk_read_temp(struct thermal_zone_device *tz, int *temperature)
{
\treturn mtk_read_temp_scan(thermal_zone_device_priv(tz), temperature, NULL);
}

''' + source.joinpath('observer-interface.c').read_text() + '\n' + 'static const struct thermal_zone_device_ops mtk_thermal_ops')
replace('\tmutex_init(&mt->lock);', '''\tmutex_init(&mt->lock);
#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)
\tmt6797_thermal_observer_init(&mt->observer);
#endif''')
replace('\n\treturn 0;\n\nfail_zone:', '''
#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)
\tif (mt->conf == &mt6797_thermal_data) {
\t\tret = devm_device_add_groups(&pdev->dev, mt6797_observer_groups);
\t\tif (ret)
\t\t\tdev_warn(&pdev->dev, "thermal observer unavailable: %d\\n", ret);
\t}
#endif
\treturn 0;

fail_zone:''')
# Integration must add no register accessor, bank locking or converter calls.
for token in ('readl(', 'writel(', 'mtk_thermal_get_bank(',
              'mtk_thermal_put_bank(', 'mt->raw_to_mcelsius('):
    assert original.count(token) == s.count(token), token
# Reverse all declared insertions to prove no undeclared production drift.
restored = s
for old, new in reversed(replacements):
    assert restored.count(new) == 1
    restored = restored.replace(new, old)
assert restored == original
p.write_text(s)
(root / 'drivers/thermal/mediatek/mt6797_thermal_observer.h').write_bytes(
    (source / 'mt6797_thermal_observer.h').read_bytes())
p = root / 'drivers/thermal/mediatek/Kconfig'
s = p.read_text()
anchor = 'config MTK_SOC_THERMAL_KUNIT_TEST\n'
assert s.count(anchor) == 1
s = s.replace(anchor, '''config MTK_SOC_THERMAL_OBSERVER
\tbool "Bounded MT6797 thermal scan observer"
\tdepends on MTK_SOC_THERMAL
\tdefault n
\thelp
\t  Expose three root-only temperature snapshots on MT6797 using
\t  the existing bank scan. Normal thermal polling spends no observer
\t  attempts. Export converted values and timing, never calibration.
\t  This diagnostic supplies no thermal protection or control policy.

''' + anchor)
p.write_text(s)
print('integration: exact parent; unchanged MMIO/lock/conversion call inventory; reversible edits PASS')
