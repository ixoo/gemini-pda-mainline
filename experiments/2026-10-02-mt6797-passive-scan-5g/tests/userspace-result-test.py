#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check private scan-result classification without a candidate or device."""
import importlib.util
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'passive-host.py'
BOOT = '00000000-0000-0000-0000-000000000001'


def main():
    with tempfile.TemporaryDirectory(prefix='mt6797-scan-result-') as root:
        prior = os.environ.get('GEMINI_PRIVATE_REPO')
        os.environ['GEMINI_PRIVATE_REPO'] = root
        try:
            spec = importlib.util.spec_from_file_location('scan_result_fixture', SOURCE)
            host = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(host)
        finally:
            if prior is None:
                del os.environ['GEMINI_PRIVATE_REPO']
            else:
                os.environ['GEMINI_PRIVATE_REPO'] = prior
        prefix = ('boot_before=' + BOOT + '\nkernel=' + host.RELEASE +
                  '\ninterface_created=1\ninterface_up=1\n__IW_PASSIVE_BEGIN__\n').encode()
        phy = b'__PHY_INFO_BEGIN__\n\t* 5200 MHz [40] (20.0 dBm) (no IR)\n__PHY_INFO_END__\n'
        bss = b'BSS 00:00:00:00:00:01(on wlan0)\n\tfreq: 5200\n'
        suffix = ('__IW_PASSIVE_END__\nscan_exit=0\nboot_after=' + BOOT + '\n').encode()

        def classify(body, err=b'', **changes):
            raw = prefix + body + suffix
            process = dict(stdout_bytes=len(raw), stderr_bytes=len(err),
                           stdin_complete=True, exit_status=0, reason=None)
            process.update(changes)
            return host.scan_process(raw, err, process, BOOT)

        result = classify(phy + bss)
        assert all(result[key] for key in ('transport_complete', 'channel40_permitted',
                                          'standard_scan_succeeded', 'standard_bss_result',
                                          'standard_5g_bss_result'))
        assert not classify(phy + bss.replace(b'5200', b'2412'))['standard_5g_bss_result']
        assert not classify(phy)['standard_bss_result']
        assert not classify(phy.replace(b'(no IR)', b'(disabled)') + bss)['channel40_permitted']
        assert not classify(bss)['channel40_permitted']
        assert not classify(phy + b'freq: 5200\n')['standard_5g_bss_result']
        assert not classify(phy + bss, b'failure')['standard_scan_succeeded']
        for changes in (dict(stdin_complete=False), dict(exit_status=1),
                        dict(reason='timeout'), dict(stdout_bytes=0), dict(stderr_bytes=1)):
            assert not classify(phy + bss, **changes)['transport_complete']
    print('userspace result: pass; valid 5GHz BSS, absent/disabled band and transport refusals')


if __name__ == '__main__':
    main()
