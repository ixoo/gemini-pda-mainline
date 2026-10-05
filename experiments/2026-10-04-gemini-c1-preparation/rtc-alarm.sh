#!/bin/sh
# SPDX-License-Identifier: MIT
# One finite awake RTC alarm through the standard sysfs interface.
# Refuses an inherited alarm, waits at most WAIT seconds, always cancels.
BB=${BB:-/bin/busybox}
RTC=/sys/class/rtc/rtc0
WAIT=20

# shellcheck disable=SC2016 # awk program, not shell expansion
irq_count() {
    $BB awk '/mt6397-rtc/ { n = 0; for (i = 2; i <= NF; i++)
        if ($i ~ /^[0-9]+$/) n += $i; else break; print n; f = 1 }
        END { if (!f) print "absent" }' /proc/interrupts
}

# The name file prints "<driver> <device>"; check the bound driver instead.
driver=$($BB readlink -f "$RTC/device/driver" 2>/dev/null)
[ "${driver##*/}" = mt6397-rtc ] || { echo "result=refused reason=rtc0-not-mt6397 driver=$driver"; exit 10; }
inherited=$($BB cat "$RTC/wakealarm") || { echo "result=refused reason=wakealarm-unreadable"; exit 11; }
[ -z "$inherited" ] || { echo "result=refused reason=inherited-alarm value=$inherited"; exit 12; }
before=$(irq_count)
case "$before" in ''|absent|*[!0-9]*) echo "result=refused reason=no-rtc-irq-line"; exit 13 ;; esac
echo "rtc_time=$($BB cat "$RTC/since_epoch") irq_before=$before"

if ! echo +10 > "$RTC/wakealarm"; then
    echo "result=set-failed"
    status=20
else
    echo "armed=$($BB cat "$RTC/wakealarm")"
    status=30
    i=0
    while [ "$i" -lt "$WAIT" ]; do
        $BB sleep 1
        i=$((i + 1))
        now=$(irq_count)
        if [ "$now" != "$before" ] && [ -z "$($BB cat "$RTC/wakealarm")" ]; then
            echo "result=fired after_s=$i irq_after=$now rtc_time=$($BB cat "$RTC/since_epoch")"
            status=0
            break
        fi
    done
    [ "$status" = 0 ] || echo "result=timeout after_s=$i irq_after=$(irq_count)"
fi

# Always cancel; with no enabled alarm this is a no-op in the RTC core.
if echo 0 > "$RTC/wakealarm" && [ -z "$($BB cat "$RTC/wakealarm")" ]; then
    echo "cleanup=pass"
else
    echo "cleanup=fail"
    [ "$status" = 0 ] && status=40
fi
exit "$status"
