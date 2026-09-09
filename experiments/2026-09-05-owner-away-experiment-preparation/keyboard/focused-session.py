#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Freeze a private focused-session plan. This module has no transport action."""
import argparse
import base64
import copy
import json
from pathlib import Path
import runpy
import subprocess
import uuid

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE/'capture.py'))
C, S, L, require, sha = (M[k] for k in ('C', 'S', 'L', 'require', 'sha'))
BUILDER = runpy.run_path(str(HERE/'../baseline/scripts/buildbox_userspace.py'))
DEST = '/a53-keyboard-focused'
A_FILES = ('keyboard-monitor', 'licenses/musl-COPYRIGHT', 'licenses/repository-LICENSE', 'licenses/GCC-copyright')
B_FILES = ('keyboard-observe', 'licenses/GPL-2')


def package(path, identity, revision):
    BUILDER['check_package'](path, identity, revision)
    return json.loads((path/'manifest.json').read_bytes())


def artifact_guard(files):
    text = ''
    for directory in (DEST, DEST+'/licenses'):
        text += f'[ -d {directory} ] && [ ! -L {directory} ]\n'
        text += f'[ "$($BB stat -c %u:%a {directory})" = 0:700 ]\n'
    text += "[ \"$($BB awk '$2 == \"/\" {n++; if (($3 == \"rootfs\" || $3 == \"ramfs\" || $3 == \"tmpfs\") && $4 !~ /(^|,)(ro|noexec)(,|$)/) ok++} END {print n+0 \":\" ok+0}' /proc/mounts)\" = 1:1 ]\n"
    text += f"[ \"$($BB awk '$2 == \"{DEST}\" || index($2, \"{DEST}/\") == 1 {{n++}} END {{print n+0}}' /proc/mounts)\" = 0 ]\n"
    for name, data in files.items():
        path = DEST + '/' + name
        mode = 700 if name in ('keyboard-monitor', 'keyboard-observe') else 600
        text += f'[ -f {path} ] && [ ! -L {path} ]\n'
        text += f'[ "$($BB stat -c %u:%a:%h:%s {path})" = 0:{mode}:1:{len(data)} ]\n'
        text += f'h=$($BB sha256sum {path}); [ "${{h%% *}}" = {sha(data)} ]\n'
    return text


def commands(context, files, ident):
    # Reuse the existing identity, RAM, logger, map, ancestry and reader guards.
    group_a = {name: files[name] for name in A_FILES}
    text = M['delivery_script']({**context, 'delivery_files': group_a}).decode()
    text = text.replace('/a53-keyboard-delivery', DEST)
    text = text.replace('__KEYBOARD_DELIVERY_PASS__', '__FOCUSED_DELIVERY_A_PASS__')
    first = text.encode()
    second = M['guard'](context, True) + artifact_guard(group_a)
    second += f'[ ! -e {DEST}/keyboard-attempt ] && [ ! -L {DEST}/keyboard-attempt ]\n'
    second += 'umask 077\nset -C\n'
    for index, name in enumerate(B_FILES):
        path = DEST + '/' + name
        second += f'[ ! -e {path} ] && [ ! -L {path} ]\n'
        second += f"$BB base64 -d >{path} <<'FOCUSED_FILE_{index}'\n{base64.b64encode(files[name]).decode()}\nFOCUSED_FILE_{index}\n"
    second += f'$BB chmod 700 {DEST}/keyboard-observe\n'
    second += artifact_guard(files)
    second += f"$BB printf '%s\\n' '{ident}' >{DEST}/ready\n"
    second += "$BB printf '__FOCUSED_DELIVERY_B_PASS__\\n'\n"
    capture = M['capture_script'](context).decode().replace('/a53-keyboard-delivery', DEST)
    require(capture.count('\nset +e\n') == 1, 'capture template changed')
    capture = capture.replace('\nset +e\n', '\n' + artifact_guard({**files, 'ready': (ident+'\n').encode()}) + 'set +e\n')
    capture = capture.replace('__KEYBOARD_POSTFLIGHT_PASS__', '__FOCUSED_POSTFLIGHT_PASS__')
    export = M['export_script'](context).replace(b'/a53-keyboard-delivery', DEST.encode())
    result = {'delivery-a.sh': first, 'delivery-b.sh': second.encode(),
              'capture.sh': capture.encode(), 'export.sh': export}
    require(all(len(raw) <= 262144 for raw in result.values()), 'command byte ceiling')
    return result


def prepare(reference_path, reference_package, focused_package, identity, revision, ident):
    require(C['UUID'].fullmatch(ident), 'new plan identity')
    reference_raw = C['regular'](reference_path, 65536)
    ref = json.loads(reference_raw, object_pairs_hook=L['unique'])
    require(ident not in (ref['id'], ref['runtime'].get('retry_id')), 'consumed identity')
    review_raw = (HERE/'focused-disconnect-source-review.json').read_bytes()
    review = json.loads(review_raw)
    require(review['scope'] == 'historical-scaled-probe-only' and review['same_boot_required'] is True
            and review['preprocessed_equal'] is True and review['new_device_proof_claim'] is False,
            'historical proof scope')
    old, new = review['records']
    # The reader may change while the reviewed supervisor sources stay identical.
    # Both current sources and the new package inputs are checked below.
    require(ref['package_revision'] == old['revision'], 'reviewed legacy revision')
    for entry in (old, new):
        for name, digest in entry['sources'].items():
            raw = subprocess.check_output(['git', '-C', str(L['REPO']), 'show',
                entry['revision'] + ':' + (HERE/name).relative_to(L['REPO']).as_posix()])
            require(sha(raw) == digest, 'review source revision')
            if entry is new:
                require(sha((HERE/name).read_bytes()) == digest, 'focused source changed')
    previous = package(reference_package, ref['package_identity'], ref['package_revision'])
    require(previous['inputs']['monitor.c'] == old['sources']['monitor.c'], 'legacy source package')
    pins = {line.split('  ./', 1)[1]: line.split('  ./', 1)[0]
            for line in (reference_package/'SHA256SUMS').read_text().splitlines()}
    dependency = L['completed_baseline'](ref['dependency'])
    M['P']['verify'](ref, dependency['prepared']['candidate'], pins, C['regular'], M['ROOT'],
                   monitor_source_sha256=old['sources']['monitor.c'])
    manifest = package(focused_package, identity, revision)
    require(manifest.get('monitor_entry') == 'focused-admission-v1' and manifest['replicas_identical'] is True,
            'focused package type')
    for name, digest in manifest['inputs'].items():
        if name != 'musl.tar.gz':
            require(sha((HERE/name).read_bytes()) == digest, 'focused package source drift')
    files = {name: (focused_package/name).read_bytes() for name in A_FILES+B_FILES}
    require(all(0 < len(data) <= 131072 for data in files.values()), 'file ceiling')
    runtime = copy.deepcopy(ref['runtime'])
    runtime.pop('retry_id', None)
    runtime.update(logger_clock='restarted', logger_age_limit_seconds=120)
    admission = {'boot_id': ref['boot_id'], 'runtime': runtime, 'monitor_sha256': sha(files['keyboard-monitor'])}
    context = {'admission': admission, 'dependency': dependency}
    scripts = commands(context, files, ident)
    plan = {'schema': 'focused-session-plan-v1', 'execution': 'disabled', 'id': ident,
        'boot_id': ref['boot_id'], 'reference_sha256': sha(reference_raw),
        'source_review_sha256': sha(review_raw), 'sources': M['source_identity'](),
        'planner_sha256': sha(Path(__file__).read_bytes()),
        'package': {'identity': identity, 'revision': revision},
        'historical_prerequisites_revalidated': True, 'new_owner_readiness': False,
        'logger_start_age_limit_seconds': 120, 'logger_seconds': 600,
        'phases': {name: {'command_sha256': sha(raw), 'command_bytes': len(raw),
                         'seconds': 60 if name == 'capture.sh' else 30}
                   for name, raw in scripts.items()},
        'remaining': ['fresh owner/Space readiness', 'current boot and logger-clock/PID readback',
                      'restart from latest preserved retry seal with a fresh archive claim',
                      'bind and retain execution receipts, export and independent log seal']}
    return plan, scripts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'reference-package', 'package', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--package-identity', required=True)
    parser.add_argument('--package-revision', required=True)
    args = parser.parse_args()
    plan, scripts = prepare(args.reference, args.reference_package, args.package,
                            args.package_identity, args.package_revision, str(uuid.uuid4()))
    args.output.mkdir(mode=0o700)
    for name, raw in scripts.items():
        C['write_new'](args.output/name, raw)
    C['write_new'](args.output/'plan.json', M['encode'](plan))
    print('focused_plan=prepared execution=disabled')


if __name__ == '__main__':
    main()
