#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Plan or collect a bounded schema check under the retained Buildbox lock.

Never declares hardware support or an automatic schema PASS. Collected logs need
integrator review, including diagnostics from recipes that hide tool failures.
"""
import argparse
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
C = json.loads((HERE.parent / 'schema-contract.json').read_text())
spec = importlib.util.spec_from_file_location('schema_process_guard', HERE / 'qemu-check.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
require = guard.require
Refusal = guard.Refusal


def sha(path):
    require(stat.S_ISREG(path.lstat().st_mode), 'regular file required: ' + path.name)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def plan(contract=C):
    source, build, tools = (Path(contract[k]) for k in ('source_root', 'build_root', 'tools_root'))
    common = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
              'CROSS_COMPILE=aarch64-linux-gnu-', '-j1', 'V=1',
              'DT_SCHEMA_FILES=' + contract['schema_filter']]
    schema = build / 'Documentation/devicetree/bindings/processed-schema.json'
    return [{'name': name, 'argv': common + [name], 'timeout': contract['make_timeout_seconds']}
            for name in ('dt_binding_check', 'dtbs_check')] + [
        {'name': 'explicit-' + Path(dtb).stem,
         'argv': [str(tools / 'bin/dt-validate'), '-v', '-s', str(schema),
                  '-l', contract['schema_filter'], str(build / 'arch/arm64/boot/dts' / dtb)],
         'timeout': contract['direct_timeout_seconds']} for dtb in contract['dtbs']]


def check_files(contract=C):
    source, build = (Path(contract[k]) for k in ('source_root', 'build_root'))
    for root in (source, build):
        require(root.is_dir() and root.resolve() == root, 'exact real source/build root required')
    for marker, expected in [('.gemini-source-state', contract['source_state']),
                             ('.gemini-source-integrity', contract['source_integrity'])]:
        require(sha(source / marker) == hashlib.sha256((expected + '\n').encode()).hexdigest(),
                'source marker mismatch: ' + marker)
    result = {'source': {}, 'build': {}}
    for group, root, members in [('source', source, contract['source_files']),
                                  ('build', build, contract['protected_build_files'])]:
        for name, expected in members.items():
            actual = sha(root / name)
            require(actual == expected, group + ' input changed: ' + name)
            result[group][name] = actual
    return result


def inspect_reset_properties(nodes):
    matches = [(name, cells) for name, compatibles, cells in nodes
               if b'mediatek,mt6797-infracfg' in compatibles]
    require(len(matches) == 1, 'exactly one MT6797 infracfg node required')
    require(matches[0][1] == b'\0\0\0\1', 'exactly one reset argument cell required')
    return {'node': matches[0][0], 'reset_cells': 1}


def inspect_dtb(path):
    import libfdt  # Only the pinned schema environment is admitted for execution.
    tree = libfdt.Fdt(path.read_bytes())
    offset, depth = -1, -1
    nodes = []
    for _ in range(4096):
        offset, depth = tree.next_node(offset, depth, quiet=(libfdt.NOTFOUND,))
        if offset < 0 or depth < 0:
            return inspect_reset_properties(nodes)
        require(depth <= 32, 'DTB depth ceiling')
        compatible = tree.getprop(offset, 'compatible', quiet=(libfdt.NOTFOUND,))
        if isinstance(compatible, int):
            continue
        cells = tree.getprop(offset, '#reset-cells', quiet=(libfdt.NOTFOUND,))
        nodes.append((tree.get_name(offset), bytes(compatible).rstrip(b'\0').split(b'\0'),
                      None if isinstance(cells, int) else bytes(cells)))
    raise Refusal('DTB node ceiling')


def check_processed(path, contract=C):
    require(path.stat().st_size <= 128 * 1024 * 1024, 'processed schema size ceiling')
    data = json.loads(path.read_text())
    require(isinstance(data, dict), 'processed schema object required')
    schema_id = contract['schema_id'].rstrip('#')
    entry = data.get(schema_id)
    require(isinstance(entry, dict) and str(entry.get('$id')).rstrip('#') == schema_id,
            'selected processed schema missing')
    require(isinstance(entry.get('properties'), dict), 'processed schema properties missing')
    require('mediatek,mt6797-infracfg' in json.dumps(entry['properties'].get('compatible')),
            'MT6797 compatible absent from processed schema')
    return sha(path)


def collect(command, output, env, lock_fd, interrupted, contract=C):
    facts = {'name': command['name'], 'argv': command['argv'],
             'timeout_seconds': command['timeout'], 'stop_reason': None,
             'log_bytes': contract['log_bytes'],
             'generated_file_bytes': contract['generated_file_bytes']}
    process = None
    started = time.monotonic()
    stdout, stderr = (output / (command['name'] + suffix) for suffix in ('.stdout', '.stderr'))
    def limits():
        if sys.platform.startswith('linux'):
            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
            libc.prctl.restype = ctypes.c_int
            if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), 'schema parent-death setup failed')
            if os.getppid() != parent_pid:
                os.kill(os.getpid(), signal.SIGKILL)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (contract['generated_file_bytes'], contract['generated_file_bytes']))
    try:
        require(interrupted['signal'] is None, 'interrupted before command')
        # Capture through pipes so the parent enforces the smaller stream cap.
        # RLIMIT_FSIZE independently bounds generated regular files in children.
        with stdout.open('xb') as out, stderr.open('xb') as err, selectors.DefaultSelector() as selector:
            parent_pid = os.getpid()
            process = subprocess.Popen(command['argv'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       stdin=subprocess.DEVNULL, env=env, start_new_session=True,
                                       preexec_fn=limits, pass_fds=(lock_fd,))
            counts = {out: 0, err: 0}
            for pipe, destination in ((process.stdout, out), (process.stderr, err)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, destination)
            while process.poll() is None or selector.get_map():
                if interrupted['signal'] is not None:
                    facts['stop_reason'] = 'interrupted: ' + interrupted['signal']
                    break
                if time.monotonic() - started >= command['timeout']:
                    facts['stop_reason'] = 'timeout'
                    break
                for key, _events in selector.select(timeout=0.05):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    destination = key.data
                    remaining = contract['log_bytes'] - counts[destination]
                    kept = chunk[:remaining]
                    destination.write(kept)
                    counts[destination] += len(kept)
                    if counts[destination] >= contract['log_bytes']:
                        facts['stop_reason'] = 'log-limit'
                        break
                if facts['stop_reason'] is not None:
                    break
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        facts['stop_reason'] = str(exc)
    finally:
        if process is not None:
            # The shared helper closes stdin/stdout; close stderr here as well.
            process.stdin = open(os.devnull, 'wb')
            try:
                guard.cleanup_group(process, facts, contract['kill_after_seconds'])
            finally:
                process.stderr.close()
        else:
            facts['returncode'] = None
            facts['cleanup'] = {'group_absent': True}
        if any(p.exists() and p.stat().st_size >= contract['log_bytes'] for p in (stdout, stderr)):
            facts['stop_reason'] = 'log-limit'
        facts['elapsed_seconds'] = round(time.monotonic() - started, 6)
        facts['logs'] = {p.name: sha(p) for p in (stdout, stderr) if p.exists()}
    return facts


def accepted_command(facts):
    require(facts['returncode'] == 0 and facts['stop_reason'] is None, 'command failure')
    require(facts['cleanup']['group_absent'], 'surviving command group')
    require(facts['elapsed_seconds'] <= facts['timeout_seconds'], 'command exceeded budget')


def check_tools(contract=C):
    root = Path(contract['tools_root'])
    require(sha(root / 'SETUP.json') == contract['tools_setup_sha256'], 'schema setup identity')
    require(Path(sys.prefix).resolve() == root, 'run with the pinned schema environment Python')
    import importlib.metadata
    import _libfdt
    setup = json.loads((root / 'SETUP.json').read_text())
    require(importlib.metadata.version('pylibfdt') == '1.7.2.post2', 'pylibfdt version')
    require(sha(Path(_libfdt.__file__)) == setup['pylibfdt_extension_sha256'], 'pylibfdt extension identity')
    require(importlib.metadata.version('dtschema') == '2026.6', 'dtschema version')
    require(importlib.metadata.version('yamllint') == '1.38.0', 'yamllint version')
    tools = {}
    for name in ('dt-doc-validate', 'dt-validate', 'dt-mk-schema', 'yamllint'):
        tools[name] = {'path': str(root / 'bin' / name), 'sha256': sha(root / 'bin' / name)}
    for name in ('make', 'dtc', 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ld'):
        located = shutil.which(name, path='/usr/bin:/bin')
        require(located is not None, 'missing tool: ' + name)
        path = Path(located).resolve()
        tools[name] = {'path': str(path), 'sha256': sha(path)}
    require(tools['aarch64-linux-gnu-gcc']['sha256'] == contract['compiler_sha256'], 'compiler identity')
    require(tools['aarch64-linux-gnu-ld']['sha256'] == contract['linker_sha256'], 'linker identity')
    built_dtc = Path(contract['build_root']) / 'scripts/dtc/dtc'
    tools['build-dtc'] = {'path': str(built_dtc), 'sha256': sha(built_dtc)}
    for name, item in tools.items():
        version = subprocess.run([item['path'], '--version'], capture_output=True, timeout=5, check=True,
                                 env={'PATH': str(root / 'bin') + ':/usr/bin:/bin',
                                      'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'})
        require(len(version.stdout) + len(version.stderr) <= 65536, 'version output limit')
        item['version'] = (version.stdout + version.stderr).decode().strip()
        require(bool(item['version']), 'missing tool version: ' + name)
    return tools


def execute(output, contract=C):
    require(sys.platform.startswith('linux'), 'Buildbox Linux required')
    require(output.parent.resolve() == output.parent and output.parent.is_dir(), 'real evidence parent required')
    require(not any(Path(contract[k]) == output or Path(contract[k]) in output.parents
                    for k in ('source_root', 'build_root', 'tools_root')), 'evidence cannot live inside inputs')
    lock = Path.home() / 'gemini-pda-buildbox/build.lock'
    descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'regular existing build lock required')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(shutil.disk_usage(contract['build_root']).free >= 512 * 1024 * 1024, 'build space headroom')
        require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024, 'evidence space headroom')
        tools = check_tools(contract)
        before = check_files(contract)
        output.mkdir(mode=0o700)  # No replacement, retry or deletion of prior evidence.
        receipt = {'result': 'INCOMPLETE', 'tools': tools, 'before': before, 'commands': []}
        with guard.interruption_guard() as interrupted:
            guard.write_receipt(output, receipt)
            try:
                # Recipe mktemp scratch is managed and removed even on failure.
                with tempfile.TemporaryDirectory(prefix='schema-scratch-', dir=output) as scratch:
                    env = {'PATH': str(Path(contract['tools_root']) / 'bin') + ':/usr/bin:/bin',
                           'HOME': str(Path.home()), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
                           'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': scratch,
                           'PYTHON3': str(Path(contract['tools_root']) / 'bin/python')}
                    integrity = {'name': 'source-integrity-before', 'argv': [sys.executable,
                                 str(ROOT / 'scripts/source-tree-integrity'), 'verify', contract['source_root']],
                                 'timeout': contract['integrity_timeout_seconds']}
                    commands = [integrity] + plan(contract)
                    for command in commands:
                        if command['name'].startswith('explicit-'):
                            receipt['processed_schema_sha256'] = check_processed(
                                Path(contract['build_root']) / 'Documentation/devicetree/bindings/processed-schema.json', contract)
                        facts = collect(command, output, env, descriptor, interrupted, contract)
                        receipt['commands'].append(facts)
                        guard.write_receipt(output, receipt)
                        accepted_command(facts)
                        require(not (output / (command['name'] + '.stderr')).read_bytes().strip(),
                                'diagnostics require review before proceeding: ' + command['name'])
                        if command['name'].startswith('explicit-'):
                            expected = 'Check:  ' + command['argv'][-1]
                            require((output / (command['name'] + '.stdout')).read_text().strip() == expected,
                                    'explicit DTB validation attribution missing or unexpected output')
                    receipt['dtbs'] = {dtb: inspect_dtb(Path(contract['build_root']) / 'arch/arm64/boot/dts' / dtb)
                                       for dtb in contract['dtbs']}
                    integrity['name'] = 'source-integrity-after'
                    facts = collect(integrity, output, env, descriptor, interrupted, contract)
                    receipt['commands'].append(facts)
                    accepted_command(facts)
                    receipt['after'] = check_files(contract)
                    require(receipt['before'] == receipt['after'], 'protected inputs changed')
                    require(sha(Path(tools['build-dtc']['path'])) == tools['build-dtc']['sha256'], 'build DTC changed')
                    receipt['result'] = 'COLLECTED_REVIEW_REQUIRED'
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                receipt['result'] = 'REFUSED'
                receipt['reason'] = str(exc)
            finally:
                # Record protected-file preservation even after a failed recipe.
                try:
                    receipt['after'] = check_files(contract)
                except (OSError, ValueError) as exc:
                    receipt['preservation_error'] = str(exc)
                    receipt['result'] = 'REFUSED'
                guard.publish_completed_result(output, receipt, interrupted)
        print(json.dumps(receipt, sort_keys=True))
        require(receipt['result'] == 'COLLECTED_REVIEW_REQUIRED', 'schema collection refused; preserve evidence')
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='requires assigned integrator lock window')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({'execution': 'not requested', 'commands': plan()}, indent=2))
        return
    require(args.output is not None, 'new explicit output required')
    execute(args.output.absolute())


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('REFUSED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
