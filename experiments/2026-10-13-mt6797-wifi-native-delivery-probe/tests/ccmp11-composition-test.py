#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the actual C32 configuration oracle for the real group-PN package."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
body = (HERE / 'ccmp-composition-test.py').read_text().replace(
    "'build-ccmp-candidate.py'", "'build-ccmp-candidate-11.py'")
needle = "    parent + b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\\n',"
assert body.count(needle) == 1
body = body.replace(needle, needle + "\n    parent + b'CONFIG_MT6797_CCMP_MASK_CONTROL=y\\n',"
                    + "\n    parent + b'CONFIG_MT6797_CCMP_GROUP_PN_OBSERVE=y\\n',")
body = body.replace("b'CONFIG_MT6797_CCMP_STABLE_EPOCH=y', b'mac.native_delivery_diag=0'",
                    "b'CONFIG_MT6797_CCMP_STABLE_EPOCH=y', b'CONFIG_MT6797_CCMP_MASK_CONTROL=y', "
                    "b'CONFIG_MT6797_CCMP_GROUP_PN_OBSERVE=y', b'mac.native_delivery_diag=0'")
body = body.replace('5 parent refusals/4 child differences', '7 parent refusals/6 child differences')
exec(compile(body, 'reused-group-pn-config-oracle', 'exec'),
     {'__file__': str(HERE / 'ccmp-composition-test.py')})
