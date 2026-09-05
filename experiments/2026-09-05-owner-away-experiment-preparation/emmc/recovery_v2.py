# SPDX-License-Identifier: MIT
"""New eMMC session only: exact wrapper stdout, original strict transport."""
ANNOUNCEMENT = b'Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'
REBOOT_SHA = '3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7'

def parse_recovery_request(raw, process, boot):
    expected = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={boot}\nreboot_sha256={REBOOT_SHA}\n'
                'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode() + ANNOUNCEMENT
    if raw != expected:
        raise ValueError('native request/wrapper output mismatch')
    if not process['stdin_complete'] or process['reason'] is not None or process['exit_status'] != 255:
        raise ValueError('native request/SSH disconnect unconfirmed')
    return {'classification': 'native-recovery-requested', 'boot_id': boot,
            'request_count': 1, 'recovery_confirmed': False}
