#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guard for hosts/console_progress.py: every leaf anchor occurs exactly once,
the injected leaf equals the reviewed leaf plus exactly the known block and
the four one-line calls and nothing else, flag off leaves the leaf
untouched, and the helper's device script gains exactly the cp() definition
and its three chunk lines with the flag on and nothing with it off.

usage: console-progress-test.py [reviewed-leaf.sh] [throughput-helper.py]
Defaults: the service host cohort's leaf and the pass-rate work directory's
helper under artifacts/; a missing input skips that half with a message.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'hosts'))
import console_progress as cp  # noqa: E402

REPO = HERE.parents[2]
LEAF = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'artifacts/wifi-service-host-cohort-1/experiments/2026-10-13-mt6797-wifi-native-delivery-probe/join-ccmp-p2.sh'
HELPER = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / 'artifacts/wifi-tx-passrate-work/hosts/throughput-helper.py'


def check_leaf():
    if not LEAF.is_file():
        print('SKIP leaf: no reviewed leaf at', LEAF)
        return
    leaf = LEAF.read_bytes()
    text = leaf.decode()
    for old, _ in cp.LEAF_EDITS:
        assert text.count(old) == 1, 'anchor not unique: %r' % old
    out = cp.inject_leaf(leaf, 'fixture')
    # Strip exactly the known insertions; what remains must be the reviewed leaf.
    stripped = out.decode()
    for old, new in cp.LEAF_EDITS:
        new = new.replace('__CP_VARIANT__', 'fixture')
        assert stripped.count(new) == 1, 'injected block not unique: %r' % new[:40]
        stripped = stripped.replace(new, old)
    assert stripped.encode() == leaf, 'injected leaf is not the reviewed leaf plus the known block'
    assert out.count(b'cp_say ') == 6 and out.count(b'/dev/tty0') == 1
    # The reviewed leaf itself never writes the console.
    assert b'/dev/tty0' not in leaf
    for path in (leaf, out):
        with tempfile.NamedTemporaryFile('wb', suffix='.sh', delete=False) as f:
            f.write(path)
        subprocess.run(['bash', '-n', f.name], check=True)
    print('PASS leaf: anchors unique, injection is exactly the known block, syntax ok')


def check_helper():
    if not HELPER.is_file():
        print('SKIP helper: no helper at', HELPER)
        return
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp); (work / 'hosts').mkdir()
        (work / 'hosts' / 'throughput-helper.py').write_text(HELPER.read_text())
        # A minimal prepare stand-in carrying the anchors patch_prepare needs.
        (work / 'hosts' / 'throughput-prepare.py').write_text(
            "import os, sys\n"
            "def prepare(retained, old, cohort, here):\n"
            "    leaf = retained.replace(old,b'    pc_result=0 # throughput: no periodic probes during measurement')\n"
            "    plan = {'schema':1,}\n"
            "    env = {\n"
            "           'TP_SOURCE_ROOT':str(cohort),\n"
            "    }\n"
            "    return leaf, plan, env\n")
        subprocess.run([sys.executable, str(HERE.parent / 'hosts' / 'console_progress.py'), str(work)],
                       check=True)
        def script(path, flag):
            spec = importlib.util.spec_from_file_location('h' + flag, path)
            mod = importlib.util.module_from_spec(spec)
            os.environ['TP_CONSOLE_PROGRESS'] = flag
            spec.loader.exec_module(mod)
            return mod, mod.remote_script('BOOT', 'HOST')
        base_mod, base = script(HELPER, '0')
        patched_mod, off = script(work / 'hosts' / 'throughput-helper.py', '0')
        _, on = script(work / 'hosts' / 'throughput-helper.py', '1')
        cp_def = cp.HELPER_CP
        assert off.count(cp_def.replace('__CP_FLAG__', '0')) == 1 and on.count(cp_def.replace('__CP_FLAG__', '1')) == 1
        # Remove exactly the known insertions; the result must be the unpatched script.
        for s, flag in ((off, '0'), (on, '1')):
            r = s.replace(cp_def.replace('__CP_FLAG__', flag), '')
            r = r.replace("        cp '\\033[3;1H\\033[Kcycle   1/1     chunk  %s/5  %s\\n' \"$i\" \"$dir\"; t0=$(clock)\n", '')
            r = r.replace("        t1=$(clock); if [ \"$dir\" = RX ] && [ \"$t1\" -gt \"$t0\" ]; then r=$($BB awk -v b=\"$n\" -v d=\"$((t1-t0))\" 'BEGIN{printf \"%.2f\", b*8000/d}'); else r=-; fi\n"
                          "        cp '\\033[4;1H\\033[Krate    %s Mbit/s\\n' \"$r\"\n", '')
            assert r == base, 'device script is not the original plus the known lines (flag %s)' % flag
        # With the flag off the device script writes nothing to the console.
        assert '"0" = 1' in off and '"1" = 1' in on
        for s in (off, on):
            for name in ('validate_idle_safety', 'validate_receive_safety'):
                getattr(patched_mod, name)(s)
            with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
                f.write(s)
            subprocess.run(['bash', '-n', f.name], check=True)
    print('PASS helper: device script is the original plus exactly the known lines, flag on and off; validators and syntax ok')


if __name__ == '__main__':
    check_leaf()
    check_helper()
