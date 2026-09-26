# Modern MediaTek power-status read errors, compile-only

The Linux 7.1.3 direct-control provider polls power status through a boolean
helper that discards both `regmap_read` results. For a future CONN domain, a
read error during ON or OFF could be interpreted as the requested ACK, so
the [initial-OFF check](../2026-09-26-mt6797-modern-provider-off-admission/README.md)
and [failure latch](../2026-09-26-mt6797-modern-provider-fault-retention/README.md)
would not provide a complete transition boundary.

The [single format-patch](../../patches/proposals/0010-pmdomain-mediatek-fail-opted-status-read-errors.patch)
adds an error-returning dual-status read for domains that opt into fault
retention. An ON/OFF poll waits through mixed status until both bits reach the
target, returns the first read error immediately, and otherwise retains the
existing finite timeout. Initial-OFF admission reuses the checked read and
still rejects ON or mixed status. The existing polling path is unchanged for
domains without the retention flag. Pinned Linux 7.1.3 checkpatch reports
zero errors and warnings, and the patch applies after the two preceding
modern-provider proposals.

No domain selects the flag in this profile. The patch does not add MT6797
domain data or a DT child, and it does not address SPM register-control
authority, external rails/reset, power-bit OFF ordering, or shared EMI/remap
ownership. It is not a boot2 candidate or evidence of usable Wi-Fi.
