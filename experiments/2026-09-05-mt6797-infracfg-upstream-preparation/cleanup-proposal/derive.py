#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure, fail-closed derivation of the separate common-helper cleanup fix."""
import hashlib

SOURCE_PATH = 'drivers/clk/mediatek/clk-mtk.c'
UPSTREAM = '4d7d9486c04d917265f64c55bd23b2cc4fe7749c'
CLOCK_NEXT = '91b1b8d437abe0cd83210d8f257b785a63047aa9'
SOURCE_SHA256 = 'e8a89dffaffedfce01489b0887fb425d64649d6fb841157bbcea5aac0fc93e59'
SOURCE_BYTES = 16200
SOURCE_URL = f'https://raw.githubusercontent.com/torvalds/linux/{UPSTREAM}/{SOURCE_PATH}'
OLD = '''\tif (mcd->rst_desc) {
\t\tr = mtk_register_reset_controller_with_dev(&pdev->dev,
\t\t\t\t\t\t\t   mcd->rst_desc);
\t\tif (r)
\t\t\tgoto unregister_clks;
\t}
'''
NEW = OLD.replace('goto unregister_clks;', 'goto unregister_provider;')
LABEL = '''\treturn r;

unregister_clks:
'''
NEW_LABEL = '''\treturn r;

unregister_provider:
\tof_clk_del_provider(node);
unregister_clks:
'''


def derive(raw):
    if len(raw) != SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('wrong complete clk-mtk.c input')
    text = raw.decode('utf-8')
    if text.count(OLD) != 1 or text.count(LABEL) != 1:
        raise ValueError('non-unique cleanup insertion boundary')
    return text.replace(OLD, NEW).replace(LABEL, NEW_LABEL).encode('utf-8')


def functions(raw):
    """Retain complete upstream probe/remove bodies; never hand-copy their logic."""
    text = raw.decode('utf-8')
    start = text.index('static int __mtk_clk_simple_probe(')
    end = text.index('int mtk_clk_pdev_probe(', start)
    return text[start:end]
