#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A refused session still exports the kernel record, and the return can stop
the owned supplicant itself.

usage: failure_preservation.py <work-dir>   (after bind rendered hosts/; before prepare)

Boot O's join failed, the leaf outlived the host's run clock, and both reviewed
paths refused while the owned supplicant lived: the session's log-export
wrapper ("owned supplicant not confirmed quiesced; refusing seal and
recovery") and the watcher's preservation and return (its quiescence proof,
exit 62, comes before its export). The kernel record was lost with the owner's
power-key restart (a cold boot; ramoops survives only a warm reset).
join_failure_exit.py makes a failed join end the leaf; this is the layer behind
it, for any other way the session can be left with an owned process alive.

Session (the adapter's bind_host wraps the session's phase invoker inside the
scan host's own wrapper; the cohort is unchanged). When the C2 wrapper refuses
on quiescence:

1. stop the owned supplicant on the device: every wpa_supplicant process
   (the same set the C2 count uses), TERM, up to 5 s, KILL, up to 5 s, and the
   before/after sets recorded;
2. re-run the C2 supplicant count and the leaf's quiescence record under new
   labels (the first, refused results stay as written);
3. if both now pass, run the C2 cycles export with its own refusal rule and
   then the reviewed log seal, and continue to the reviewed return;
4. otherwise export the kernel record through the reviewed seal script,
   keep its raw bytes privately, and refuse the return as before.

Watcher (preserve-and-return.py): stop the owned processes the quiescence proof
names (wpa_supplicant, nc, dhcpcd, udhcpc) the same way, export the sealed log
whatever their state, and only then require the proof before the native reboot.
The RAM-wiping reboot still needs the proof; the export no longer does.
"""
import sys
from pathlib import Path

OWNED = ('wpa_supplicant', 'nc', 'dhcpcd', 'udhcpc')


def stop_script(boot, names):
    """TERM then KILL every process whose comm is one of names; identity before
    and after; the sets before, after TERM and after KILL, framed."""
    case = '|'.join(names)
    return ("#!/bin/sh\nset -u\nBB=/bin/busybox\n"
            "[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = '" + boot + "' ] || exit 3\n"
            "owned() { for d in /proc/[0-9]*; do n=; IFS= read -r n < \"$d/comm\" 2>/dev/null || continue; "
            "case \"$n\" in " + case + ") $BB printf '%s:%s ' \"${d#/proc/}\" \"$n\";; esac; done; }\n"
            "pids() { owned | $BB sed 's/:[^ ]*//g'; }\n"
            "before=$(owned)\n"
            "p=$(pids); [ -z \"$p\" ] || kill -TERM $p 2>/dev/null || :\n"
            "i=0; while [ -n \"$(pids)\" ] && [ \"$i\" -lt 25 ]; do $BB sleep 0.2; i=$((i + 1)); done\n"
            "after_term=$(owned)\n"
            "p=$(pids); [ -z \"$p\" ] || kill -KILL $p 2>/dev/null || :\n"
            "i=0; while [ -n \"$(pids)\" ] && [ \"$i\" -lt 25 ]; do $BB sleep 0.2; i=$((i + 1)); done\n"
            "after=$(owned)\n"
            "$BB printf '__OWNED_STOP_BEGIN__\\nboot_id=%s\\nbefore=%s\\nafter_term=%s\\nafter=%s\\n__OWNED_STOP_END__\\nboot_after=%s\\n' "
            "'" + boot + "' \"$before\" \"$after_term\" \"$after\" \"$($BB cat /proc/sys/kernel/random/boot_id)\"\n")


def stop_result(raw, err, process, boot):
    import re
    text = raw.decode('ascii', 'replace') if isinstance(raw, (bytes, bytearray)) else raw
    m = re.search(r'__OWNED_STOP_BEGIN__\nboot_id=(\S+)\nbefore=([^\n]*)\nafter_term=([^\n]*)\nafter=([^\n]*)\n'
                  r'__OWNED_STOP_END__\nboot_after=(\S+)\n$', text)
    result = {'framed': bool(m), 'boot_match': bool(m and m[1] == boot and m[5] == boot),
              'before': m[2].split() if m else None, 'after_term': m[3].split() if m else None,
              'after': m[4].split() if m else None,
              'transport_ok': bool(not err and (process or {}).get('exit_status') == 0)}
    result['stopped'] = bool(result['framed'] and result['boot_match'] and result['transport_ok'] and not result['after'])
    return result


# Inserted into the adapter: wraps the session's phase invoker (see the docstring).
SESSION = '''

def _bind_failure_preservation(ph):
    """failure_preservation.py: stop, re-check, then seal; or export, then refuse."""
    import json
    original = ph.SCAN.PREPARE
    c2, root = ph.C2, ph.ROOT

    def prepare(candidate):
        prepared = original(candidate)
        g = prepared['execute'].__globals__
        inner = g['invoke']
        budgets = {'owned-stop': (30, 4096), 'supplicant-log-recheck': (20, c2['LOG_LIMIT'] + 4096),
                   'quiescence-recheck': (20, 4096), 'refusal-log-export': (30, 3145728)}
        for label, (seconds, limit) in budgets.items():
            g['BUDGETS'][label] = (seconds, limit)
            prepared['claim']['phase_budgets'][label] = {'connections': 1, 'seconds': seconds,
                                                         'stdout_bytes': limit, 'stderr_bytes': 16384}
        done = False

        def write(active, name, value):
            active['collector'].write_new(root / name, value if isinstance(value, bytes) else
                                          ph.HOST.DOMAIN.HOST.encoded(value))

        def invoke(active, label, script, *, network_status=None):
            nonlocal done
            if label != 'log-export' or done:
                return inner(active, label, script, network_status=network_status)
            done = True
            try:
                return inner(active, label, script, network_status=network_status)
            except RuntimeError as error:
                if 'not confirmed quiesced' not in str(error):
                    raise
                refusal = str(error)
            boot = json.loads((root / 'observation-result.json').read_bytes())['boot_id']
            raw, err, process = inner(active, 'owned-stop', _fp_stop_script(boot, ('wpa_supplicant',)).encode())
            write(active, 'owned-stop-result.json', dict(_fp_stop_result(raw, err, process, boot), refusal=refusal))
            raw, err, process = inner(active, 'supplicant-log-recheck', c2['log_script'](boot))
            log = c2['log_result'](raw, err, process, boot)
            write(active, 'supplicant-log-recheck-result.json', log)
            raw, err, process = inner(active, 'quiescence-recheck', c2['quiescence_script'](boot))
            quiet = c2['quiescence_result'](raw, err, process, boot)
            write(active, 'quiescence-recheck-result.json', quiet)
            if log.get('supplicant_processes') == 0 and quiet.get('quiesced'):
                # The C2 wrapper's remaining steps, its own refusal rule, then the reviewed seal.
                craw, cerr, cprocess = inner(active, 'cycles-export', c2['cycles_export_script'](boot))
                write(active, 'cycles-evidence.raw', craw)
                try:
                    cresult = c2['cycles_export_result'](craw, cerr, cprocess, boot)
                except (ValueError, KeyError, TypeError) as error:
                    cresult = {'complete': False, 'reason': str(error)}
                write(active, 'cycles-evidence-result.json', cresult)
                if not cresult.get('boot_match') or not cresult.get('transport_ok') or cresult.get('truncated'):
                    raise RuntimeError('cycles-export transport/boot/framing failed or a file was '
                                       'truncated after the owned stop; refusing seal and recovery')
                return inner(active, label, script, network_status=network_status)
            # Still not quiescent: keep the kernel record, then refuse as before.
            raw, err, process = inner(active, 'refusal-log-export', script)
            write(active, 'refusal-log-export.raw', raw)
            write(active, 'refusal-log-export-process.json', dict(process or {}, stderr_bytes=len(err or b'')))
            raise RuntimeError(refusal + '; owned stop did not quiesce; kernel record exported before the refusal')

        g['invoke'] = invoke
        return prepared

    ph.SCAN.PREPARE = prepare
'''


def session_source():
    import inspect
    helpers = (inspect.getsource(stop_script).replace('def stop_script(', 'def _fp_stop_script(') +
               '\n\n' + inspect.getsource(stop_result).replace('def stop_result(', 'def _fp_stop_result('))
    return '\n\n' + helpers + SESSION


def apply_adapter(path):
    s = path.read_text()
    old = "    host.THROUGHPUT_BINDING = (str(root), plan['helper_sha256'])\n"
    assert s.count(old) == 1, 'adapter anchor (bind_host)'
    s = s.replace(old, old + "    _bind_failure_preservation(host.PH)\n")
    old = "\ndef run_phase(phase, execute):\n"
    assert s.count(old) == 1, 'adapter anchor (run_phase)'
    s = s.replace(old, session_source() + "\n" + old)
    compile(s, str(path), 'exec')
    path.write_text(s)


def apply_return(path):
    s = path.read_text()
    # A work directory derived from one already patched carries the change: verify it, do not re-apply.
    if s.count("p, out, err = step('owned-stop', ") == 1:
        assert s.index("step('owned-stop'") < s.index("step('log-export'") < s.index("step('post-session-quiescence'"), \
            'return order (stop, export, proof) changed'
        return
    old = """p, out, err = step('post-session-quiescence', q)
assert p['exit_status'] == 0 and p['reason'] is None and p['stdin_complete'] and not err and out == b'post_session_quiescence=pass\\n', (p, out, err)
p, out, err = step('log-export', S.seal_script(v, boot), 30, 3145728)
exported = S.parse_log_export(out, err, p)
h['write'](r/'log-result.json', h['encoded'](exported['result']))
for name, data in exported['files'].items(): h['write'](r/name, data)
"""
    assert s.count(old) == 1, 'return anchor (quiescence, export)'
    new = """# failure_preservation.py: stop the owned processes, export the sealed log whatever
# their state, and only then require the quiescence proof before the native reboot.
fp = runpy.run_path(str(root/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/hosts/failure_preservation.py'))
p, out, err = step('owned-stop', identity + fp['stop_script'](boot, fp['OWNED']).encode().split(b'\\n', 1)[1], 30, 4096)
h['write'](r/'owned-stop-result.json', h['encoded'](fp['stop_result'](out, err, p, boot)))
p, out, err = step('log-export', S.seal_script(v, boot), 30, 3145728)
exported = S.parse_log_export(out, err, p)
h['write'](r/'log-result.json', h['encoded'](exported['result']))
for name, data in exported['files'].items(): h['write'](r/name, data)
p, out, err = step('post-session-quiescence', q)
assert p['exit_status'] == 0 and p['reason'] is None and p['stdin_complete'] and not err and out == b'post_session_quiescence=pass\\n', (p, out, err)
"""
    s = s.replace(old, new)
    compile(s, str(path), 'exec')
    path.write_text(s)


if __name__ == '__main__':
    work = Path(sys.argv[1])
    apply_adapter(work / 'hosts/throughput-session-adapter.py')
    apply_return(work / 'preserve-and-return.py')
    print('failure preservation: the session stops the owned supplicant and re-checks, or exports then refuses; '
          'the return stops the owned processes and exports before its proof (adapter, preserve-and-return)')
