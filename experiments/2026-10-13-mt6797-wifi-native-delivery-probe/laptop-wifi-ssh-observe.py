#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""D1: retain output of one existing Wi-Fi SSH attempt, without changing its command."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'laptop-wifi-ssh-ccmp.py'
FROZEN = HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join/laptop-wifi-ssh.py'
for path, digest in ((SOURCE, '2389fbb748a6e3f0b258e14d07bfc715cad6dd71b384c9f5d444a5ddac478d51'),
                     (FROZEN, '4861544e49345230cca61c631bf888eb9b7cb3f5434c279d406bda74ca4c6e99')):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('reviewed SSH helper changed')
SPEC = importlib.util.spec_from_file_location('ccmp_ssh_observation_source', SOURCE)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def observing_runner(root, runner=subprocess.run, monotonic_ns=time.monotonic_ns):
    """Pass USB calls through; retain the original Wi-Fi call's output once.

    Do not add SSH options or inspect/alter the returned bytes. The original
    verifier alone decides identity and ACK. Existing subprocess timeout and
    owned-process-group cleanup still apply, including TimeoutExpired.
    """
    used = False

    def invoke(argv, **kwargs):
        nonlocal used
        if not any(arg.startswith('HostKeyAlias=') for arg in argv):
            return runner(argv, **kwargs)
        if used or kwargs.get('stdout') != subprocess.PIPE or \
                kwargs.get('stderr') != subprocess.DEVNULL:
            raise ValueError('unexpected or repeated Wi-Fi acquisition')
        used = True
        root.mkdir(mode=0o700)  # exclusive: never replace a prior observation
        with (root / 'stderr.bin').open('xb') as error, \
                (root / 'stdout.bin').open('xb') as output:
            started = monotonic_ns()
            record = {'started_ns': started, 'ended_ns': None,
                      'exit': None, 'timeout': False, 'stdout_bytes': 0}
            try:
                result = runner(argv, **{**kwargs, 'stderr': error})
                output.write(result.stdout)
                record.update(exit=result.returncode, stdout_bytes=len(result.stdout))
                return result
            except subprocess.TimeoutExpired as exc:
                partial = exc.output or b''
                output.write(partial)
                record.update(timeout=True, stdout_bytes=len(partial))
                raise
            finally:
                record['ended_ns'] = monotonic_ns()
                error.flush()
                record['stderr_bytes'] = error.tell()
                with (root / 'process.json').open('x') as stream:
                    json.dump(record, stream, indent=2, sort_keys=True)
                    stream.write('\n')
    return invoke


def main():
    os.umask(0o077)
    # The owned helper supplies exactly one receipt argument. Keep all argument
    # parsing, validation and execution in the original helper's main().
    if sys.argv.count('--receipt') != 1:
        raise ValueError('one private session receipt is required')
    receipt = Path(sys.argv[sys.argv.index('--receipt') + 1])
    expected = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / \
        'ccmp-stable-monitor/session-ccmp10/wifi-ssh-receipt.json'
    if receipt != expected or receipt.parent.is_symlink():
        raise ValueError('observation receipt is outside the admitted session')
    observed = observing_runner(receipt.parent / 'ssh-client-observation')

    def run(*args, **kwargs):
        return C.run(*args, **kwargs, runner=observed)

    C.M.run = run
    return C.M.main()


if __name__ == '__main__':
    sys.exit(main())
