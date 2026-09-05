#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One admitted compatibility run, reusing existing bounded schema collectors."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import compare
import derive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('retained_schema', HERE.parent / 'scripts/schema-check.py')
retained = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retained)
C = retained.C
require = compare.require
PREVIOUS = HERE.parent / 'results/schema-attempt-2-f4ff1028/result.json'
# Narrow enough to preserve all diagnostics, including expected negative cases.
LIMITS = dict(C, log_bytes=262144, generated_file_bytes=134217728)
SCRATCH = Path('/workspace/gemini-pda/tmp/infracfg-binding-compatibility')
OUTPUT_PARENT = Path('/workspace/gemini-pda/artifacts/binding-compatibility')


def optional(raw):
    require(hashlib.sha256(raw).hexdigest() == C['source_files'][derive.SCHEMA], 'wrong mandatory binding')
    anchor = b'          - mediatek,mt6795-infracfg\n          - mediatek,mt6797-infracfg\n          - mediatek,mt7622-infracfg\n'
    require(raw.count(anchor) == 1, 'wrong conditional boundary')
    corrected = raw.replace(anchor, anchor.replace(b'          - mediatek,mt6797-infracfg\n', b''))
    require(hashlib.sha256(corrected).hexdigest() == derive.SCHEMA_SHA256, 'wrong optional binding')
    return corrected


def scratch_root(root):
    identity = 'infracfg binding compatibility scratch v1\n'
    if not root.exists() and not root.is_symlink():
        root.mkdir(mode=0o700)
        (root / '.owner').write_text(identity)
    info = root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077, 'scratch ownership/mode')
    marker = root / '.owner'
    require(not marker.is_symlink() and marker.is_file() and marker.read_text() == identity, 'unknown scratch')
    work = root / 'run'
    require(not work.is_symlink() and (not work.exists() or work.is_dir()), 'unsafe scratch run')
    if work.exists():
        shutil.rmtree(work)
    return work


def dtc_diagnostics(case, text, source):
    malformed = case['name'] in ('mt6797-two-cells', 'mt6797-string', 'mt6797-byte', 'mt6797-boolean')
    require(source.name == case['name'] + '.dts', 'wrong diagnostic fixture path')
    if not malformed:
        require(not text, 'unexpected dtc diagnostic case')
        return
    lines = text.splitlines()
    require(len(lines) == 2 and text == '\n'.join(lines) + '\n', 'missing/extra dtc diagnostic chain')
    require(re.fullmatch(re.escape(str(source)) + r':[0-9]+\.[0-9]+(?:-[0-9]+(?:\.[0-9]+)?)?: Warning \(resets_is_cell\): /infracfg@10001000:#reset-cells: property is not a single cell', lines[0]), 'unexpected primary dtc diagnostic')
    require(lines[1] == str(source.with_suffix('.dtb')) + ": Warning (resets_property): Failed prerequisite 'resets_is_cell'", 'unexpected dependent dtc diagnostic')


def execute(revision, published_ref):
    require(sys.platform == 'linux' and str(ROOT).startswith('/workspace/gemini-pda/checkouts/'), 'managed Buildbox only')
    require(published_ref.startswith('refs/heads/'), 'full published branch ref required')
    subprocess.run(['git', 'check-ref-format', published_ref], check=True, timeout=5, capture_output=True)
    require(subprocess.check_output(['git', '-C', str(ROOT), 'remote', 'get-url', 'origin'], text=True, timeout=5).strip() == 'https://github.com/ixoo/gemini-pda-mainline.git', 'wrong project origin')
    require(len(revision) == 40 and all(c in '0123456789abcdef' for c in revision), 'exact revision')
    require(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() == revision, 'wrong project revision')
    require(not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip(), 'dirty project checkout')
    descriptor = os.open(Path.home() / 'gemini-pda-buildbox/build.lock', os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'existing regular lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(SCRATCH.parent.is_dir() and SCRATCH.parent.resolve() == SCRATCH.parent, 'managed scratch parent')
        require(OUTPUT_PARENT.is_dir() and OUTPUT_PARENT.resolve() == OUTPUT_PARENT, 'admitted evidence parent required')
        for p in (SCRATCH.parent, OUTPUT_PARENT):
            require(shutil.disk_usage(p).free >= 512 * 1024 * 1024, '512 MiB headroom required')
        tools = retained.check_tools()
        previous = json.loads(PREVIOUS.read_text())['tools']
        require(tools == previous, 'retained tool identity/version changed')
        before = retained.check_files()
        processed = Path(C['build_root']) / 'Documentation/devicetree/bindings/processed-schema.json'
        processed_before = retained.sha(processed)
        require(processed_before == 'a3265d87a3617c19c3463fb3a728df2120b8932ee0be686dcd8c4f69fac82b38', 'retained processed schema changed')
        output = OUTPUT_PARENT / revision
        output.mkdir(mode=0o700)  # Existing result, even refused, cannot be replaced.
        receipt = {'result': 'INCOMPLETE', 'repository_commit': revision, 'commands': [], 'tools': tools, 'before': before, 'published_ref': published_ref}
        retained.guard.write_receipt(output, receipt)
        with retained.guard.interruption_guard() as interrupted:
            work = None
            try:
                work = scratch_root(SCRATCH)
                # The try/finally cleanup is installed before creating source state.
                work.mkdir(mode=0o700)
                env = {'PATH': C['tools_root'] + '/bin:/usr/bin:/bin', 'HOME': str(Path.home()),
                       'GIT_TERMINAL_PROMPT': '0', 'LC_ALL': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(work)}
                def run(name, argv, timeout=30):
                    facts = retained.collect({'name': name, 'argv': argv, 'timeout': timeout}, output, env, descriptor, interrupted, LIMITS)
                    receipt['commands'].append(facts)
                    retained.guard.write_receipt(output, receipt)
                    retained.accepted_command(facts)
                    return ((output / (name + '.stdout')).read_text(), (output / (name + '.stderr')).read_text())
                out, err = run('publication', ['git', 'ls-remote', '--exit-code', '--refs', 'https://github.com/ixoo/gemini-pda-mainline.git', published_ref])
                require(not err and out.strip() == revision + '\t' + published_ref, 'fresh published revision mismatch')
                integrity = [str(Path(C['tools_root']) / 'bin/python'), str(ROOT / 'scripts/source-tree-integrity'), 'verify', C['source_root']]
                out, err = run('source-before', integrity, 180)
                require(not err and out.strip() == 'source_tree_integrity=' + C['source_integrity'], 'source integrity diagnostic')
                raw = (Path(C['source_root']) / derive.SCHEMA).read_bytes()
                for variant, data in [('mandatory', raw), ('optional', optional(raw))]:
                    directory = work / variant / 'clock'; directory.mkdir(parents=True)
                    binding = directory / 'mediatek,infracfg.yaml'; binding.write_bytes(data)
                    out, err = run(variant + '-doc', [tools['dt-doc-validate']['path'], str(binding)])
                    require(not out and not err, 'binding meta-schema diagnostic')
                    out, err = run(variant + '-process', [tools['dt-mk-schema']['path'], '-j', '-o', str(work / variant / 'processed.json'), str(binding)])
                    require(not out and not err, 'schema processing diagnostic')
                    retained.check_processed(work / variant / 'processed.json')
                cases = compare.load_cases(HERE / 'fixtures.json')
                receipt['fixtures_sha256'] = retained.sha(HERE / 'fixtures.json')
                receipt['dtbs'] = {}
                for case in cases:
                    source = work / (case['name'] + '.dts'); source.write_text(case['dts'])
                    dtb = source.with_suffix('.dtb')
                    out, err = run('dtc-' + case['name'], [tools['build-dtc']['path'], '-I', 'dts', '-O', 'dtb', '-o', str(dtb), str(source)], 5)
                    require(not out, 'unexpected dtc stdout'); dtc_diagnostics(case, err, source)
                    require(0 < dtb.stat().st_size <= 65536, 'fixture DTB ceiling')
                    receipt['dtbs'][case['name']] = {'dts': retained.sha(source), 'dtb': retained.sha(dtb)}
                out, err = run('compare', [str(Path(C['tools_root']) / 'bin/python'), str(HERE / 'compare.py'), '--child', str(work), str(HERE / 'fixtures.json')], 60)
                require(not err, 'unattributed schema decoder/runtime diagnostic')
                result = json.loads(out)
                require(result.get('decoder_modules_sha256') == compare.DECODER_MODULES, 'wrong decoder source identity')
                for variant, digest in result['processed_sha256'].items():
                    require(variant in ('mandatory', 'optional') and retained.sha(work / variant / 'processed.json') == digest, 'processed output identity')
                require(set(result['processed_sha256']) == {'mandatory', 'optional'}, 'missing processed identity')
                for row in result['rows']:
                    require(row['dtb_sha256'] == receipt['dtbs'][row['case']]['dtb'], 'wrong DTB attribution')
                receipt['comparison'] = compare.classify(result['rows'], cases)
                out, err = run('source-after', integrity, 180)
                require(not err and out.strip() == 'source_tree_integrity=' + C['source_integrity'], 'post integrity diagnostic')
                receipt['result'] = 'COLLECTED_REVIEW_REQUIRED'
            except Exception as error:
                receipt['result'] = 'REFUSED'; receipt['reason'] = str(error)
            finally:
                if work is not None and work.exists():
                    shutil.rmtree(work)
                receipt['scratch_removed'] = work is not None and not work.exists()
                try:
                    receipt['after'] = retained.check_files()
                    require(receipt['before'] == receipt['after'], 'protected inputs changed')
                    require(retained.sha(processed) == processed_before, 'retained processed schema changed')
                    require(retained.check_tools() == tools, 'tools changed')
                except Exception as error:
                    receipt['result'] = 'REFUSED'; receipt['preservation_error'] = str(error)
                retained.guard.publish_completed_result(output, receipt, interrupted)
        require(receipt['result'] == 'COLLECTED_REVIEW_REQUIRED', 'run refused; retain evidence and review before retry')
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', metavar='EXACT_PUBLISHED_REVISION')
    parser.add_argument('--published-ref', default='')
    args = parser.parse_args()
    if args.execute:
        execute(args.execute, args.published_ref)
    else:
        print('PREPARED_ONLY: requires exact published checkout, assigned lock window and pinned schema Python; no execution')
