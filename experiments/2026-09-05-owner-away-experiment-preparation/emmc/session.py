#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit one-process identity/read/seal orchestration, no automatic chaining.

The coordinator admits identity with --execute and actual observation admission.
Then stdin accepts a single collect request and a separately admitted preserve
request. EOF/interruption drops the process-local receipt; there is no resume.
No credentials, raw device bytes or addresses are printed by this runner.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
L = runpy.run_path(str(HERE / 'collect-emmc.py'))
M = runpy.run_path(str(HERE / 'finish-emmc.py'))
H = runpy.run_path(str(HERE / 'mainline_host.py'))


class Session:
    def __init__(self, context, identity_directory):
        # Only Session.start may attach a newly authenticated live receipt.
        self.context = context
        self.identity_directory = Path(identity_directory)
        self.window = None
        self.collected = False
        self.closed = False

    @classmethod
    def start(cls, admission):
        L['execution_gate']()
        context = L['prepare'](admission)
        directory = (L['REPO'] / 'artifacts/a53-authenticated/emmc-readonly/identities' /
                     context['admission']['admission_id'])
        L['require'](not directory.exists() and not directory.is_symlink(),
                     'identity budget already consumed; process restart cannot resume')
        L['require'](not L['ATTEMPT_ROOT'].exists(), 'read budget already consumed')
        L['C']['private_root'](directory.parent)
        session = cls(context, directory)
        session.window = H['identity_window'](context, directory)
        return session

    def dispatch(self, request):
        try:
            return self._dispatch(request)
        except BaseException:
            self.close()
            raise

    def _dispatch(self, request):
        L['require'](not self.closed and self.window is not None, 'session interrupted or closed')
        L['require'](type(request) is dict and request.get('action') in ('collect', 'preserve-log'),
                     'explicit session action required')
        if request['action'] == 'collect':
            L['require'](set(request) == {'action'} and not self.collected, 'one collection only')
            # A refusal is terminal for this orchestration, not a retry invitation.
            self.collected = True
            return L['collect'](self.context, True, self.window)
        L['require'](set(request) == {'action', 'admission'} and
                     type(request['admission']) is str and self.collected,
                     'separate preservation admission required after collection')
        context = M['prepare'](Path(request['admission']))
        L['require'](context['admission']['action'] == 'preserve-log', 'preservation action only')
        result = M['perform'](context, True, self.window)
        self.close()
        return result

    def close(self):
        self.window = None
        self.closed = True


def main(argv=None, stream=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--admission', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'classification': 'dry-run', 'network_access': 'none'}))
        return 0
    if args.admission is None:
        parser.error('execution requires a fresh admission')
    session = None
    try:
        session = Session.start(args.admission)
        print(json.dumps({'classification': 'identity-verified', 'next': 'explicit action required'}), flush=True)
        stream = sys.stdin if stream is None else stream
        while not session.closed:
            line = stream.readline(4097)
            if not line:
                break
            L['require'](len(line) <= 4096 and line.endswith('\n'), 'bounded complete action line required')
            result = session.dispatch(json.loads(line, object_pairs_hook=L['unique']))
            print(json.dumps({'classification': result['classification'],
                              'next': 'separate admission or stop'}), flush=True)
        return 0
    except (ValueError, OSError, KeyboardInterrupt):
        print(json.dumps({'classification': 'stopped', 'resume': False}), flush=True)
        return 2
    finally:
        if session is not None:
            session.close()


if __name__ == '__main__':
    raise SystemExit(main())
