# SPDX-License-Identifier: MIT
"""Future CCMP2 genuine no-scan path; frozen CCMP1 host definitions unchanged."""


def run_without_scan(ph, candidate):
    """No helper/leaf was started, so do not install C2 export prerequisites.

    Use the existing underlying WIPHY/A53 preparation, which preserves all
    private context/one-claim/seal/regression/recovery checks. A started or
    uncertain helper cannot take this shortcut; its real guards remain intact.
    """
    helper = ph.HELPER
    if helper.record.get('started') is not False or helper.proc is not None or helper.pgid is not None:
        raise RuntimeError('no-scan requires a never-started helper; preserve real child quiescence guards')
    prepared = ph.WIPHY_PREPARE(candidate)
    prepared['finish'].REPO = ph.PRIVATE_REPO
    result = prepared['execute'](prepared)
    result['scan_attempted'] = False
    (ph.ROOT / 'failure-session-result.json').write_bytes(ph.HOST.DOMAIN.HOST.encoded(result))
    prepared['finish'].sync_directory(ph.ROOT)
    return 0 if result.get('regression_pass') and result.get('recovery_confirmed') else 1
