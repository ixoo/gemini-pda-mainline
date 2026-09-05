#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive review-only upstream edits from exact inputs, on Buildbox only."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLK = 'drivers/clk/mediatek/'
BINDING = 'include/dt-bindings/reset/mt6797-resets.h'
SCHEMA = 'Documentation/devicetree/bindings/clock/mediatek,infracfg.yaml'
DTS = 'arch/arm64/boot/dts/mediatek/mt6797.dtsi'
PHASES = ('bounds', 'bounds-test', 'binding', 'provider', 'provider-test', 'dts')

BOUNDS = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DRV_CLK_MTK_RESET_INTERNAL_H
#define __DRV_CLK_MTK_RESET_INTERNAL_H

#include <linux/bitops.h>
#include <linux/errno.h>

#include "reset.h"

static inline int
mtk_reset_xlate_index(const struct mtk_clk_rst_desc *desc, unsigned int index)
{
	if (!desc->rst_idx_map || index >= desc->rst_idx_map_nr)
		return -EINVAL;

	return desc->rst_idx_map[index];
}

static inline int
mtk_reset_set_clr_reg(const struct mtk_clk_rst_desc *desc,
		      unsigned long id, bool deassert,
		      unsigned int *reg, unsigned int *mask)
{
	unsigned long bank = id / RST_NR_PER_BANK;

	if (!desc->rst_bank_ofs || bank >= desc->rst_bank_nr)
		return -EINVAL;

	*reg = desc->rst_bank_ofs[bank] + (deassert ? 0x4 : 0);
	*mask = BIT(id % RST_NR_PER_BANK);

	return 0;
}

#endif /* __DRV_CLK_MTK_RESET_INTERNAL_H */
'''

HEADER = '''/* SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause) */
#ifndef _DT_BINDINGS_RESET_MT6797_H
#define _DT_BINDINGS_RESET_MT6797_H

#define MT6797_INFRA_THERM_CTRL_RST	0
#define MT6797_INFRA_PMIC_WRAP_RST	1

#endif /* _DT_BINDINGS_RESET_MT6797_H */
'''

DESCRIPTOR = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DRV_CLK_MTK_MT6797_RESET_H
#define __DRV_CLK_MTK_MT6797_RESET_H

#include <dt-bindings/reset/mt6797-resets.h>
#include <linux/kernel.h>

#include "reset.h"

static u16 infra_rst_ofs[] = {
	INFRA_RST0_SET_OFFSET,
	INFRA_RST2_SET_OFFSET,
};

static u16 infra_rst_idx_map[] = {
	[MT6797_INFRA_THERM_CTRL_RST] = 0 * RST_NR_PER_BANK,
	[MT6797_INFRA_PMIC_WRAP_RST] = 1 * RST_NR_PER_BANK,
};

static const struct mtk_clk_rst_desc infra_rst_desc = {
	.version = MTK_RST_SET_CLR,
	.rst_bank_ofs = infra_rst_ofs,
	.rst_bank_nr = ARRAY_SIZE(infra_rst_ofs),
	.rst_idx_map = infra_rst_idx_map,
	.rst_idx_map_nr = ARRAY_SIZE(infra_rst_idx_map),
};

#endif /* __DRV_CLK_MTK_MT6797_RESET_H */
'''

GENERIC_TEST = '''// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/limits.h>
#include <linux/module.h>

#include "reset-internal.h"

static u16 test_offsets[] = { 0x120, 0x140 };
static u16 test_map[] = { 0, 32, 64 };

static const struct mtk_clk_rst_desc test_desc = {
	.rst_bank_ofs = test_offsets,
	.rst_bank_nr = ARRAY_SIZE(test_offsets),
	.rst_idx_map = test_map,
	.rst_idx_map_nr = ARRAY_SIZE(test_map),
};

static void mtk_reset_map_bounds(struct kunit *test)
{
	struct mtk_clk_rst_desc desc = test_desc;

	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 0), 0);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 1), 32);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 3), -EINVAL);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, UINT_MAX), -EINVAL);
	desc.rst_idx_map = NULL;
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 0), -EINVAL);
}

static void mtk_reset_register_pairs(struct kunit *test)
{
	unsigned int reg = 0, mask = 0;

	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&test_desc, 0, false,
						    &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, 0x120U);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&test_desc, 63, true,
						    &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, 0x144U);
	KUNIT_EXPECT_EQ(test, mask, BIT(31));
}

static void expect_no_address(struct kunit *test,
			      const struct mtk_clk_rst_desc *desc,
			      unsigned long id)
{
	unsigned int reg = 0xfeed, mask = 0xbeef;

	KUNIT_EXPECT_EQ(test, mtk_reset_set_clr_reg(desc, id, false,
						    &reg, &mask), -EINVAL);
	KUNIT_EXPECT_EQ(test, reg, 0xfeedU);
	KUNIT_EXPECT_EQ(test, mask, 0xbeefU);
}

static void mtk_reset_invalid_bank(struct kunit *test)
{
	int id = mtk_reset_xlate_index(&test_desc, 2);

	KUNIT_ASSERT_EQ(test, id, 64);
	expect_no_address(test, &test_desc, id);
	expect_no_address(test, &test_desc, ULONG_MAX);
	/* Also catches a bank narrowed to zero on a 64-bit build. */
	if (BITS_PER_LONG > 32)
		expect_no_address(test, &test_desc, (unsigned long)(1ULL << 37));
}

static void mtk_reset_missing_banks(struct kunit *test)
{
	struct mtk_clk_rst_desc desc = test_desc;

	desc.rst_bank_nr = 0;
	expect_no_address(test, &desc, 0);
	desc = test_desc;
	desc.rst_bank_ofs = NULL;
	expect_no_address(test, &desc, 0);
}

static struct kunit_case mtk_reset_cases[] = {
	KUNIT_CASE(mtk_reset_map_bounds),
	KUNIT_CASE(mtk_reset_register_pairs),
	KUNIT_CASE(mtk_reset_invalid_bank),
	KUNIT_CASE(mtk_reset_missing_banks),
	{}
};

static struct kunit_suite mtk_reset_suite = {
	.name = "mtk-reset-bounds",
	.test_cases = mtk_reset_cases,
};

kunit_test_suite(mtk_reset_suite);

MODULE_LICENSE("GPL");
'''

SOC_TEST = '''// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/module.h>

#include "clk-mt6797-reset.h"
#include "reset-internal.h"

static void mt6797_reset_descriptor(struct kunit *test)
{
	KUNIT_EXPECT_EQ(test, infra_rst_desc.version, MTK_RST_SET_CLR);
	KUNIT_EXPECT_EQ(test, infra_rst_desc.rst_bank_nr, 2U);
	KUNIT_EXPECT_EQ(test, infra_rst_desc.rst_idx_map_nr, 2U);
	KUNIT_EXPECT_EQ(test, infra_rst_ofs[0], (u16)0x120);
	KUNIT_EXPECT_EQ(test, infra_rst_ofs[1], (u16)0x140);
}

static void expect_pair(struct kunit *test, unsigned int index,
			unsigned int expected_reg)
{
	unsigned int reg = 0, mask = 0;
	int id = mtk_reset_xlate_index(&infra_rst_desc, index);

	KUNIT_ASSERT_GE(test, id, 0);
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&infra_rst_desc, id, false,
						    &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, expected_reg);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&infra_rst_desc, id, true,
						    &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, expected_reg + 4);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
}

static void mt6797_reset_thermal(struct kunit *test)
{
	expect_pair(test, MT6797_INFRA_THERM_CTRL_RST, 0x120);
}

static void mt6797_reset_pwrap(struct kunit *test)
{
	expect_pair(test, MT6797_INFRA_PMIC_WRAP_RST, 0x140);
}

static void mt6797_reset_unexposed(struct kunit *test)
{
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 2), -EINVAL);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 64), -EINVAL);
}

static struct kunit_case mt6797_reset_cases[] = {
	KUNIT_CASE(mt6797_reset_descriptor),
	KUNIT_CASE(mt6797_reset_thermal),
	KUNIT_CASE(mt6797_reset_pwrap),
	KUNIT_CASE(mt6797_reset_unexposed),
	{}
};

static struct kunit_suite mt6797_reset_suite = {
	.name = "mt6797-infracfg-reset",
	.test_cases = mt6797_reset_cases,
};

kunit_test_suite(mt6797_reset_suite);

MODULE_LICENSE("GPL");
'''


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source anchor absent or ambiguous')
    return text.replace(old, new, 1)


def phase_edits(files, phase):
    """Pure transformation; caller pins and validates the complete input inventory."""
    out = dict(files)

    def change(path, old, new):
        out[path] = replace(out[path], old, new)

    def create(path, content):
        if path in out:
            raise ValueError('new source path already exists: ' + path)
        out[path] = content

    if phase == 'bounds':
        create(CLK + 'reset-internal.h', BOUNDS)
        change(CLK + 'reset.c', '#include "reset.h"', '#include "reset-internal.h"')
        change(CLK + 'reset.c', '''	unsigned int deassert_ofs = deassert ? 0x4 : 0;

	return regmap_write(data->regmap,
			    data->desc->rst_bank_ofs[id / RST_NR_PER_BANK] +
			    deassert_ofs,
			    BIT(id % RST_NR_PER_BANK));''', '''	unsigned int reg, mask;
	int ret;

	ret = mtk_reset_set_clr_reg(data->desc, id, deassert, &reg, &mask);
	if (ret)
		return ret;

	return regmap_write(data->regmap, reg, mask);''')
        change(CLK + 'reset.c', '''	if (reset_spec->args[0] >= rcdev->nr_resets ||
	    reset_spec->args[0] >= data->desc->rst_idx_map_nr)''',
               '\tif (reset_spec->args[0] >= rcdev->nr_resets)')
        change(CLK + 'reset.c', '\treturn data->desc->rst_idx_map[reset_spec->args[0]];',
               '\treturn mtk_reset_xlate_index(data->desc, reset_spec->args[0]);')
    elif phase == 'bounds-test':
        create(CLK + 'reset-test.c', GENERIC_TEST)
        change(CLK + 'Kconfig', 'config COMMON_CLK_MEDIATEK_FHCTL\n', '''config COMMON_CLK_MEDIATEK_RESET_KUNIT_TEST
	tristate "Test MediaTek reset bounds" if !KUNIT_ALL_TESTS
	depends on KUNIT
	default KUNIT_ALL_TESTS
	help
	  Test reset index and SET/CLEAR register translation without
	  registering a reset controller or accessing hardware.

config COMMON_CLK_MEDIATEK_FHCTL
''')
        change(CLK + 'Makefile', '\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_FHCTL)',
               '\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_RESET_KUNIT_TEST) += reset-test.o\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_FHCTL)')
    elif phase == 'binding':
        create(BINDING, HEADER)
        change(SCHEMA, '          - mediatek,mt6795-infracfg\n          - mediatek,mt7622-infracfg',
               '          - mediatek,mt6795-infracfg\n          - mediatek,mt6797-infracfg\n          - mediatek,mt7622-infracfg')
    elif phase == 'provider':
        create(CLK + 'clk-mt6797-reset.h', DESCRIPTOR)
        change(CLK + 'clk-mt6797.c', '#include "clk-pll.h"',
               '#include "clk-pll.h"\n#include "clk-mt6797-reset.h"')
        change(CLK + 'clk-mt6797.c', '''static int mtk_infrasys_init(struct platform_device *pdev)
{
	int i;
	struct device_node *node = pdev->dev.of_node;

''', '''static int mtk_infrasys_init(struct platform_device *pdev)
{
	struct device_node *node = pdev->dev.of_node;
	int i, ret;

	ret = mtk_register_reset_controller_with_dev(&pdev->dev, &infra_rst_desc);
	if (ret)
		return ret;

''')
    elif phase == 'provider-test':
        create(CLK + 'clk-mt6797-reset-test.c', SOC_TEST)
        change(CLK + 'Kconfig', 'config COMMON_CLK_MT6797_MMSYS\n', '''config COMMON_CLK_MT6797_RESET_KUNIT_TEST
	tristate "Test MT6797 infracfg reset mapping" if !KUNIT_ALL_TESTS
	depends on KUNIT
	default KUNIT_ALL_TESTS
	help
	  Test the two supported MT6797 reset lines and the rejected
	  public indices using the production descriptor and helpers.
	  Verify thermal and PMIC-wrapper SET/CLEAR offsets and masks.
	  This test does not register a controller or access hardware.

config COMMON_CLK_MT6797_MMSYS
''')
        change(CLK + 'Makefile', 'obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\n',
               'obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\nobj-$(CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST) += clk-mt6797-reset-test.o\n')
    elif phase == 'dts':
        change(DTS, '''compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		#clock-cells = <1>;
	};''', '''compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		#clock-cells = <1>;
		#reset-cells = <1>;
	};''')
    else:
        raise ValueError('unknown phase')
    return out


def expected_stages(fetcher):
    manifest = json.loads((HERE.parent / 'derivation-inputs.json').read_text())
    files = {}
    for entry in manifest['remote']:
        source = fetcher(entry)
        data = source.encode('utf-8')
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('pinned derivation input mismatch: ' + entry['path'])
        files[entry['path']] = source
    stages = [files]
    for phase in PHASES:
        stages.append(phase_edits(stages[-1], phase))
    return stages


# Exact revised inputs; the historical phase editor above remains unchanged.
REVISED_PROPOSAL_SHA256 = 'd387544cb48726d2b49fe8cf19650e89cbaef3ddb623e2a151a1491e88d07cee'


def revised_inputs(raw, read_file):
    """Validate the immutable ordered proposal and every input before Git writes."""
    if hashlib.sha256(raw).hexdigest() != REVISED_PROPOSAL_SHA256:
        raise ValueError('revised proposal identity')
    proposal = json.loads(raw)
    entries = proposal['ordered_inputs']
    if [e['position'] for e in entries] != list(range(1, 7)):
        raise ValueError('revised input order')
    for entry in entries:
        for path_key, hash_key in [('original_path', 'original_sha256'),
                                   ('selected_path', 'selected_sha256')]:
            data = read_file(entry[path_key])
            if hashlib.sha256(data).hexdigest() != entry[hash_key]:
                raise ValueError('revised patch identity: ' + entry[path_key])
    return proposal


def revised_final(proposal, hashes, changed_paths):
    """Require exact source bytes and footprint, including unchanged binding."""
    expected = proposal['expected_final_source_sha256']
    if hashes != expected or sorted(changed_paths) != sorted(set(expected) - {SCHEMA}):
        raise ValueError('revised final source identity/footprint')


def revised_scratch(root):
    import os
    import shutil
    import stat
    identity = 'infracfg revised Git-index generation v1\n'
    if not root.exists() and not root.is_symlink():
        root.mkdir(mode=0o700)
        (root / '.owner').write_text(identity)
    info = root.lstat()
    marker = root / '.owner'
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or
            info.st_mode & 0o077 or marker.is_symlink() or not marker.is_file() or
            marker.read_text() != identity):
        raise ValueError('unrecognized revised scratch')
    if set(p.name for p in root.iterdir()) - {'.owner', 'run'}:
        raise ValueError('unknown revised scratch contents')
    work = root / 'run'
    if work.is_symlink() or (work.exists() and not work.is_dir()):
        raise ValueError('unsafe revised scratch run')
    if work.exists():
        shutil.rmtree(work)
    return work


def revised_generate(revision, published_ref):
    """Use retained source/checker and a disposable bare Git index, never a tree copy."""
    import fcntl
    import importlib.util
    import os
    import re
    import shutil
    import stat
    import subprocess
    import sys
    repo = HERE.parents[2]
    if sys.platform != 'linux' or not str(repo).startswith('/workspace/gemini-pda/checkouts/'):
        raise ValueError('managed Buildbox checkout required')
    if not re.fullmatch('[0-9a-f]{40}', revision) or not published_ref.startswith('refs/heads/'):
        raise ValueError('exact revision and full branch ref required')
    subprocess.run(['git', 'check-ref-format', published_ref], check=True, timeout=5, capture_output=True)
    for args, expected in [(['rev-parse', 'HEAD'], revision), (['status', '--porcelain'], ''),
                           (['remote', 'get-url', 'origin'], 'https://github.com/ixoo/gemini-pda-mainline.git')]:
        if subprocess.check_output(['git', '-C', str(repo), *args], text=True, timeout=5).strip() != expected:
            raise ValueError('project checkout identity/cleanliness')
    def read_input(name):
        path = repo / name
        if path.is_symlink() or not path.is_file() or path.resolve() != path:
            raise ValueError('nonregular proposal input')
        return path.read_bytes()
    proposal = revised_inputs((HERE.parent / 'revised-topic/proposal.json').read_bytes(), read_input)
    spec = importlib.util.spec_from_file_location('revised_retained', HERE / 'schema-check.py')
    retained = importlib.util.module_from_spec(spec); spec.loader.exec_module(retained)
    require, contract = retained.require, retained.C
    limits = dict(contract, log_bytes=262144, generated_file_bytes=134217728)
    scratch = Path('/workspace/gemini-pda/tmp/infracfg-revised-generation')
    parent = Path('/workspace/gemini-pda/review-packages/infracfg-revised')
    require(parent.is_dir() and parent.resolve() == parent, 'explicit real output parent required')
    require(scratch.parent.is_dir() and scratch.parent.resolve() == scratch.parent, 'real scratch parent required')
    descriptor = os.open(Path.home() / 'gemini-pda-buildbox/build.lock', os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'existing regular shared lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for path in (scratch.parent, parent):
            require(shutil.disk_usage(path).free >= 1024 ** 3, '1 GiB free required')
        before = retained.check_files()
        tools = retained.check_tools()
        require(tools == json.loads((HERE.parent / 'results/schema-attempt-2-f4ff1028/result.json').read_text())['tools'], 'retained tools changed')
        processed = Path(contract['build_root']) / 'Documentation/devicetree/bindings/processed-schema.json'
        processed_hash = retained.sha(processed)
        require(processed_hash == 'a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38', 'retained schema changed')
        output = parent / revision
        output.mkdir(mode=0o700)  # Never replace a completed or refused receipt.
        receipt = {'result': 'INCOMPLETE', 'mode': 'revised', 'repository_commit': revision,
                   'published_ref': published_ref, 'proposal_sha256': REVISED_PROPOSAL_SHA256,
                   'commands': [], 'before': before, 'tools': tools,
                   'certification': 'synthetic non-certifying review identity; actual authors/DCO unresolved'}
        retained.guard.write_receipt(output, receipt)
        with retained.guard.interruption_guard() as interrupted:
            work = None
            try:
                work = revised_scratch(scratch)
                work.mkdir(mode=0o700)
                env = {'PATH': contract['tools_root'] + '/bin:/usr/bin:/bin', 'HOME': str(work),
                       'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
                       'GIT_AUTHOR_NAME': 'Gemini Mainline Experiment', 'GIT_COMMITTER_NAME': 'Gemini Mainline Experiment',
                       'GIT_AUTHOR_EMAIL': 'gemini-mainline@example.invalid', 'GIT_COMMITTER_EMAIL': 'gemini-mainline@example.invalid',
                       'LC_ALL': 'C.UTF-8', 'TMPDIR': str(work), 'PYTHONDONTWRITEBYTECODE': '1',
                       'GIT_INDEX_FILE': str(work / 'index')}
                def run(name, argv, seconds=30):
                    require(len(receipt['commands']) < 80, 'generation command budget')
                    facts = retained.collect({'name': name, 'argv': argv, 'timeout': seconds}, output, env, descriptor, interrupted, limits)
                    receipt['commands'].append(facts); retained.guard.write_receipt(output, receipt)
                    retained.accepted_command(facts)
                    out, err = ((output / (name + ext)).read_text() for ext in ('.stdout', '.stderr'))
                    require(not err, 'unexpected command stderr: ' + name)
                    return out.strip()
                receipt['git_version'] = run('git-version', ['git', '--version'])
                receipt['perl_version'] = run('perl-version', ['perl', '--version'])
                advertised = run('publication', ['git', 'ls-remote', '--exit-code', '--refs', 'https://github.com/ixoo/gemini-pda-mainline.git', published_ref])
                require(advertised == revision + '\t' + published_ref, 'fresh publication mismatch')
                integrity = [str(Path(contract['tools_root']) / 'bin/python'), str(repo / 'scripts/source-tree-integrity'), 'verify', contract['source_root']]
                require(run('source-before', integrity, 180) == 'source_tree_integrity=' + contract['source_integrity'], 'source integrity before')
                git = ['git', '--git-dir=' + str(work / 'objects.git')]
                run('git-init', git + ['init', '--bare', '--quiet'])
                run('git-remote', git + ['remote', 'add', 'origin', 'https://github.com/torvalds/linux.git'])
                run('git-fetch', git + ['-c', 'protocol.version=2', 'fetch', '--quiet', '--filter=blob:none', '--depth=1', 'origin', proposal['upstream_commit']], 60)
                upstream = proposal['upstream_commit']
                require(run('upstream-identity', git + ['rev-parse', 'FETCH_HEAD']) == upstream, 'upstream parent')
                new_paths = [BINDING, CLK + 'reset-internal.h', CLK + 'reset-test.c', CLK + 'clk-mt6797-reset.h', CLK + 'clk-mt6797-reset-test.c']
                require(not run('new-paths-absent', git + ['ls-tree', '-r', '--name-only', upstream, '--', *new_paths]), 'new upstream path exists')
                run('index-parent', git + ['read-tree', upstream])
                run('head-parent', git + ['update-ref', 'HEAD', upstream])
                head = upstream
                subjects = ['clk: mediatek: reject out-of-bank SET/CLEAR reset IDs',
                            'clk: mediatek: test reset translation bounds',
                            'dt-bindings: reset: mediatek: add MT6797 infracfg reset IDs',
                            'clk: mediatek: add MT6797 infracfg SET/CLEAR resets',
                            'clk: mediatek: test MT6797 infracfg reset mapping',
                            'arm64: dts: mediatek: expose MT6797 infracfg resets']
                for entry, subject in zip(proposal['ordered_inputs'], subjects):
                    number = entry['position']; patch = str(repo / entry['selected_path'])
                    run(f'input-{number}-check', git + ['apply', '--cached', '--check', patch])
                    run(f'input-{number}-apply', git + ['apply', '--cached', patch])
                    run(f'input-{number}-whitespace', git + ['diff', '--cached', '--check'])
                    # Tree IDs preserve every indexed reference; omitted unrelated
                    # blobs need not be fetched. Final source hashes remain mandatory.
                    tree = run(f'input-{number}-tree', git + ['write-tree', '--missing-ok'])
                    message = work / 'message'
                    if number == 3:
                        body = 'Expose the thermal and PMIC-wrapper reset IDs.\nKeep the existing optional reset-cell binding unchanged so older\nMT6797 descriptions remain valid.'
                    else:
                        # Retain original review message body, never copy its mail identity.
                        import email
                        mail = email.message_from_bytes(read_input(entry['original_path']))
                        body = mail.get_payload().split('\n---\n', 1)[0].strip()
                        require(body and 'Signed-off-by:' not in body, 'unexpected certification/body')
                    message.write_text(subject + '\n\n' + body + '\n')
                    env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = f'2026-09-05T03:0{number - 1}:00Z'
                    head = run(f'input-{number}-commit', git + ['commit-tree', tree, '-p', head, '-F', str(message)])
                    require(re.fullmatch('[0-9a-f]{40}', head), 'generated commit identity')
                    run(f'input-{number}-head', git + ['update-ref', 'HEAD', head])
                changed = run('final-paths', git + ['diff', '--name-only', upstream, head]).splitlines()
                hashes = {}
                for number, name in enumerate(proposal['expected_final_source_sha256']):
                    # Hash in the guarded group: source bytes never enter receipt logs.
                    digest = run(f'final-hash-{number}', ['bash', '-o', 'pipefail', '-c', 'git "$@" | sha256sum', 'source-hash',
                                                       '--git-dir=' + str(work / 'objects.git'), 'show', head + ':' + name])
                    hashes[name] = digest.split()[0]
                revised_final(proposal, hashes, changed)
                receipt.update(generated_head=head, tree=tree, final_source_sha256=hashes)
                patch_dir = output / 'patches'; patch_dir.mkdir()
                run('format-patch', git + ['format-patch', '--no-signature', '--numbered', '--output-directory', str(patch_dir), upstream + '..' + head])
                patches = sorted(patch_dir.glob('*.patch'))
                require(len(patches) == 6 and all(not p.is_symlink() and p.is_file() and p.stat().st_size <= 65536 for p in patches), 'generated patch inventory/size')
                (patch_dir / 'series').write_text(''.join(p.name + '\n' for p in patches))
                env['GIT_INDEX_FILE'] = str(work / 'replay-index')
                run('replay-parent', git + ['read-tree', upstream])
                for number, patch in enumerate(patches, 1):
                    run(f'replay-{number}-check', git + ['apply', '--cached', '--check', str(patch)])
                    run(f'replay-{number}-apply', git + ['apply', '--cached', str(patch)])
                require(run('replay-tree', git + ['write-tree', '--missing-ok']) == tree, 'replay tree mismatch')
                source = Path(contract['source_root'])
                run('checkpatch', ['perl', str(source / 'scripts/checkpatch.pl'), '--no-tree', '--strict',
                                  '--ignore', 'MISSING_SIGN_OFF,FILE_PATH_CHANGES,COMMIT_LOG_LONG_LINE', *map(str, patches)])
                run('maintainers', ['bash', '-c', 'cd "$1" || exit; shift; exec perl scripts/get_maintainer.pl --no-git --no-git-fallback --no-git-blame --no-file-emails --no-mailmap --no-fixes --roles --no-rolestats --scm "$@"',
                                    'maintainer-review', str(source), *map(str, patches)])
                receipt['retained_dtbs'] = {name: retained.inspect_dtb(Path(contract['build_root']) / 'arch/arm64/boot/dts' / name) for name in contract['dtbs']}
                require(run('source-after', integrity, 180) == 'source_tree_integrity=' + contract['source_integrity'], 'source integrity after')
                receipt['patches'] = {p.name: retained.sha(p) for p in patches}
                receipt['replay'] = 'exact-full-tree-match'
                receipt['result'] = 'COLLECTED_REVIEW_REQUIRED'
            except Exception as error:
                receipt['result'] = 'REFUSED'; receipt['reason'] = str(error)
            finally:
                try:
                    if work is not None and work.exists():
                        shutil.rmtree(work)
                    receipt['scratch_removed'] = work is not None and not work.exists()
                except OSError as error:
                    receipt['scratch_removed'] = False
                    receipt['result'] = 'REFUSED'; receipt['cleanup_error'] = str(error)
                try:
                    receipt['after'] = retained.check_files()
                    require(receipt['before'] == receipt['after'], 'retained source/build changed')
                    require(retained.check_tools() == tools and retained.sha(processed) == processed_hash, 'retained tools/processed changed')
                except Exception as error:
                    receipt['result'] = 'REFUSED'; receipt['preservation_error'] = str(error)
                retained.guard.publish_completed_result(output, receipt, interrupted)
        require(receipt['result'] == 'COLLECTED_REVIEW_REQUIRED', 'generation refused; preserve evidence before any retry')
    finally:
        os.close(descriptor)


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--revised-generate":
        parser = argparse.ArgumentParser(description="Explicit revised review archive; Buildbox only")
        parser.add_argument("--revised-generate", required=True)
        parser.add_argument("--published-ref", required=True)
        args = parser.parse_args()
        revised_generate(args.revised_generate, args.published_ref)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--phase', choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not str(root).startswith('/workspace/gemini-pda/tmp/infracfg-topic.'):
        raise ValueError('only an isolated Buildbox scratch checkout is allowed')
    manifest = json.loads((HERE.parent / 'derivation-inputs.json').read_text())
    # Reconstruct every expected intermediate from immutable Git parent bytes.
    import subprocess
    def original(entry):
        data = subprocess.check_output(['git', '-C', str(root), 'show',
                                        manifest['upstream_commit'] + ':' + entry['path']])
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('pinned parent changed: ' + entry['path'])
        return data.decode('utf-8')
    stages = expected_stages(original)
    new_paths = sorted(set(stages[-1]) - set(stages[0]))
    existing = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r',
                                       '--name-only', manifest['upstream_commit'],
                                       '--', *new_paths], text=True)
    if existing:
        raise ValueError('new path already exists in upstream Git tree')
    index = PHASES.index(args.phase)
    before, after = stages[index:index + 2]
    # Check the entire derivation inventory before any edit, including future paths.
    for name in stages[-1]:
        path = root / name
        if path.is_symlink() or (name in before and
                                (not path.is_file() or path.read_text() != before[name])):
            raise ValueError('intermediate source mismatch: ' + name)
        if name not in before and path.exists():
            raise ValueError('unexpected existing path: ' + name)
    for name, content in after.items():
        if before.get(name) != content:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


if __name__ == '__main__':
    main()
