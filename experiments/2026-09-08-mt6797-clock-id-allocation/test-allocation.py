#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check actual probe allocation statements against MT6797 binding IDs."""
import argparse
import pathlib
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    args = parser.parse_args()
    root = args.source
    clocks = root / 'drivers/clk/mediatek'
    text = (clocks / 'clk-mtk.c').read_text()
    allocation = text.split('/* Calculate how many clk_hw_onecell_data entries to allocate */', 1)[1]
    allocation = allocation.split('clk_data = mtk_alloc_clk_data(num_clks);', 1)[0]
    header = (root / 'include/dt-bindings/clock/mt6797-clk.h').read_text()
    ids = {name: int(value) for name, value in
           re.findall(r'#define\s+(CLK_\w+)\s+(\d+)\b', header)}
    cases = []
    for name in ('img', 'mm', 'vdec', 'venc'):
        source = (clocks / f'clk-mt6797-{name}.c').read_text()
        array = source.split(f'{name}_clks[] = {{', 1)[1].split('\n};', 1)[0]
        gate_ids = [ids[key] for key in re.findall(r'GATE_\w+\((CLK_\w+),', array)]
        assert gate_ids and len(gate_ids) == len(set(gate_ids))
        desc = source.split(f'{name}_desc = {{', 1)[1].split('\n};', 1)[0]
        explicit = re.search(r'\.num_clk_ids\s*=\s*(CLK_\w+)', desc)
        slots = ids[explicit.group(1)] if explicit else 0
        cases.append((name, len(gate_ids), slots, max(gate_ids) + 1))
    c = '''#include <stdio.h>
struct mtk_clk_desc {
    unsigned int num_clk_ids;
    unsigned int num_clks, num_composite_clks, num_fixed_clks;
    unsigned int num_factor_clks, num_mux_clks, num_divider_clks;
};
static int allocate(const struct mtk_clk_desc *mcd)
{
    int num_clks;
''' + allocation + '''
    return num_clks;
}
int main(void)
{
    int failed = 0;
    struct mtk_clk_desc dense = { .num_clks = 4 };
    struct mtk_clk_desc mixed = { .num_clks = 2, .num_composite_clks = 3,
        .num_fixed_clks = 4, .num_factor_clks = 5, .num_mux_clks = 6,
        .num_divider_clks = 7 };
    failed += allocate(&dense) != 4;
    failed += allocate(&mixed) != 27;
'''
    for name, gates, slots, required in cases:
        c += f'''    {{
        struct mtk_clk_desc desc = {{ .num_clks = {gates}, .num_clk_ids = {slots} }};
        int allocated = allocate(&desc);
        printf("{name}: gates={gates} allocated=%d required={required}\\n", allocated);
        failed += allocated != {required};
    }}
'''
    c += '    return failed ? 1 : 0;\n}\n'
    with tempfile.TemporaryDirectory(prefix='mt6797-clock-ids-') as temp:
        source = pathlib.Path(temp) / 'allocation.c'
        binary = pathlib.Path(temp) / 'allocation'
        source.write_text(c)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(source), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=False)
        if result.returncode:
            raise SystemExit('FAIL: provider slot count does not cover the binding IDs')
    print('PASS: four MT6797 providers and two unchanged default-allocation cases')


if __name__ == '__main__':
    main()
